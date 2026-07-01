"""FR-5: trade decision + execution.

Each agent trades at most ONCE per round at the exchange. The decision is
RULE-BASED and fully deterministic (no LLM, no randomness) so the same agent
state always yields the same trade. This keeps the round reproducible and the
behaviour explainable: a trade is a pure function of the agent's persona type
and its fear/greed (plus the market fear/greed index for the market-aware
personas).

Pipeline:
    decide_trade(agent, assets) -> TradeDecision   # what the agent wants to do
    execute_trade(decision, agent, assets) -> TradeResult  # clamp + apply
    run_trades(agents, assets) -> list[TradeResult]  # decide all, execute sorted

This module depends ONLY on sim.models and the stdlib.
"""

from __future__ import annotations

from . import tuning as T
from .llm import LLMClient, safe_json
from .models import (
    Action,
    Agent,
    Asset,
    AgentType,
    Event,
    MarketData,
    PortfolioHolding,
    TradeDecision,
    TradeResult,
)

# --------------------------------------------------------------------------- #
# Tunable, deterministic constants. Fractions are of cash (buys) or of the
# targeted holding's amount (sells).
# --------------------------------------------------------------------------- #
PANIC_SELL_FRACTION = 0.5  # panic_seller dumps half its largest holding
FOMO_BUY_FRACTION = 0.3  # fomo_trader chases with a chunk of cash
WHALE_BUY_FRACTION = 0.6  # whale buys big into fear
CONTRARIAN_BUY_FRACTION = 0.3
CONTRARIAN_SELL_FRACTION = 0.5
VALUE_BUY_FRACTION = 0.2  # value_investor nibbles on "oversold" greed
QUANT_TRADE_FRACTION = 0.3  # quant mechanical sizing (buy or sell)
CONSPIRACY_BUY_FRACTION = 0.15  # like fomo but smaller
GAMBLER_BUY_FRACTION = 0.7  # §9.5.3 한탕 도박꾼: 분산 깨고 몰빵(과대베팅 G2)

# Emotion thresholds.
HIGH_FEAR = 60.0
HIGH_GREED = 60.0
LOW_FEAR = 40.0
EMOTION_MARGIN = 10.0  # greed/fear must beat the other by this to act

# Market fear/greed index extremes (0 = extreme fear, 100 = extreme greed).
INDEX_EXTREME_FEAR = 30.0
INDEX_EXTREME_GREED = 70.0


# --------------------------------------------------------------------------- #
# Symbol-selection helpers
# --------------------------------------------------------------------------- #
def _largest_holding(
    agent: Agent, assets_by_sym: dict[str, Asset]
) -> PortfolioHolding | None:
    """Largest (by amount) holding that is actually tradeable this round."""
    candidates = [
        h
        for h in agent.portfolio
        if h.amount > 0 and h.asset in assets_by_sym
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda h: h.amount)


def _buy_symbol(agent: Agent, assets_by_sym: dict[str, Asset]) -> str | None:
    """Pick a symbol to buy: prefer one the agent already holds, else a default."""
    for h in agent.portfolio:
        if h.asset in assets_by_sym:
            return h.asset
    if assets_by_sym:
        return next(iter(assets_by_sym))  # deterministic: first inserted key
    return None


def _buy_qty(agent: Agent, symbol: str, assets_by_sym: dict[str, Asset], fraction: float) -> float:
    """Units buyable when spending `fraction` of cash at the current price."""
    asset = assets_by_sym.get(symbol)
    if asset is None or asset.price <= 0:
        return 0.0
    spend = max(0.0, agent.cash) * fraction
    return spend / asset.price


def _fear_is_high(agent: Agent) -> bool:
    """A persona's own panic threshold takes precedence over the global one."""
    if agent.fear_threshold is not None:
        return agent.fear >= agent.fear_threshold
    return agent.fear > HIGH_FEAR


# --------------------------------------------------------------------------- #
# Decision builders
# --------------------------------------------------------------------------- #
def _hold(agent: Agent, reason: str) -> TradeDecision:
    return TradeDecision(agent_id=agent.id, action=Action.HOLD, symbol=None, qty=0.0, reason=reason)


