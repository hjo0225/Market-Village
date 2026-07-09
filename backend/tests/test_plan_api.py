"""§2.2 — 오늘의 일과 편성(플랜) API.

GET /emo/{id}/plan(멱등) + POST(제출·잠금). 예산 초과 400 / 중복 제출 409 /
GET 멱등 / 플랜 반영 후 band_places 일치 / forecast == 실제 정산 적용치(I3) /
미제출 시 기존 자동 루트(I6).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sim import emo_store, place_effects as PE
from sim.emo_api import router


def _client():
    emo_store._clear()
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


ANSWERS = {"q_panic": 0.5, "q_fomo": 0.5, "q_rumor": 0.5, "q_check": 0.5}


def _start(c, seed=42, days=5):
    return c.post("/emo/start", json={"answers": ANSWERS, "seed": seed, "days": days}).json()["game_id"]


# --- GET /plan ---------------------------------------------------------- #
def test_get_plan_returns_budget_bands_and_lock_state():
    c = _client()
    gid = _start(c)
    body = c.get(f"/emo/{gid}/plan").json()
    assert body["day"] == 0
    assert body["budget"] == PE.PLAN_BUDGET
    assert body["locked"] is False
    assert body["current_plan"] is None
    assert set(body["fixed"]) == {"점심"}
    bands = {b["band"]: b for b in body["bands"]}
    assert set(bands) == {"오전", "오후", "저녁"}
    for band in bands.values():
        assert len(band["options"]) == len(PE.PLAN_PLACES)
        for opt in band["options"]:
            assert opt["place"] in PE.PLAN_PLACES
            assert opt["cost"] == PE.place_cost(opt["place"])
            assert opt["forecast"] == PE.place_forecast(opt["place"])
            assert isinstance(opt["npcs"], list)
            assert opt["badges"]
            assert isinstance(opt["flavor"], str)


def test_get_plan_is_idempotent():
    c = _client()
    gid = _start(c)
    a = c.get(f"/emo/{gid}/plan").json()
    b = c.get(f"/emo/{gid}/plan").json()
    assert a == b
    # GET이 상태를 변이하지 않음(state도 그대로).
    st1 = c.get(f"/emo/{gid}/state").json()["emotion"]
    c.get(f"/emo/{gid}/plan")
    st2 = c.get(f"/emo/{gid}/state").json()["emotion"]
    assert st1 == st2


# --- POST /plan: 성공 경로 ------------------------------------------------ #
def test_submit_plan_locks_and_updates_band_places():
    c = _client()
    gid = _start(c)
    plan = {"오전": "카페", "오후": "운동", "저녁": "집"}
    r = c.post(f"/emo/{gid}/plan", json={"plan": plan})
    assert r.status_code == 200
    state = r.json()
    assert state["band_places"]["오전"] == "카페"
    assert state["band_places"]["저녁"] == "집"

    got = c.get(f"/emo/{gid}/plan").json()
    assert got["locked"] is True
    assert got["current_plan"] == plan


# --- POST /plan: 예산 초과 400 ------------------------------------------- #
def test_submit_plan_over_budget_returns_400():
    c = _client()
    gid = _start(c)
    over_budget_place = max(PE.PLAN_PLACES, key=PE.place_cost)
    plan = {b: over_budget_place for b in PE.PLAN_BANDS}
    assert sum(PE.place_cost(plan[b]) for b in PE.PLAN_BANDS) > PE.PLAN_BUDGET
    r = c.post(f"/emo/{gid}/plan", json={"plan": plan})
    assert r.status_code == 400


def test_submit_plan_missing_band_returns_400():
    c = _client()
    gid = _start(c)
    r = c.post(f"/emo/{gid}/plan", json={"plan": {"오전": "카페", "오후": "카페"}})
    assert r.status_code == 400


def test_submit_plan_unknown_place_returns_400():
    c = _client()
    gid = _start(c)
    plan = {"오전": "카페", "오후": "카페", "저녁": "우주정거장"}
    r = c.post(f"/emo/{gid}/plan", json={"plan": plan})
    assert r.status_code == 400


# --- POST /plan: 중복 제출 409 ------------------------------------------- #
def test_submit_plan_twice_returns_409():
    c = _client()
    gid = _start(c)
    plan = {"오전": "카페", "오후": "마켓", "저녁": "집"}
    r1 = c.post(f"/emo/{gid}/plan", json={"plan": plan})
    assert r1.status_code == 200
    r2 = c.post(f"/emo/{gid}/plan", json={"plan": plan})
    assert r2.status_code == 409


# --- I3: forecast == 실제 정산 적용치 ------------------------------------ #
def test_plan_forecast_matches_actual_settlement_deltas():
    c = _client()
    gid = _start(c)
    plan = {"오전": "카페", "오후": "운동", "저녁": "집"}
    plan_body = c.get(f"/emo/{gid}/plan").json()
    bands = {b["band"]: b for b in plan_body["bands"]}
    forecasts = {
        band: next(o for o in bands[band]["options"] if o["place"] == place)["forecast"]
        for band, place in plan.items()
    }
    c.post(f"/emo/{gid}/plan", json={"plan": plan})
    board = c.get(f"/emo/{gid}/board").json()
    choice_id = board["scenario"]["choices"][0]["id"]
    state = c.post(f"/emo/{gid}/choose", json={"choice_id": choice_id}).json()
    settlement = state["settlement"]
    place_steps = [s for s in settlement["emotion_steps"] if s["source"] == "place"]
    assert len(place_steps) == 3
    by_place = {s["place"]: s["deltas"] for s in place_steps}
    for band, place in plan.items():
        # settlement step은 5축 전체(0 포함)를 싣고, forecast는 0이 아닌 축만
        # 담는다(place_effects.place_forecast) — 값은 축마다 동일해야 한다(I3).
        actual = by_place[place]
        expected = forecasts[band]
        for axis, v in expected.items():
            assert actual.get(axis, 0) == v, (band, place, axis)
        for axis, v in actual.items():
            if axis not in expected:
                assert v == 0, (band, place, axis, "forecast에 없는 축이 0이 아님")


# --- I6: 미제출 시 기존 자동 루트 유지 ------------------------------------ #
def test_no_plan_submitted_keeps_legacy_auto_route():
    c = _client()
    gid = _start(c)
    before = c.get(f"/emo/{gid}/state").json()
    board = c.get(f"/emo/{gid}/board").json()
    choice_id = board["scenario"]["choices"][0]["id"]
    state = c.post(f"/emo/{gid}/choose", json={"choice_id": choice_id}).json()
    assert state["day"] == before["day"] + 1
    settlement = state["settlement"]
    # 플랜 미제출 → place 스텝이 없다(자동 루트, 장소 효과 미적용).
    assert not [s for s in settlement["emotion_steps"] if s["source"] == "place"]


def test_plan_get_after_day_advances_shows_fresh_unlocked_plan():
    c = _client()
    gid = _start(c)
    plan = {"오전": "카페", "오후": "마켓", "저녁": "집"}
    c.post(f"/emo/{gid}/plan", json={"plan": plan})
    board = c.get(f"/emo/{gid}/board").json()
    c.post(f"/emo/{gid}/choose", json={"choice_id": board["scenario"]["choices"][0]["id"]})
    got = c.get(f"/emo/{gid}/plan").json()
    assert got["day"] == 1
    assert got["locked"] is False
    assert got["current_plan"] is None
