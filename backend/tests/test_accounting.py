"""T-103 · §6.5 가격수용자 회계 완성 — 실현손익 + 자금 행선지.

기존 평단(_merge_buy)·매도(_reduce_sell)는 정확. 빠진 두 가지를 채운다:
  (1) 매도 시 실현손익 = (P − avg_cost) × q  (§6.5.4)
  (2) 자금 행선지 분류 (§6.5.5/§8.3) — 매도 대금이 어디로 가는지가 감정을 드러냄.
"""

from __future__ import annotations

from sim.models import Action, Asset, Agent, PortfolioHolding, TradeDecision
from sim import trade


def _agent(cash=10_000.0, holdings=None):
    return Agent(
        id="clone", alias="클론", type="player_clone", sprite="", cash=cash,
        portfolio=holdings or [],
    )


def _assets(price=120.0):
    return {"A": Asset(symbol="A", name="A", price=price)}


# --- 실현손익 (§6.5.4) --------------------------------------------------- #
def test_realized_pnl_on_profitable_sell():
    # 평단 100에 10개 보유, 120에 4개 매도 → 실현손익 = (120−100)×4 = 80
    ag = _agent(holdings=[PortfolioHolding(asset="A", amount=10.0, avgPrice=100.0)])
    dec = TradeDecision(agent_id="clone", action=Action.SELL, symbol="A", qty=4.0)
    res = trade.execute_trade(dec, ag, _assets(price=120.0))
    assert res.realized_pnl == 80.0
    # 남은 물량 평단은 불변 (§6.5.4)
    held = ag.holding("A")
    assert held.amount == 6.0
    assert held.avgPrice == 100.0


def test_realized_pnl_loss():
    ag = _agent(holdings=[PortfolioHolding(asset="A", amount=5.0, avgPrice=200.0)])
    dec = TradeDecision(agent_id="clone", action=Action.SELL, symbol="A", qty=5.0)
    res = trade.execute_trade(dec, ag, _assets(price=150.0))
    assert res.realized_pnl == (150.0 - 200.0) * 5.0  # −250
    assert ag.holding("A") is None  # 전량 매도 → 드롭


def test_buy_has_zero_realized_pnl():
    ag = _agent(cash=1000.0)
    dec = TradeDecision(agent_id="clone", action=Action.BUY, symbol="A", qty=2.0)
    res = trade.execute_trade(dec, ag, _assets(price=100.0))
    assert res.realized_pnl == 0.0
    # 평단 가중평균은 기존대로
    assert ag.holding("A").avgPrice == 100.0


def test_weighted_avg_cost_still_correct():
    # 회귀 가드: 100에 2개 보유 → 200에 2개 추가매수 → 평단 150
    ag = _agent(cash=1000.0, holdings=[PortfolioHolding(asset="A", amount=2.0, avgPrice=100.0)])
    dec = TradeDecision(agent_id="clone", action=Action.BUY, symbol="A", qty=2.0)
    trade.execute_trade(dec, ag, _assets(price=200.0))
    held = ag.holding("A")
    assert held.amount == 4.0
    assert held.avgPrice == 150.0


# --- 자금 행선지 (§6.5.5 / §8.3) ---------------------------------------- #
def test_fund_destination_signals():
    # 매도 → 현금/스테이블 유지 → 공포 (F1/F2)
    emo, traps = trade.fund_destination("to_cash")
    assert traps == ["F1", "F2"]
    emo, traps = trade.fund_destination("to_stable")
    assert traps == ["F1", "F2"]
    # 매도 → 더 뜨거운 종목 → FOMO (M1/M2)
    _, traps = trade.fund_destination("to_hotter")
    assert traps == ["M1", "M2"]
    # 한 종목 집중 → 과대베팅 (G2)
    _, traps = trade.fund_destination("concentrate")
    assert traps == ["G2"]
    # 수익 종목 미매도(이동 없음) → 익절거부 (G1)
    _, traps = trade.fund_destination("hold_winner")
    assert traps == ["G1"]


def test_fund_destination_unknown_is_neutral():
    emo, traps = trade.fund_destination("whatever")
    assert traps == []
