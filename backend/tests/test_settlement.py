"""§5.1 — 정산 캐스케이드 「선택 → 수익률 → 감정」(choose() 응답의 settlement).

emotion_before + Σsteps == emotion_after(클램프 흡수 포함) / market.pct가
cat_returns와 일치(I1) / settlement 직렬화-복원.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sim import emo_store
from sim.emo_api import router
from sim.emo_game import EmoGameRun
from sim.fate_line import CATEGORIES
from sim.player_emotion.state import AXES, PlayerEmotionState

ANSWERS = {"q_panic": 0.5, "q_fomo": 0.5, "q_rumor": 0.5, "q_check": 0.5}


def _client():
    emo_store._clear()
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _cat(returns):
    return {c: list(returns) for c in CATEGORIES}


# --- emotion_before + Σsteps == emotion_after ---------------------------- #
def test_emotion_before_plus_steps_equals_emotion_after_via_api():
    c = _client()
    gid = c.post("/emo/start", json={"answers": ANSWERS, "seed": 5, "days": 6}).json()["game_id"]
    for _ in range(4):
        board = c.get(f"/emo/{gid}/board").json()
        choice_id = board["scenario"]["choices"][0]["id"]   # 매도(방어) — coin_target 필요
        state = c.post(f"/emo/{gid}/choose",
                       json={"choice_id": choice_id, "coin_target": "meme"}).json()
        settlement = state["settlement"]
        before = settlement["emotion_before"]
        after = settlement["emotion_after"]
        summed = dict(before)
        for step in settlement["emotion_steps"]:
            for axis, v in step["deltas"].items():
                summed[axis] = summed.get(axis, 0) + v
        for axis in AXES:
            assert abs(summed[axis] - after[axis]) < 1e-3, (
                axis, summed[axis], after[axis], settlement["emotion_steps"]
            )
        if state["is_over"]:
            break


def test_emotion_cascade_sum_holds_even_with_clamping():
    # 극단 emotion(포화 근접)에서 클램프가 발동해도 스텝 합이 여전히 정확히 맞아야
    # 한다(스펙: 클램프로 잘린 만큼을 마지막 스텝이 흡수).
    run = EmoGameRun.new(
        ANSWERS, ["market_crash"] * 3, _cat([-0.1] * 3), seed=1,
    )
    run.emotion = PlayerEmotionState(fear=99, greed=1, anxiety=99, restlessness=1, composure=99)
    run.choose("sell", coin_target="meme")
    settlement = run.last_settlement
    before = settlement["emotion_before"]
    after = settlement["emotion_after"]
    summed = dict(before)
    for step in settlement["emotion_steps"]:
        for axis, v in step["deltas"].items():
            summed[axis] = summed.get(axis, 0) + v
    for axis in AXES:
        assert abs(summed[axis] - after[axis]) < 1e-3


# --- I1: market.pct == cat_returns ---------------------------------------- #
def test_settlement_market_pct_matches_cat_returns_untouched_by_choice():
    returns = {"large": [0.05, -0.03], "alt": [0.02, 0.01], "meme": [-0.1, 0.2], "stable": [0.0, 0.0]}
    run_a = EmoGameRun.new(ANSWERS, ["market_crash", "market_surge"], returns, seed=1)
    run_b = EmoGameRun.new(ANSWERS, ["market_crash", "market_surge"], returns, seed=1)
    run_a.choose("sell", coin_target="meme")   # 방어적 선택(매도)
    run_b.choose("buy", coin_target="meme")    # 공격적 선택(매수)
    for cat in CATEGORIES:
        pct_a = next(m["pct"] for m in run_a.last_settlement["market"] if m["category"] == cat)
        pct_b = next(m["pct"] for m in run_b.last_settlement["market"] if m["category"] == cat)
        expected = round(returns.get(cat, [0.0])[0] * 100, 2)
        assert pct_a == expected == pct_b, (
            "선택이 시장 수익률에 영향을 줌(I1 위반)", cat, pct_a, pct_b, expected
        )


def test_settlement_choice_only_affects_rebalance_not_market():
    run = EmoGameRun.new(ANSWERS, ["market_crash"], _cat([-0.1]), seed=1)
    run.choose("sell", coin_target="meme")
    settlement = run.last_settlement
    assert settlement["choice"]["id"] == "sell"
    assert "rebalance" in settlement
    assert "risk_share_before" in settlement["rebalance"]
    assert "risk_share_after" in settlement["rebalance"]
    # sell(매도, position<0)은 지정 위험코인을 현금화해 위험 비중을 낮춘다.
    assert settlement["rebalance"]["risk_share_after"] <= settlement["rebalance"]["risk_share_before"]


# --- settlement 직렬화-복원 ------------------------------------------------ #
def test_settlement_survives_serialization_roundtrip():
    run = EmoGameRun.new(ANSWERS, ["market_crash", "market_surge"], _cat([-0.1, 0.1]), seed=1)
    run.choose("sell", coin_target="meme")
    doc = run.to_doc()
    assert doc["last_settlement"] == run.last_settlement
    restored = EmoGameRun.from_doc(doc)
    assert restored.last_settlement == run.last_settlement


def test_state_endpoint_includes_settlement_after_choose():
    c = _client()
    gid = c.post("/emo/start", json={"answers": ANSWERS, "seed": 3, "days": 4}).json()["game_id"]
    st0 = c.get(f"/emo/{gid}/state").json()
    assert st0["settlement"] is None   # 아직 정산 전
    board = c.get(f"/emo/{gid}/board").json()
    choice_id = board["scenario"]["choices"][0]["id"]
    after_choose = c.post(f"/emo/{gid}/choose",
                          json={"choice_id": choice_id, "coin_target": "meme"}).json()
    assert after_choose["settlement"] is not None
    # 다음 GET에도 마지막 정산이 유지된다(스펙 §5.1 "구현 단순한 쪽").
    st1 = c.get(f"/emo/{gid}/state").json()
    assert st1["settlement"] == after_choose["settlement"]


def test_settlement_choice_label_and_position_present():
    c = _client()
    gid = c.post("/emo/start", json={"answers": ANSWERS, "seed": 3, "days": 4}).json()["game_id"]
    board = c.get(f"/emo/{gid}/board").json()
    chosen = board["scenario"]["choices"][0]
    state = c.post(f"/emo/{gid}/choose",
                   json={"choice_id": chosen["id"], "coin_target": "meme"}).json()
    settlement = state["settlement"]
    assert settlement["choice"]["id"] == chosen["id"]
    assert settlement["choice"]["label"] == chosen["label"]
    assert settlement["choice"]["position"] == chosen["position"]
    assert settlement["day"] == 0
