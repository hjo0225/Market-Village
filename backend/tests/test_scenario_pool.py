"""§4/§6 — 게시판 선택지 6개 풀 → 3개 노출(버킷 방어/관망/공격 스펙트럼 보장).

get_scenario(event_id, seed, day)가 결정론으로 3개를 뽑는다(I2/I4). 6개 전부는
get_choice로 조회 가능해야 하고, 노출 안 된 id로 POST /choose 하면 400.
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


def test_different_day_can_change_the_three_choices():
    # 최소 하루 이상에서 다른 조합이 나와야 "변주"가 성립(결정론이되 날짜별로 변화).
    ids_by_day = set()
    for day in range(12):
        sc = get_scenario("market_crash", seed=99, day=day)
        ids_by_day.add(tuple(c["id"] for c in sc["choices"]))
    assert len(ids_by_day) > 1, "노출 조합이 날짜에 따라 전혀 변주되지 않음"


def test_different_seed_can_change_the_three_choices():
    ids_by_seed = set()
    for seed in range(12):
        sc = get_scenario("market_crash", seed=seed, day=0)
        ids_by_seed.add(tuple(c["id"] for c in sc["choices"]))
    assert len(ids_by_seed) > 1


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
    scenarios = load_scenarios()
    for event_id in EVENT_CATEGORIES:
        all_choices = scenarios[event_id]["choices"]
        assert len(all_choices) == 6
        exposed = pick_exposed_choices(all_choices, seed=1, day=1, event_id=event_id)
        assert len(exposed) == 3


# ── 6개 전부 get_choice로 조회 가능 ──────────────────────────────────────
def test_all_six_choices_reachable_via_get_choice():
    scenarios = load_scenarios()
    for event_id in EVENT_CATEGORIES:
        for ch in scenarios[event_id]["choices"]:
            found = get_choice(event_id, ch["id"])
            assert found["id"] == ch["id"]


def test_get_scenario_without_seed_day_returns_full_pool_of_six():
    # 레거시 호출부(seed/day 생략) 하위 호환 — 6개 전부.
    for event_id in EVENT_CATEGORIES:
        assert len(get_scenario(event_id)["choices"]) == 6


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
    c = _client()
    gid = c.post("/emo/start", json={"answers": ANSWERS, "seed": 11, "days": 5}).json()["game_id"]
    board = c.get(f"/emo/{gid}/board").json()
    exposed_ids = {ch["id"] for ch in board["scenario"]["choices"]}
    event_id = board["event_id"]
    all_ids = {ch["id"] for ch in load_scenarios()[event_id]["choices"]}
    unexposed = all_ids - exposed_ids
    assert unexposed, "테스트 전제 위반: 노출 안 된 선택지가 없음"
    bad_id = next(iter(unexposed))
    r = c.post(f"/emo/{gid}/choose", json={"choice_id": bad_id})
    assert r.status_code == 400


def test_choose_with_exposed_choice_id_succeeds():
    c = _client()
    gid = c.post("/emo/start", json={"answers": ANSWERS, "seed": 11, "days": 5}).json()["game_id"]
    board = c.get(f"/emo/{gid}/board").json()
    exposed_id = board["scenario"]["choices"][0]["id"]
    r = c.post(f"/emo/{gid}/choose", json={"choice_id": exposed_id})
    assert r.status_code == 200
