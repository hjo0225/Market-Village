"""T-210 · §8.3 충동매매 자금 행선지 → 실제 포트폴리오 이동 (순수함수).

지금까지 to_cash/to_stable(전량 매도)만 구현돼 있었다 — to_hotter(M1/M2 추격
매수)·concentrate(G2 몰빵)는 함정이 판정까지는 나도 포트폴리오에 아무 효과가
없어(무시됨) 사실상 죽어있었다. 이 모듈은 그 자금 이동 자체만 순수하게 검증한다
(트리거 판정 파이프라인은 건드리지 않음 — 국소 변경).
"""

from __future__ import annotations

from sim.run_loop import apply_fund_flow


def test_to_cash_sells_all_realizes_pnl():
    r = apply_fund_flow("to_cash", avg_cost=100.0, quantity=2.0, cash=0.0,
                        positions={}, price_today=150.0)
    assert r["quantity"] == 0.0
    assert r["cash"] == 300.0
    assert r["realized"] == 100.0   # (150-100)*2


def test_to_hotter_chases_surge_category_with_half_cash():
    r = apply_fund_flow("to_hotter", avg_cost=100.0, quantity=0.0, cash=200.0,
                        positions={}, price_today=100.0,
                        surge_category="meme", surge_price=50.0)
    assert r["cash"] == 100.0                              # 절반만 태움
    assert r["positions"]["meme"]["quantity"] == 2.0        # 100/50
    assert r["realized"] == 0.0                             # 실현손익 아님(신규 매수)


def test_to_hotter_no_cash_does_nothing():
    r = apply_fund_flow("to_hotter", avg_cost=100.0, quantity=1.0, cash=0.0,
                        positions={}, price_today=100.0,
                        surge_category="meme", surge_price=50.0)
    assert r["cash"] == 0.0
    assert r["positions"] == {}


def test_to_hotter_adds_to_existing_secondary_position():
    r = apply_fund_flow("to_hotter", avg_cost=100.0, quantity=0.0, cash=100.0,
                        positions={"meme": {"avg_cost": 40.0, "quantity": 1.0}},
                        price_today=100.0, surge_category="meme", surge_price=50.0)
    assert r["positions"]["meme"]["quantity"] == 2.0   # 1.0 + (50/50)


def test_concentrate_buys_more_of_primary_weighted_avg_cost():
    r = apply_fund_flow("concentrate", avg_cost=100.0, quantity=1.0, cash=100.0,
                        positions={}, price_today=200.0)
    # 현금 절반(50) → 200에 0.25주 추가. 새 평단 = (100*1 + 200*0.25)/1.25 = 120
    assert r["quantity"] == 1.25
    assert round(r["avg_cost"], 2) == 120.0
    assert r["cash"] == 50.0


def test_concentrate_no_cash_does_nothing():
    r = apply_fund_flow("concentrate", avg_cost=100.0, quantity=1.0, cash=0.0,
                        positions={}, price_today=200.0)
    assert r["quantity"] == 1.0
    assert r["avg_cost"] == 100.0


def test_unknown_flow_is_noop():
    r = apply_fund_flow("", avg_cost=100.0, quantity=1.0, cash=50.0,
                        positions={}, price_today=200.0)
    assert r == {"avg_cost": 100.0, "quantity": 1.0, "cash": 50.0,
                "positions": {}, "realized": 0.0}
