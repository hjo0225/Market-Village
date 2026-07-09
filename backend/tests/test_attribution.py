"""v3 §C1 — 원인 카드(attribution): counterfactual_holdings + settlement.attribution.

수학 검증(actual/counterfactual pnl, delta) / day0(전날 없음) 생략 /
counterfactual_holdings 직렬화-복원 / 4종 정적 템플릿(방어성공/방어손해/
공격성공/공격손해).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sim import emo_store
from sim.emo_api import router
from sim.emo_game import CASH, EmoGameRun
from sim.fate_line import CATEGORIES

ANSWERS = {"Q1": 2, "Q2": 2, "Q3": 2, "Q4": 2, "Q5": 2, "Q6": 2, "Q7": 2}


def _client():
    emo_store._clear()
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _cat(returns):
    return {c: list(returns) for c in CATEGORIES}


# --- day 0: attribution 생략 ------------------------------------------------ #
def test_attribution_absent_on_day_zero():
    run = EmoGameRun.new(ANSWERS, ["market_crash"] * 3, _cat([-0.1, 0.05, 0.02]), seed=1)
    run.choose("cut")
    assert run.last_settlement["attribution"] is None


def test_attribution_absent_on_day_zero_via_api():
    c = _client()
    gid = c.post("/emo/start", json={"answers": ANSWERS, "seed": 1, "days": 3}).json()["game_id"]
    board = c.get(f"/emo/{gid}/board").json()
    state = c.post(f"/emo/{gid}/choose", json={"choice_id": board["scenario"]["choices"][0]["id"]}).json()
    assert state["settlement"]["attribution"] is None


# --- counterfactual_holdings 저장(정산 직후·리밸런스 전) --------------------- #
def test_counterfactual_holdings_saved_post_market_pre_rebalance():
    run = EmoGameRun.new(ANSWERS, ["market_crash"] * 2, _cat([-0.1, 0.05]), seed=1)
    even = 1_000_000 / 5
    run.choose("cut")   # position -0.6(방어) → cut 이후 위험자산이 줄어든 holdings와는 달라야 함
    # counterfactual = 시장 실현만 반영(각 카테고리 -10%), 리밸런스는 미반영.
    expected = round(even * 0.9, 2)
    for cat in CATEGORIES:
        assert run.counterfactual_holdings[cat] == expected
    assert run.counterfactual_holdings[CASH] == even   # cash는 시장 수익률 0, 리밸런스 전이라 불변
    # 실제 holdings는 cut(손절)으로 위험자산 → 현금 이동이 반영돼 달라야 한다.
    assert run.holdings != run.counterfactual_holdings


# --- 수학 검증 --------------------------------------------------------------- #
def test_attribution_math_matches_hand_computation():
    # day0: -10% 전 카테고리, cut(방어, position -0.6) → 위험자산 상당 부분이 현금화.
    # day1: +5% 반등 → 방어가 반등을 놓쳤어야 하므로 delta<0(counterfactual이 더 좋음).
    run = EmoGameRun.new(ANSWERS, ["market_crash"] * 3, _cat([-0.1, 0.05, 0.0]), seed=1)
    run.choose("cut")
    cf_snapshot = dict(run.counterfactual_holdings)
    run.choose("cut")
    attr = run.last_settlement["attribution"]

    cf_before = sum(cf_snapshot.values())
    cf_after = sum(cf_snapshot[c] * 1.05 for c in CATEGORIES) + cf_snapshot[CASH]
    expected_cf_pnl = round((cf_after - cf_before) / cf_before * 100, 2)

    # settlement.portfolio가 이미 실제(actual) before/after/pnl_pct를 담고 있다.
    portfolio = run.last_settlement["portfolio"]
    expected_actual_pnl = portfolio["pnl_pct"]

    assert attr["counterfactual_pnl_pct"] == expected_cf_pnl
    assert attr["actual_pnl_pct"] == expected_actual_pnl
    assert attr["delta_pct"] == round(expected_actual_pnl - expected_cf_pnl, 2)


def test_attribution_delta_pct_equals_actual_minus_counterfactual():
    run = EmoGameRun.new(ANSWERS, ["market_crash"] * 3, _cat([-0.1, 0.05, 0.03]), seed=2)
    run.choose("cut")
    run.choose("hold")
    attr = run.last_settlement["attribution"]
    assert attr["delta_pct"] == round(attr["actual_pnl_pct"] - attr["counterfactual_pnl_pct"], 2)


def test_attribution_cause_choice_label_is_previous_days_choice():
    run = EmoGameRun.new(ANSWERS, ["market_crash"] * 3, _cat([-0.1, 0.05, 0.0]), seed=1)
    run.choose("plan_check")   # "미리 정해둔 손절선만 확인하고 앱을 끈다"
    run.choose("cut")
    attr = run.last_settlement["attribution"]
    assert attr["cause_choice_label"] == "미리 정해둔 손절선만 확인하고 앱을 끈다"


# --- 4종 정적 템플릿 ---------------------------------------------------------- #
def test_attribution_text_defense_success_when_avoided_bigger_loss():
    # 방어(position<0) 후 시장이 더 빠졌다면(반사실이 더 나빴다면) "성공" 문구.
    run = EmoGameRun.new(ANSWERS, ["market_crash"] * 3, _cat([-0.05, -0.3, 0.0]), seed=1)
    run.choose("cut")   # position -0.6
    run.choose("cut")
    attr = run.last_settlement["attribution"]
    assert attr["delta_pct"] >= 0
    assert "덕분에" in attr["text"]
    assert "대신" in attr["text"]


def test_attribution_text_defense_loss_when_missed_rebound():
    # 방어 후 시장이 반등했다면(반사실이 더 좋았다면) "손해" 문구.
    run = EmoGameRun.new(ANSWERS, ["market_crash"] * 3, _cat([-0.1, 0.2, 0.0]), seed=1)
    run.choose("cut")   # position -0.6(방어)
    run.choose("cut")
    attr = run.last_settlement["attribution"]
    assert attr["delta_pct"] < 0
    assert "오히려" in attr["text"]


def test_attribution_text_aggressive_success_when_rally_continues():
    run = EmoGameRun.new(ANSWERS, ["market_surge"] * 3, _cat([0.1, 0.15, 0.0]), seed=1)
    run.choose("all_in_reserve")   # position 0.6(공격)
    run.choose("chase")
    attr = run.last_settlement["attribution"]
    assert attr["delta_pct"] >= 0
    assert "더 태운 덕분에" in attr["text"]


def test_attribution_text_aggressive_loss_when_reversal_hits():
    run = EmoGameRun.new(ANSWERS, ["market_surge"] * 3, _cat([0.1, -0.2, 0.0]), seed=1)
    run.choose("all_in_reserve")   # position 0.6(공격)
    run.choose("chase")
    attr = run.last_settlement["attribution"]
    assert attr["delta_pct"] < 0
    assert "더 물렸다" in attr["text"]


# --- 직렬화-복원 ------------------------------------------------------------- #
def test_counterfactual_holdings_survive_serialization_roundtrip():
    run = EmoGameRun.new(ANSWERS, ["market_crash"] * 3, _cat([-0.1, 0.05, 0.0]), seed=1)
    run.choose("cut")
    doc = run.to_doc()
    assert doc["counterfactual_holdings"] == run.counterfactual_holdings
    assert doc["counterfactual_choice_label"] == run.counterfactual_choice_label
    restored = EmoGameRun.from_doc(doc)
    assert restored.counterfactual_holdings == run.counterfactual_holdings
    assert restored.counterfactual_choice_label == run.counterfactual_choice_label
    assert restored.counterfactual_choice_position == run.counterfactual_choice_position
    # 복원 후에도 다음날 attribution이 정상 계산돼야 한다.
    restored.choose("cut")
    assert restored.last_settlement["attribution"] is not None


def test_from_doc_without_counterfactual_fields_defaults_to_none():
    # 구 doc(신 필드 없음) 복원 — attribution 없이도 크래시 없이 동작(하위 호환).
    run = EmoGameRun.new(ANSWERS, ["market_crash"] * 2, _cat([-0.1, 0.05]), seed=1)
    doc = run.to_doc()
    del doc["counterfactual_holdings"]
    del doc["counterfactual_choice_label"]
    del doc["counterfactual_choice_position"]
    restored = EmoGameRun.from_doc(doc)
    assert restored.counterfactual_holdings is None
    assert restored.counterfactual_choice_position == 0.0


# --- API 계약 ---------------------------------------------------------------- #
def test_attribution_present_in_settlement_via_api_after_day1():
    c = _client()
    gid = c.post("/emo/start", json={"answers": ANSWERS, "seed": 5, "days": 4}).json()["game_id"]
    board0 = c.get(f"/emo/{gid}/board").json()
    c.post(f"/emo/{gid}/choose", json={"choice_id": board0["scenario"]["choices"][0]["id"]})
    board1 = c.get(f"/emo/{gid}/board").json()
    state = c.post(f"/emo/{gid}/choose", json={"choice_id": board1["scenario"]["choices"][0]["id"]}).json()
    attr = state["settlement"]["attribution"]
    assert attr is not None
    assert set(attr) == {
        "actual_pnl_pct", "counterfactual_pnl_pct", "delta_pct",
        "cause_choice_label", "text",
    }
