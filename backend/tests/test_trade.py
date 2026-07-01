"""Tests for FR-5 trade decision + execution (sim/trade.py)."""

from __future__ import annotations

from sim.models import (
    Action,
    Agent,
    Asset,
    MarketData,
    PortfolioHolding,
)
from sim.trade import decide_trade, execute_trade, run_trades


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #
def _asset(symbol: str = "BTC", price: float = 100.0) -> Asset:
    return Asset(symbol=symbol, name=symbol, price=price)


def _assets(*assets: Asset) -> dict[str, Asset]:
    if not assets:
        assets = (_asset(),)
    return {a.symbol: a for a in assets}


def _agent(
    agent_id: str,
    atype: str,
    cash: float = 10_000.0,
    fear: float = 50.0,
    greed: float = 50.0,
    holdings: list[PortfolioHolding] | None = None,
    fear_threshold: float | None = None,
) -> Agent:
    return Agent(
        id=agent_id,
        alias=agent_id,
        type=atype,
        sprite="s.png",
        cash=cash,
        fear=fear,
        greed=greed,
        portfolio=holdings or [],
        fear_threshold=fear_threshold,
    )


def _hold(symbol: str = "BTC", amount: float = 10.0, avg: float = 90.0) -> PortfolioHolding:
    return PortfolioHolding(asset=symbol, amount=amount, avgPrice=avg)


# --------------------------------------------------------------------------- #
# run_trades: once-per-round + deterministic order
# --------------------------------------------------------------------------- #
def test_trade_executed_once_per_round():
    assets = _assets()
    agents = [
        _agent("a1", "panic_seller", fear=90, holdings=[_hold()]),
        _agent("a2", "fomo_trader", greed=90),
        _agent("a3", "news_bot"),
    ]
    results = run_trades(agents, assets)
    assert len(results) == len(agents)
    assert {r.agent_id for r in results} == {"a1", "a2", "a3"}


def test_trades_run_in_plan_order():
    assets = _assets()
    # Pass in deliberately unsorted order; results must come back sorted by id.
    agents = [
        _agent("c", "news_bot"),
        _agent("a", "news_bot"),
        _agent("b", "news_bot"),
    ]
    results = run_trades(agents, assets)
    assert [r.agent_id for r in results] == ["a", "b", "c"]


# --------------------------------------------------------------------------- #
# Clamping
# --------------------------------------------------------------------------- #
def test_qty_within_cash():
    assets = _assets(_asset("BTC", price=100.0))
    # fomo wants to buy; cash is small so spend must be clamped.
    agent = _agent("a", "fomo_trader", cash=50.0, greed=99)
    decision = decide_trade(agent, assets)
    result = execute_trade(decision, agent, assets)
    assert result.action == Action.BUY
    assert result.qty * result.price <= 50.0 + 1e-9
    assert result.cash_after >= 0.0
    assert agent.cash >= 0.0


def test_qty_within_holdings():
    assets = _assets(_asset("BTC", price=100.0))
    agent = _agent("a", "panic_seller", fear=95, holdings=[_hold("BTC", amount=4.0)])
    decision = decide_trade(agent, assets)
    result = execute_trade(decision, agent, assets)
    assert result.action == Action.SELL
    assert result.qty <= 4.0 + 1e-9
    held = agent.holding("BTC")
    remaining = held.amount if held is not None else 0.0
    assert remaining >= 0.0


# --------------------------------------------------------------------------- #
# Persona rules
# --------------------------------------------------------------------------- #
def test_panic_seller_sells_on_high_fear():
    assets = _assets(_asset("BTC", price=100.0))
    agent = _agent("a", "panic_seller", fear=90, holdings=[_hold("BTC", amount=10.0)])
    before = agent.holding("BTC").amount
    decision = decide_trade(agent, assets)
    assert decision.action == Action.SELL
    execute_trade(decision, agent, assets)
    after = agent.holding("BTC").amount if agent.holding("BTC") else 0.0
    assert after < before


def test_whale_buy_large_on_fear_spike():
    assets = _assets(_asset("BTC", price=100.0))
    agent = _agent("a", "whale", cash=100_000.0)
    market = MarketData(fearGreedIndex=10.0)  # extreme fear
    cash_before = agent.cash
    decision = decide_trade(agent, assets, market)
    assert decision.action == Action.BUY_LARGE
    result = execute_trade(decision, agent, assets)
    assert result.cash_after < cash_before
    assert agent.cash < cash_before


def test_value_investor_never_panic_sells():
    assets = _assets(_asset("BTC", price=100.0))
    agent = _agent("a", "value_investor", fear=90, greed=10, holdings=[_hold("BTC")])
    decision = decide_trade(agent, assets)
    assert decision.action != Action.SELL  # HOLD here; never panic-sells


def test_execute_updates_cash_and_portfolio():
    assets = _assets(_asset("BTC", price=100.0))
    agent = _agent("a", "fomo_trader", cash=1_000.0, greed=99)
    cash_before = agent.cash
    decision = decide_trade(agent, assets)
    assert decision.action == Action.BUY
    result = execute_trade(decision, agent, assets)
    held = agent.holding(result.symbol)
    assert held is not None
    assert held.amount > 0.0
    # cash decreased by exactly qty*price
    assert abs((cash_before - agent.cash) - result.qty * result.price) < 1e-6
    assert agent.lastAction == Action.BUY.value


# --------------------------------------------------------------------------- #
# Extra coverage for the remaining personas / no-op paths
# --------------------------------------------------------------------------- #
def test_news_bot_always_holds():
    assets = _assets()
    agent = _agent("a", "news_bot", fear=99, greed=99, holdings=[_hold()])
    assert decide_trade(agent, assets).action == Action.HOLD


def test_contrarian_sells_on_extreme_greed():
    assets = _assets(_asset("BTC", price=100.0))
    agent = _agent("a", "contrarian", holdings=[_hold("BTC", amount=10.0)])
    market = MarketData(fearGreedIndex=85.0)
    assert decide_trade(agent, assets, market).action == Action.SELL


def test_quant_buys_on_greed_signal_sells_on_fear_signal():
    assets = _assets(_asset("BTC", price=100.0))
    greedy = _agent("g", "quant", greed=80, fear=20)
    fearful = _agent("f", "quant", greed=20, fear=80, holdings=[_hold("BTC")])
    flat = _agent("n", "quant", greed=50, fear=50)
    assert decide_trade(greedy, assets).action == Action.BUY
    assert decide_trade(fearful, assets).action == Action.SELL
    assert decide_trade(flat, assets).action == Action.HOLD


def test_hold_is_noop_on_cash_and_portfolio():
    assets = _assets()
    agent = _agent("a", "news_bot", cash=500.0, holdings=[_hold()])
    result = execute_trade(decide_trade(agent, assets), agent, assets)
    assert result.action == Action.HOLD
    assert agent.cash == 500.0
    assert result.cash_after == 500.0
