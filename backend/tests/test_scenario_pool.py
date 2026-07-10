"""T-53 (F4) — 게시판 선택지 = 3액션(매수/매도/유지, 버킷 방어/관망/공격 각 1개).

풀 자체가 3개라 노출 = 3개 전부(버킷 스펙트럼 보장). 3액션 전부 get_choice로
조회 가능하고, 그 밖의 id로 POST /choose 하면 400(노출 게이트).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sim import emo_store
from sim.emo_api import router
from sim.scenario import (
    EVENT_CATEGORIES,
    _bucket_of,
    get_choice,
    get_scenario,
    load_scenarios,
    pick_exposed_choices,
)


def _client():
    emo_store._clear()
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


ANSWERS = {"q_panic": 0.5, "q_fomo": 0.5, "q_rumor": 0.5, "q_check": 0.5}


# ── 결정론 ────────────────────────────────────────────────────────────────
def test_same_seed_day_event_gives_same_three_choices():
    for event_id in EVENT_CATEGORIES:
        a = get_scenario(event_id, seed=7, day=2)["choices"]
        b = get_scenario(event_id, seed=7, day=2)["choices"]
        assert [c["id"] for c in a] == [c["id"] for c in b]


# ── 버킷 스펙트럼 보장 ───────────────────────────────────────────────────
def test_exposed_three_always_span_all_three_buckets():
    for event_id in EVENT_CATEGORIES:
        for day in range(10):
            sc = get_scenario(event_id, seed=3, day=day)
            choices = sc["choices"]
            assert len(choices) == 3
            buckets = {_bucket_of(float(c["position"])) for c in choices}
            assert buckets == {"defense", "neutral", "aggressive"}, (event_id, day, choices)


def test_pick_exposed_choices_returns_one_per_bucket():
    # T-53: 풀 자체가 3액션(버킷당 1개)이라 노출 = 3개 전부(버킷당 1개).
    scenarios = load_scenarios()
    for event_id in EVENT_CATEGORIES:
        all_choices = scenarios[event_id]["choices"]
        assert len(all_choices) == 3
        exposed = pick_exposed_choices(all_choices, seed=1, day=1, event_id=event_id)
        assert len(exposed) == 3


# ── 3액션 전부 get_choice로 조회 가능 ────────────────────────────────────
def test_all_three_actions_reachable_via_get_choice():
    scenarios = load_scenarios()
    for event_id in EVENT_CATEGORIES:
        for ch in scenarios[event_id]["choices"]:
            found = get_choice(event_id, ch["id"])
            assert found["id"] == ch["id"]


def test_get_scenario_without_seed_day_returns_full_set_of_three():
    # 레거시 호출부(seed/day 생략) 하위 호환 — 3액션 전부.
    for event_id in EVENT_CATEGORIES:
        assert len(get_scenario(event_id)["choices"]) == 3


# ── GET board 멱등 + 노출 3개 ────────────────────────────────────────────
def test_board_get_exposes_exactly_three_choices_idempotently():
    c = _client()
    gid = c.post("/emo/start", json={"answers": ANSWERS, "seed": 11, "days": 5}).json()["game_id"]
    b1 = c.get(f"/emo/{gid}/board").json()
    b2 = c.get(f"/emo/{gid}/board").json()
    assert len(b1["scenario"]["choices"]) == 3
    assert b1["scenario"]["choices"] == b2["scenario"]["choices"]   # GET 멱등(I4)


# ── 노출 안 된 id로 choose → 400 ────────────────────────────────────────
def test_choose_with_unexposed_choice_id_returns_400():
    # T-53: 노출 = 3액션(buy/sell/hold) 전부. 그 밖의 id(옛 제거된 선택지 등)로
    # choose 하면 엔드포인트의 노출 게이트가 400으로 막는다.
    c = _client()
    gid = c.post("/emo/start", json={"answers": ANSWERS, "seed": 11, "days": 5}).json()["game_id"]
    board = c.get(f"/emo/{gid}/board").json()
    exposed_ids = {ch["id"] for ch in board["scenario"]["choices"]}
    bad_id = "buy_dip"   # T-53으로 제거된 옛 선택지 id — 오늘 노출에 없다
    assert bad_id not in exposed_ids
    r = c.post(f"/emo/{gid}/choose", json={"choice_id": bad_id})
    assert r.status_code == 400


def test_choose_with_exposed_choice_id_succeeds():
    c = _client()
    gid = c.post("/emo/start", json={"answers": ANSWERS, "seed": 11, "days": 5}).json()["game_id"]
    board = c.get(f"/emo/{gid}/board").json()
    exposed_id = board["scenario"]["choices"][0]["id"]   # 매도(방어 버킷) — coin_target 필요
    r = c.post(f"/emo/{gid}/choose", json={"choice_id": exposed_id, "coin_target": "meme"})
    assert r.status_code == 200