def _buy_decision(
    agent: Agent,
    assets_by_sym: dict[str, Asset],
    fraction: float,
    action: Action,
    reason: str,
) -> TradeDecision:
    symbol = _buy_symbol(agent, assets_by_sym)
    if symbol is None:
        return _hold(agent, "no tradeable symbol to buy")
    qty = _buy_qty(agent, symbol, assets_by_sym, fraction)
    if qty <= 0:
        return _hold(agent, "insufficient cash to buy")
    return TradeDecision(agent_id=agent.id, action=action, symbol=symbol, qty=qty, reason=reason)


def _sell_decision(
    agent: Agent,
    assets_by_sym: dict[str, Asset],
    fraction: float,
    reason: str,
) -> TradeDecision:
    holding = _largest_holding(agent, assets_by_sym)
    if holding is None:
        return _hold(agent, "nothing to sell")
    qty = holding.amount * fraction
    if qty <= 0:
        return _hold(agent, "nothing to sell")
    return TradeDecision(
        agent_id=agent.id, action=Action.SELL, symbol=holding.asset, qty=qty, reason=reason
    )


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def decide_trade(
    agent: Agent,
    assets_by_sym: dict[str, Asset],
    market: MarketData | None = None,
) -> TradeDecision:
    """Rule-based, deterministic trade decision for one agent (FR-5)."""
    atype = agent.type
    index = market.fearGreedIndex if market is not None else None

    # panic_seller: dumps on high fear, otherwise sits tight.
    if atype == AgentType.PANIC_SELLER.value:
        if _fear_is_high(agent):
            return _sell_decision(
                agent, assets_by_sym, PANIC_SELL_FRACTION, "panic: fear too high, cutting losses"
            )
        return _hold(agent, "fear tolerable, holding")

    # fomo_trader: chases price when greed runs hot.
    if atype == AgentType.FOMO_TRADER.value:
        if agent.greed > HIGH_GREED:
            return _buy_decision(
                agent, assets_by_sym, FOMO_BUY_FRACTION, Action.BUY, "FOMO: greed high, buying in"
            )
        return _hold(agent, "not greedy enough yet")

    # whale: buys big into extreme fear, or when personally calm and greedy.
    if atype == AgentType.WHALE.value:
        cheap = index is not None and index < INDEX_EXTREME_FEAR
        calm_greedy = agent.fear < LOW_FEAR and agent.greed > HIGH_GREED
        if cheap or calm_greedy:
            return _buy_decision(
                agent, assets_by_sym, WHALE_BUY_FRACTION, Action.BUY_LARGE,
                "whale: accumulating into fear",
            )
        return _hold(agent, "whale waiting")

    # contrarian: fades the crowd via the market index.
    if atype == AgentType.CONTRARIAN.value:
        if index is not None and index < INDEX_EXTREME_FEAR:
            return _buy_decision(
                agent, assets_by_sym, CONTRARIAN_BUY_FRACTION, Action.BUY,
                "contrarian: buying extreme fear",
            )
        if index is not None and index > INDEX_EXTREME_GREED:
            return _sell_decision(
                agent, assets_by_sym, CONTRARIAN_SELL_FRACTION, "contrarian: selling extreme greed"
            )
        return _hold(agent, "crowd not extreme")

    # value_investor: mostly holds; nibbles on "oversold" greed; never panic sells.
    if atype == AgentType.VALUE_INVESTOR.value:
        if agent.greed - agent.fear >= EMOTION_MARGIN:
            return _buy_decision(
                agent, assets_by_sym, VALUE_BUY_FRACTION, Action.BUY,
                "value: oversold opportunity",
            )
        return _hold(agent, "value: no margin of safety, holding")

    # quant: mechanical greed-vs-fear sizing.
    if atype == AgentType.QUANT.value:
        if agent.greed - agent.fear >= EMOTION_MARGIN:
            return _buy_decision(
                agent, assets_by_sym, QUANT_TRADE_FRACTION, Action.BUY, "quant: greed signal"
            )
        if agent.fear - agent.greed >= EMOTION_MARGIN:
            return _sell_decision(
                agent, assets_by_sym, QUANT_TRADE_FRACTION, "quant: fear signal"
            )
        return _hold(agent, "quant: no signal")

    # conspiracy: follows greed like fomo, but sizes smaller.
    if atype == AgentType.CONSPIRACY.value:
        if agent.greed > HIGH_GREED:
            return _buy_decision(
                agent, assets_by_sym, CONSPIRACY_BUY_FRACTION, Action.BUY,
                "conspiracy: riding the narrative",
            )
        return _hold(agent, "conspiracy: waiting for a story")

    if atype == AgentType.GAMBLER.value:
        # 과신·욕심 → 분산 깨고 크게 베팅(G2). 익절은 안 함(G1).
        if agent.greed > HIGH_GREED:
            return _buy_decision(
                agent, assets_by_sym, GAMBLER_BUY_FRACTION, Action.BUY_LARGE,
                "gambler: all in, go bigger",
            )
        return _hold(agent, "gambler: holding for the moonshot")

    # news_bot (and any unknown type): never trades.
    return _hold(agent, "news_bot: observe only")


