"""§8.6.2 하루치 결정 파이프라인 — 새 시스템들을 한 클론의 하루로 조립.

결정/표현 분리(§8.6.3): 여기 [1]~[4]는 전부 규칙 엔진(결정적·회차 재현 가능).
[5] LLM 표현(대사·독백)은 범위 밖 — 이 오케스트레이터는 수치 결정만 낸다.

  [1] 자극 반영   : 뉴스 톤 → 감정 자극(§7.1 가격 무관)
  [2] 컨텍스트    : 운명선 change_rate + 보유 평가익 → CrisisContext
  [3] 함정 판정   : trap_pipeline.run_crisis (감지→정렬→개입→저항)
  [4] 회계+스탯   : 실현손익(§6.5) + 4스탯 자동증감(§11.5) → DailySnapshot
"""

from __future__ import annotations

from . import clone_stats as CSt
from . import news as NEWS
from . import traps as TR
from .clone_spec import CloneSpec
from .fate_line import FateLine
from .resistance import CloneProfile
from .runs import DailySnapshot
from .trade import apply_fund_flow
from .trap_pipeline import CrisisInput, Intervention, run_crisis


def _profile(spec: CloneSpec) -> CloneProfile:
    """클론 스펙(§5.5) → 저항 판정용 프로필. 성향 플래그는 인터뷰 확장 시 채움."""
    return CloneProfile(trap_scores=dict(spec.trap_scores), weakness_threshold=50.0)


def simulate_clone_day(
    *,
    clone_spec: CloneSpec,
    stats: dict[str, float],
    fate_line: FateLine,
    category: str,
    day: int,
    holding: dict,
    news: dict | None = None,
    news_reverse: bool = False,
    intervention: Intervention | None = None,
    roll: float = 100.0,
    unheld_surge_pct: float = 0.0,
    confidence: float = 0.0,
    just_realized_profit: bool = False,
    fgi: float = 0.0,
    crowd_buying: bool = False,
    ignore_streak: int = 0,
    escalation_kind: str | None = None,
    companion: str = "",
) -> DailySnapshot:
    """한 클론의 하루 결정을 §8.6.2 순서로 굴려 DailySnapshot 반환(결정론)."""
    stats = dict(stats)
    avg_cost = float(holding.get("avg_cost", 0.0))
    qty = float(holding.get("quantity", 0.0))

    # [1] 자극 반영 — 뉴스 톤 → 감정 자극(가격 무관 §7.1). 격앙 자극으로 환산.
    escalation_stimulus = 0.0
    if news is not None:
        tone = news.get("tone", "fear")
        coef = clone_spec.news_tone_coef.get(tone, 1.0)
        delta = NEWS.apply_news_to_clone(news, coef=coef, reverse=news_reverse)
        escalation_stimulus = abs(delta.fear_delta) + abs(delta.greed_delta)

    # [2] 컨텍스트 — 운명선(고정) + 보유 평가익
    ohlc = fate_line.day_ohlc(category, day)
    close = ohlc[3] if ohlc else avg_cost
    change_pct = fate_line.change_rate(category, day)
    profit_pct = ((close - avg_cost) / avg_cost * 100.0) if (avg_cost and qty > 0) else 0.0
    holding_loss = profit_pct < 0.0

    ctx = TR.CrisisContext(
        change_pct=change_pct,
        holding_profit_pct=profit_pct,
        unheld_surge_pct=unheld_surge_pct,
        confidence=confidence,
        just_realized_profit=just_realized_profit,
        fgi=fgi,
        crowd_buying=crowd_buying,
    )

    # 선정될 함정의 '관련 내성'을 2층 상태로 미리 집어 격앙도에 반영
    triggered = TR.detect_triggers(ctx)
    related_resilience = 50.0
    if triggered:
        pre_trap = TR.prioritize(triggered, clone_spec.trap_scores)
        stat_name = CSt.stat_for_trap(pre_trap)
        if stat_name in stats:
            related_resilience = stats[stat_name]

    # [3] 함정 판정
    res = run_crisis(CrisisInput(
        ctx=ctx, clone=_profile(clone_spec), vulnerability=clone_spec.trap_scores,
        related_resilience=related_resilience, escalation_stimulus=escalation_stimulus,
        intervention=intervention, roll=roll, holding_loss=holding_loss,
        ignore_streak=ignore_streak, escalation_kind=escalation_kind,
    ))

    # [4] 회계 + 스탯 자동증감. 진짜 평온한 날(트리거 자체 없음)엔 아무 것도 안
    # 움직인다 — "관련" 내성이 특정 함정에 묶여 있으므로(§11.5.1), 관련 함정이
    # 없는 날 전체를 건드리면 8:3:1 비대칭(무너지는 게임 §10)이 희석된다.
    if res.trap is not None:
        CSt.apply_outcome(stats, res.trap, res.stat_outcome)

    # 충동 매도(공포 도피)면 실현손익 확정(§6.5.4). 그 외엔 0(이동 없음/매수).
    realized_pnl = 0.0
    fund_flow = ""
    if res.impulse_trade and res.fund_signal is not None:
        fund_flow = next(
            (k for k, v in _FLOW_FROM_SIGNAL.items() if v == res.fund_signal[1]), ""
        )
        if fund_flow in ("to_cash", "to_stable") and qty > 0:
            realized_pnl = (close - avg_cost) * qty

    total_asset = (holding.get("cash", 0.0) if isinstance(holding, dict) else 0.0) + close * qty

    return DailySnapshot(
        day=day,
        holdings={category: {"quantity": qty, "avg_cost": avg_cost}},
        cash=float(holding.get("cash", 0.0)),
        total_asset=total_asset,
        realized_pnl=realized_pnl,
        trades=[],
        emotion_stats=stats,
        swayed=res.impulse_trade,
        fund_flow=fund_flow,
        companion=companion,
        trap=res.trap,
    )


