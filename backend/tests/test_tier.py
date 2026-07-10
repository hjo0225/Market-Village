"""v3 §C2 — 통제 티어(목표 위젯): tier_score/tier_for_score/compute_tier + _state().

5티어 경계값 / 결정론(상태에서만 파생, 저장 없음) / next_at / 이름이 스펙
문자열 그대로(새싹/불개미 졸업/평정 수련/강철 멘탈/마을의 현자)인지.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sim import emo_store
from sim import tier as T
from sim.emo_api import router
from sim.emo_game import EmoGameRun
from sim.fate_line import CATEGORIES
from sim.player_emotion.state import PlayerEmotionState

ANSWERS = {"Q1": 2, "Q2": 2, "Q3": 2, "Q4": 2, "Q5": 2, "Q6": 2, "Q7": 2}


def _client():
    emo_store._clear()
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# --- 이름/아이콘 스펙 문자열 그대로 ------------------------------------------ #
def test_tier_names_match_spec_exactly():
    assert T.TIER_NAMES == ("새싹", "불개미 졸업", "평정 수련", "강철 멘탈", "마을의 현자")


# --- 경계값 ------------------------------------------------------------------ #
def test_tier_for_score_boundaries_lower_bound_inclusive():
    assert T.tier_for_score(0)["name"] == "새싹"
    assert T.tier_for_score(34.99)["name"] == "새싹"
    assert T.tier_for_score(35)["name"] == "불개미 졸업"
    assert T.tier_for_score(54.99)["name"] == "불개미 졸업"
    assert T.tier_for_score(55)["name"] == "평정 수련"
    assert T.tier_for_score(71.99)["name"] == "평정 수련"
    assert T.tier_for_score(72)["name"] == "강철 멘탈"
    assert T.tier_for_score(87.99)["name"] == "강철 멘탈"
    assert T.tier_for_score(88)["name"] == "마을의 현자"


def test_tier_for_score_negative_clamped_to_first_tier():
    # tier_score()는 max(0, ...)로 클램프하지만 tier_for_score 자체도 방어적으로.
    assert T.tier_for_score(-10)["name"] == "새싹"


def test_tier_next_at_present_except_top_tier():
    assert T.tier_for_score(0)["next_at"] == 35.0
    assert T.tier_for_score(35)["next_at"] == 55.0
    assert T.tier_for_score(55)["next_at"] == 72.0
    assert T.tier_for_score(72)["next_at"] == 88.0
    assert T.tier_for_score(88)["next_at"] is None   # 최고 티어 — 더 오를 곳 없음


def test_tier_for_score_shape():
    out = T.tier_for_score(50)
    assert set(out) == {"name", "icon", "score", "next_at"}
    assert out["score"] == 50


# --- tier_score: 기존 지표(composure/편차) + special_event_count 재사용 ------ #
def test_tier_score_uses_composure_directly_when_neutral_emotion():
    # 4부정축이 0이면 compute_score=0(편차 없음) → score == composure.
    e = PlayerEmotionState(fear=0, greed=0, anxiety=0, restlessness=0, composure=60)
    assert T.tier_score(e, special_event_count=0) == 60.0


def test_tier_score_penalizes_emotion_deviation():
    neutral = PlayerEmotionState(fear=0, greed=0, anxiety=0, restlessness=0, composure=50)
    skewed = PlayerEmotionState(fear=0, greed=80, anxiety=0, restlessness=80, composure=50)
    assert T.tier_score(skewed, 0) < T.tier_score(neutral, 0)


def test_tier_score_special_event_bonus_increases_score():
    e = PlayerEmotionState(fear=0, greed=0, anxiety=0, restlessness=0, composure=50)
    base = T.tier_score(e, special_event_count=0)
    boosted = T.tier_score(e, special_event_count=3)
    assert boosted > base
    assert boosted - base == 3 * 3.0   # _SPECIAL_EVENT_BONUS=3.0/건


def test_tier_score_never_negative():
    worst = PlayerEmotionState(fear=100, greed=100, anxiety=100, restlessness=100, composure=0)
    assert T.tier_score(worst, 0) >= 0.0


def test_compute_tier_is_pure_and_deterministic():
    e = PlayerEmotionState(fear=10, greed=20, anxiety=5, restlessness=15, composure=55)
    a = T.compute_tier(e, 2)
    b = T.compute_tier(e, 2)
    assert a == b


# --- _state()에 tier 포함 ----------------------------------------------------- #
def test_state_includes_tier_with_expected_shape():
    c = _client()
    gid = c.post("/emo/start", json={"answers": ANSWERS, "seed": 1, "days": 5}).json()["game_id"]
    body = c.get(f"/emo/{gid}/state").json()
    assert "tier" in body
    assert set(body["tier"]) == {"name", "icon", "score", "next_at"}
    assert body["tier"]["name"] in T.TIER_NAMES


def test_tier_not_persisted_purely_derived_each_call():
    # 새 상태 저장 없이 emotion/special_event_count로만 파생 — to_doc에 별도
    # 'tier' 키가 없어야 한다(저장 안 함, 스펙 "score는 상태에서 파생").
    run = EmoGameRun.new(ANSWERS, ["market_crash"] * 3, {c: [0.0] * 3 for c in CATEGORIES}, seed=1)
    doc = run.to_doc()
    assert "tier" not in doc


def test_tier_changes_when_special_event_count_changes_state_unchanged_otherwise():
    c = _client()
    gid = c.post("/emo/start", json={"answers": ANSWERS, "seed": 1, "days": 5}).json()["game_id"]
    t0 = c.get(f"/emo/{gid}/state").json()["tier"]
    t1 = c.get(f"/emo/{gid}/state").json()["tier"]
    assert t0 == t1   # GET 멱등 — 상태 안 바뀌면 tier도 안 바뀐다.