# --------------------------------------------------------------------------- #
# LLM-driven decision (FR-5, "행동 결정까지 LLM"). Falls back to the deterministic
# rule above on ANY failure (no/invalid JSON, no key), so a trade always resolves
# and the offline/mocked paths stay reproducible.
# --------------------------------------------------------------------------- #
_TRADE_SYSTEM = (
    "You are ONE investor making a single trade decision at the exchange in a "
    "market-psychology game. Stay true to your personality and emotional state. "
    "Output strict JSON only."
)


def _portfolio_block(agent: Agent, assets_by_sym: dict[str, Asset]) -> str:
    rows = []
    for h in agent.portfolio:
        a = assets_by_sym.get(h.asset)
        if a is not None and h.amount > 0:
            rows.append(f"{h.asset} {h.amount:g}주 (평단 {h.avgPrice:.0f}, 현재 {a.price:.0f})")
    return "; ".join(rows) if rows else "(보유 종목 없음)"


def decide_trade_llm(
    client: LLMClient,
    agent: Agent,
    assets_by_sym: dict[str, Asset],
    market: MarketData | None = None,
    event: Event | None = None,
) -> TradeDecision:
    """LLM decides the action; deterministic ``decide_trade`` is the fallback."""
    symbols = list(assets_by_sym.keys())[:12]
    prices = ", ".join(f"{s} {assets_by_sym[s].price:.0f}" for s in symbols[:6])
    fgi = f"{market.fearGreedIndex:.0f}/100" if market is not None else "n/a"
    user = (
        f"투자자: {agent.alias} (type: {agent.type})\n"
        f"- 성향: {agent.innate}\n"
        f"- 현재: {agent.currently}\n"
        f"- 공포 {agent.fear:.0f}/100, 탐욕 {agent.greed:.0f}/100\n"
        f"- 현금 {agent.cash:.0f}원, 보유: {_portfolio_block(agent, assets_by_sym)}\n"
        f"시장: 공포탐욕지수 {fgi}, 시세 [{prices}]\n"
        + (f'오늘 이벤트: "{event.text}"\n' if event is not None else "")
        + f"거래 가능 종목: {symbols}\n\n"
        "성격과 감정에 맞게 거래를 한 번 결정하라. JSON only:\n"
        '{"action": "BUY|SELL|BUY_LARGE|HOLD", "symbol": "TICKER 또는 null", '
        '"size": 0.0~1.0 (매수=현금 비율, 매도=보유수량 비율), "reason": "짧은 한국어 이유"}'
    )
    data = safe_json(client, user, fallback={}, system=_TRADE_SYSTEM, temperature=0.6)
    if not data:  # empty/parse fail -> deterministic rule keeps the round alive
        return decide_trade(agent, assets_by_sym, market)

    try:
        action = Action(str(data.get("action", "HOLD")).upper())
    except ValueError:
        action = Action.HOLD
    reason = str(data.get("reason") or "LLM 판단")[:120]
    if action == Action.HOLD:
        return _hold(agent, reason)

    symbol = data.get("symbol")
    symbol = str(symbol).upper() if symbol not in (None, "", "null", "NULL") else None
    try:
        size = float(data.get("size", 0.3))
    except (TypeError, ValueError):
        size = 0.3
    size = min(max(size, 0.0), 1.0)

    if action in (Action.BUY, Action.BUY_LARGE):
        if symbol not in assets_by_sym:
            symbol = _buy_symbol(agent, assets_by_sym)
        if symbol is None:
            return _hold(agent, "살 종목이 없음")
        qty = _buy_qty(agent, symbol, assets_by_sym, size or 0.3)
        if qty <= 0:
            return _hold(agent, "현금 부족")
        return TradeDecision(agent_id=agent.id, action=action, symbol=symbol, qty=qty, reason=reason)

    # SELL
    held = agent.holding(symbol) if symbol else None
    if held is None or held.amount <= 0:
        held = _largest_holding(agent, assets_by_sym)
    if held is None:
        return _hold(agent, "팔 종목이 없음")
    qty = held.amount * (size or 0.5)
    if qty <= 0:
        return _hold(agent, "매도 수량 0")
    return TradeDecision(agent_id=agent.id, action=Action.SELL, symbol=held.asset, qty=qty, reason=reason)