# fund_destination 신호(함정 ids) → flow 키 역매핑
_FLOW_FROM_SIGNAL = {
    "to_cash": ["F1", "F2"],
    "to_hotter": ["M1", "M2"],
    "concentrate": ["G2"],
    "hold_winner": ["G1"],
}


def simulate_clone_day_multi(
    *,
    clone_spec: CloneSpec,
    stats: dict[str, float],
    fate_line: FateLine,
    category: str,
    day: int,
    holding: dict,
    news: dict | None = None,
    news_reverse: bool = False,
    intervention: Intervention | None = None,
    roll: float = 100.0,
    unheld_surge_pct: float = 0.0,
    confidence: float = 0.0,
    just_realized_profit: bool = False,
    fgi: float = 0.0,
    crowd_buying: bool = False,
    ignore_streak: int = 0,
    escalation_kind: str | None = None,
    companion: str = "",
    surge_category: str | None = None,
    surge_price: float | None = None,
) -> DailySnapshot:
    """T-216 D4 — 다자산 보유 시 §8.6.2를 보유 종목마다 굴려 하루 1위기로 번들.

    §8.5 STEP1을 보유 중인 전 종목(주력+T-215 2차 포지션)에 대해 각각 돌린다.
    단, 다자산 신호(M1 미보유감시·G2 자신감·M2 FGI단톡방)는 개념상 "오늘 클론
    전체의 상태" 하나뿐이라 주력에만 흘려보낸다(§8.3) — 2차 포지션은 스스로
    F1(급락)·F2(마모)·G1(익절거부)만 트리거할 수 있다.

    트리거 0개=평온(기존과 동일), 1개=`simulate_clone_day`와 완전히 같은 결과
    (회귀 없음), 2개 이상=번들 — 같은 전략(A/B/C)이 각 함정에 독립 적용되어
    종목별로 성공/실패가 갈릴 수 있다(§11.4 저항식은 함정마다 다른 취약점·
    관련내성을 쓰므로 같은 roll이어도 결과가 갈린다).
    """
    stats = dict(stats)

    escalation_stimulus = 0.0
    if news is not None:
        tone = news.get("tone", "fear")
        coef = clone_spec.news_tone_coef.get(tone, 1.0)
        delta = NEWS.apply_news_to_clone(news, coef=coef, reverse=news_reverse)
        escalation_stimulus = abs(delta.fear_delta) + abs(delta.greed_delta)

    positions_in = dict(holding.get("positions", {}) or {})
    all_holdings = [(category, float(holding.get("avg_cost", 0.0)), float(holding.get("quantity", 0.0)))]
    all_holdings += [(c, float(p["avg_cost"]), float(p["quantity"])) for c, p in positions_in.items()]

    _close_cache: dict[str, float] = {}

    def close_of(cat: str, fallback: float) -> float:
        if cat not in _close_cache:
            ohlc = fate_line.day_ohlc(cat, day)
            _close_cache[cat] = ohlc[3] if ohlc else fallback
        return _close_cache[cat]

    # STEP1 — 종목별 트리거 감지 + 종목 내 우선순위(§8.5 STEP2, 종목 하나 안에서는 그대로 1개).
    candidates = []
    for cat, avg_cost, qty in all_holdings:
        close = close_of(cat, avg_cost)
        change_pct = fate_line.change_rate(cat, day)
        profit_pct = ((close - avg_cost) / avg_cost * 100.0) if (avg_cost and qty > 0) else 0.0
        is_primary = cat == category
        ctx = TR.CrisisContext(
            change_pct=change_pct,
            holding_profit_pct=profit_pct,
            unheld_surge_pct=unheld_surge_pct if is_primary else 0.0,
            confidence=confidence if is_primary else 0.0,
            just_realized_profit=just_realized_profit if is_primary else False,
            fgi=fgi if is_primary else 0.0,
            crowd_buying=crowd_buying if is_primary else False,
        )
        triggered = TR.detect_triggers(ctx)
        if not triggered:
            continue
        trap_id = TR.prioritize(triggered, clone_spec.trap_scores)
        candidates.append({"category": cat, "avg_cost": avg_cost, "quantity": qty,
                           "close": close, "trap_id": trap_id, "ctx": ctx, "is_primary": is_primary})

    if not candidates:
        total_asset = float(holding.get("cash", 0.0)) + sum(
            qty * close_of(cat, avg_cost) for cat, avg_cost, qty in all_holdings)
        holdings_out = {cat: {"quantity": qty, "avg_cost": avg_cost} for cat, avg_cost, qty in all_holdings}
        return DailySnapshot(
            day=day, holdings=holdings_out, cash=float(holding.get("cash", 0.0)),
            total_asset=round(total_asset, 4), realized_pnl=0.0, trades=[], emotion_stats=stats,
            swayed=False, fund_flow="", companion=companion, trap=None, bundle=[],
        )

    # STEP2~5 — 후보마다 독립 저항 판정(같은 전략, 종목별로 다른 함정 적합도/내성).
    cash = float(holding.get("cash", 0.0))
    positions_out = dict(positions_in)
    primary_avg_cost = float(holding.get("avg_cost", 0.0))
    primary_qty = float(holding.get("quantity", 0.0))
    bundle: list[dict] = []
    total_realized = 0.0

    for c in candidates:
        stat_name = CSt.stat_for_trap(c["trap_id"])
        related_resilience = stats.get(stat_name, 50.0) if stat_name else 50.0
        holding_loss = (c["close"] - c["avg_cost"]) < 0.0 if (c["avg_cost"] and c["quantity"] > 0) else False

        res = run_crisis(CrisisInput(
            ctx=c["ctx"], clone=_profile(clone_spec), vulnerability=clone_spec.trap_scores,
            related_resilience=related_resilience, escalation_stimulus=escalation_stimulus,
            intervention=intervention, roll=roll, holding_loss=holding_loss,
            ignore_streak=ignore_streak, escalation_kind=escalation_kind,
        ))

        if res.trap is not None:
            CSt.apply_outcome(stats, res.trap, res.stat_outcome)

        fund_flow = ""
        realized = 0.0
        if res.impulse_trade and res.fund_signal is not None:
            fund_flow = next((k for k, v in _FLOW_FROM_SIGNAL.items() if v == res.fund_signal[1]), "")
            if c["is_primary"]:
                flow_out = apply_fund_flow(
                    fund_flow, avg_cost=primary_avg_cost, quantity=primary_qty, cash=cash,
                    positions=positions_out, price_today=c["close"],
                    surge_category=surge_category, surge_price=surge_price,
                )
                primary_avg_cost, primary_qty, cash, positions_out, realized = (
                    flow_out["avg_cost"], flow_out["quantity"], flow_out["cash"],
                    flow_out["positions"], flow_out["realized"])
            elif fund_flow in ("to_cash", "to_stable") and c["quantity"] > 0:
                # 2차 포지션은 F1/F2/G1만 트리거 가능(위에서 다자산 신호를 0으로
                # 막아둠) → 여기 도달하는 fund_flow는 to_cash/to_stable뿐(G1의
                # hold_winner는 애초에 이 분기 밖 — 이동 없음).
                realized = (c["close"] - c["avg_cost"]) * c["quantity"]
                cash += c["quantity"] * c["close"]
                positions_out[c["category"]] = {"avg_cost": c["avg_cost"], "quantity": 0.0}

        total_realized += realized
        trap = TR.get_trap(res.trap) if res.trap else None
        bundle.append({
            "category": c["category"], "trap": res.trap,
            "trap_name": trap.name if trap else None,
            "resisted": res.resisted, "reason": res.reason,
            "fund_flow": fund_flow, "realized_pnl": round(realized, 4),
        })

    holdings_out = {category: {"quantity": primary_qty, "avg_cost": primary_avg_cost}}
    for cat, pos in positions_out.items():
        holdings_out[cat] = {"quantity": pos["quantity"], "avg_cost": pos["avg_cost"]}
    total_asset = cash + sum(
        pos["quantity"] * close_of(cat, pos["avg_cost"]) for cat, pos in holdings_out.items())

    return DailySnapshot(
        day=day, holdings=holdings_out, cash=round(cash, 4),
        total_asset=round(total_asset, 4), realized_pnl=round(total_realized, 4),
        trades=[], emotion_stats=stats,
        swayed=any(not b["resisted"] for b in bundle),
        fund_flow=bundle[0]["fund_flow"] if len(bundle) == 1 else "",
        companion=companion, trap=bundle[0]["trap"] if bundle else None, bundle=bundle,
    )