def run_trades_llm(
    client: LLMClient,
    agents: list[Agent],
    assets_by_sym: dict[str, Asset],
    market: MarketData | None = None,
    event: Event | None = None,
) -> list[TradeResult]:
    """LLM-decide for all agents (concurrently — decisions are independent), then
    execute in a deterministic order (by id)."""
    from concurrent.futures import ThreadPoolExecutor

    def _decide(a: Agent):
        return a.id, decide_trade_llm(client, a, assets_by_sym, market, event)

    with ThreadPoolExecutor(max_workers=8) as ex:
        decisions = dict(ex.map(_decide, agents))
    ordered = sorted(agents, key=lambda a: a.id)
    return [execute_trade(decisions[a.id], a, assets_by_sym) for a in ordered]


def execute_trade(
    decision: TradeDecision,
    agent: Agent,
    assets_by_sym: dict[str, Asset],
) -> TradeResult:
    """Apply a decision to the agent, clamping to cash/holdings (FR-5)."""
    action = decision.action
    symbol = decision.symbol
    asset = assets_by_sym.get(symbol) if symbol else None

    agent.lastAction = action.value

    # HOLD, or a malformed/untradeable decision: no-op.
    if action == Action.HOLD or asset is None or symbol is None:
        return TradeResult(
            agent_id=agent.id,
            action=Action.HOLD if asset is None else action,
            symbol=symbol if asset is not None else None,
            qty=0.0,
            price=asset.price if asset is not None else 0.0,
            cash_after=agent.cash,
        )

    price = asset.price

    if action in (Action.BUY, Action.BUY_LARGE):
        qty = max(0.0, decision.qty)
        # Clamp qty so the agent never spends more cash than it has.
        if price > 0 and qty * price > agent.cash:
            qty = agent.cash / price
        cost = qty * price
        agent.cash -= cost
        _merge_buy(agent, symbol, qty, price)
        return TradeResult(
            agent_id=agent.id, action=action, symbol=symbol, qty=qty, price=price,
            cash_after=agent.cash,
        )

    # SELL: clamp to the held amount; never go short.
    held = agent.holding(symbol)
    held_amount = held.amount if held is not None else 0.0
    avg_cost = held.avgPrice if held is not None else 0.0
    qty = min(max(0.0, decision.qty), held_amount)
    # §6.5.4 실현손익 = (체결가 − 평단) × 매도수량. 평단은 _reduce_sell이 안 바꿈.
    realized_pnl = (price - avg_cost) * qty
    agent.cash += qty * price
    _reduce_sell(agent, symbol, qty)
    return TradeResult(
        agent_id=agent.id, action=Action.SELL, symbol=symbol, qty=qty, price=price,
        cash_after=agent.cash, realized_pnl=realized_pnl,
    )


def run_trades(
    agents: list[Agent],
    assets_by_sym: dict[str, Asset],
    market: MarketData | None = None,
) -> list[TradeResult]:
    """Decide for all agents, then execute in a deterministic order (by id)."""
    decisions = {a.id: decide_trade(a, assets_by_sym, market) for a in agents}
    ordered = sorted(agents, key=lambda a: a.id)
    return [execute_trade(decisions[a.id], a, assets_by_sym) for a in ordered]


# --------------------------------------------------------------------------- #
# Portfolio mutation helpers
# --------------------------------------------------------------------------- #
def _merge_buy(agent: Agent, symbol: str, qty: float, price: float) -> None:
    """Add to (or create) a holding, recomputing the cost-weighted avgPrice."""
    if qty <= 0:
        return
    held = agent.holding(symbol)
    if held is None:
        agent.portfolio.append(PortfolioHolding(asset=symbol, amount=qty, avgPrice=price))
        return
    total_amount = held.amount + qty
    if total_amount <= 0:
        return
    held.avgPrice = (held.amount * held.avgPrice + qty * price) / total_amount
    held.amount = total_amount


def _reduce_sell(agent: Agent, symbol: str, qty: float) -> None:
    """Reduce a holding; drop it entirely once it hits zero."""
    if qty <= 0:
        return
    held = agent.holding(symbol)
    if held is None:
        return
    held.amount -= qty
    if held.amount <= 1e-9:
        agent.portfolio = [h for h in agent.portfolio if h.asset != symbol]


# --------------------------------------------------------------------------- #
# §6.5.5 / §8.3 자금 행선지 판독 — "어디서 어디로"가 감정을 드러낸다
# --------------------------------------------------------------------------- #
# 포트폴리오(여러 종목+현금)에서 매도/매수는 항상 자금 이동이다. 행선지가 함정 신호.
_FUND_FLOW_SIGNALS: dict[str, tuple[str, list[str]]] = {
    "to_cash":     ("공포(시장 밖 도피)", ["F1", "F2"]),
    "to_stable":   ("공포(시장 밖 도피)", ["F1", "F2"]),
    "to_hotter":   ("FOMO(차분한 거 팔아 뜨거운 거 추격)", ["M1", "M2"]),
    "concentrate": ("과대 베팅(분산 → 한 종목 집중)", ["G2"]),
    "hold_winner": ("탐욕(수익 종목 익절 거부, 이동 없음)", ["G1"]),
}


def fund_destination(flow: str, proceeds: float = 0.0) -> tuple[str, list[str]]:
    """매도 대금의 다음 행선지 → (드러나는 감정, 연결 함정 ids). 미정의는 중립.

    flow ∈ {to_cash, to_stable, to_hotter, concentrate, hold_winner}.
    proceeds는 로깅용(현재 분류엔 미사용) — 호출자가 금액과 함께 기록.
    """
    return _FUND_FLOW_SIGNALS.get(flow, ("중립", []))


def apply_fund_flow(fund_flow, *, avg_cost, quantity, cash, positions,
                    price_today, surge_category=None, surge_price=None):
    """§8.3 충동매매 자금 행선지 → 포트폴리오 실제 이동(순수). 미정의 flow는 무변화.

    to_cash/to_stable(F1/F2 공포도피) = 전량 매도. to_hotter(M1/M2 추격) = 보유
    현금 일부를 급등 미보유 종목에 새로 태움. concentrate(G2 몰빵) = 보유 현금
    일부로 기존 포지션을 더 사(가중평균 평단 갱신). 비율은 tuning.py 상수.

    run_loop.py(단일종목 경로)와 crisis_day.py(T-216 다중종목 번들)가 공유한다
    — trade.py에 둔 이유는 둘 다 이 함수를 필요로 해서(crisis_day←run_loop
    순환 임포트를 피하려면 둘 다 임포트할 수 있는 더 낮은 모듈에 있어야 함).
    """
    positions = dict(positions)
    realized = 0.0
    if fund_flow in ("to_cash", "to_stable") and quantity > 0:
        realized = (price_today - avg_cost) * quantity
        cash += quantity * price_today
        quantity = 0.0
    elif fund_flow == "to_hotter" and surge_category and surge_price and cash > 0:
        chase_cash = cash * T.CHASE_FRACTION
        prev = positions.get(surge_category, {"avg_cost": surge_price, "quantity": 0.0})
        new_qty = prev["quantity"] + chase_cash / surge_price
        positions[surge_category] = {"avg_cost": surge_price, "quantity": new_qty}
        cash -= chase_cash
    elif fund_flow == "concentrate" and cash > 0 and price_today:
        add_cash = cash * T.CONCENTRATE_FRACTION
        add_qty = add_cash / price_today
        new_qty = quantity + add_qty
        if new_qty:
            avg_cost = ((avg_cost * quantity) + (price_today * add_qty)) / new_qty
        quantity = new_qty
        cash -= add_cash
    return {"avg_cost": avg_cost, "quantity": quantity, "cash": cash,
            "positions": positions, "realized": realized}
