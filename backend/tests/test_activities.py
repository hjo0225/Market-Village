"""v4 §1.2 — 활동(activity) 시스템 단위/통합 테스트.

같은 (seed,day,band,place) → 같은 활동 / forecast == 실제 정산 적용치(I3) /
스키마 린트(≥2 변형·cost 0~3·|delta| 1~6·순이득 금지) / 다른 날 → 다른 조합 /
예산 강제(cost 3 둘은 불가 + 세번째 밴드 ≥0).
"""

from __future__ import annotations

import random
import zlib

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


# --- 결정론: 같은 (seed,day,band,place) → 같은 활동 ------------------------ #
def test_activity_for_is_deterministic():
    a1 = PE.activity_for(42, 3, "오전", "카페")
    a2 = PE.activity_for(42, 3, "오전", "카페")
    assert a1 == a2


def test_activity_for_matches_crc32_choice_pattern():
    # 스펙 §1.2 — rng = random.Random(zlib.crc32(f"act:{seed}:{day}:{band}:{place}"))
    # → rng.choice(variants). 패턴을 직접 재현해 일치를 확인(I2).
    seed, day, band, place = 7, 2, "저녁", "펍"
    variants = PE.ACTIVITIES[(band, place)]
    rng = random.Random(zlib.crc32(f"act:{seed}:{day}:{band}:{place}".encode()))
    expected = rng.choice(variants)
    assert PE.activity_for(seed, day, band, place) == expected


def test_activity_for_unknown_combo_raises_keyerror():
    import pytest
    with pytest.raises(KeyError):
        PE.activity_for(1, 1, "새벽", "카페")


# --- 다른 날 → (전체적으로) 다른 조합 등장 ---------------------------------- #
def test_different_days_produce_varying_activities_somewhere():
    seed = 99
    seen: set[str] = set()
    for day in range(30):
        for band in PE.PLAN_BANDS:
            for place in PE.PLAN_PLACES:
                seen.add(PE.activity_for(seed, day, band, place)["id"])
    # 52개 활동 중 상당수가 30일 안에 등장해야 함(다양성 확보 — 정확한 개수는
    # rng 표본 의존이라 느슨하게, 하지만 단일 활동만 반복되진 않아야 한다).
    assert len(seen) > 24


def test_same_combo_varies_across_days_for_multi_variant_place():
    seed = 123
    ids = {PE.activity_for(seed, day, "오전", "카페")["id"] for day in range(30)}
    assert len(ids) > 1, "30일이면 카페/오전의 3개 변형이 최소 2개는 등장해야 함"


# --- 스키마 린트: 모든 (밴드,장소) 조합에 변형 >= 2 ------------------------- #
def test_all_band_place_combos_have_at_least_two_variants():
    for band in PE.PLAN_BANDS:
        for place in PE.PLAN_PLACES:
            variants = PE.ACTIVITIES.get((band, place))
            assert variants is not None, f"missing combo {(band, place)}"
            assert 2 <= len(variants) <= 3, f"{(band, place)}: {len(variants)} variants"


def test_activity_count_is_at_least_48():
    total = sum(len(v) for v in PE.ACTIVITIES.values())
    assert total >= 48


# --- 스키마 린트: cost 0~3 · |delta| 1~6 · 순이득 금지 ---------------------- #
_BENEFICIAL_DIRECTION = {
    "fear": -1, "greed": -1, "anxiety": -1, "restlessness": -1, "composure": 1,
}


def test_activity_schema_cost_and_delta_ranges():
    for (band, place), variants in PE.ACTIVITIES.items():
        ids = set()
        for act in variants:
            assert act["id"] not in ids, f"dup id {act['id']}"
            ids.add(act["id"])
            assert act.get("name"), f"{act['id']}: missing name"
            assert 0 <= act["cost"] <= 3, f"{act['id']}: cost {act['cost']} out of [0,3]"
            deltas = act.get("deltas") or {}
            assert deltas, f"{act['id']}: no deltas (at least one axis required)"
            for axis, v in deltas.items():
                assert 1 <= abs(v) <= 6, f"{act['id']}: axis {axis} delta {v} out of [1,6]"


def test_activity_schema_no_net_positive_below_cost_two():
    """순이득 금지: 델타가 전부 '이로운 방향'(공포/탐욕/불안/조급 감소 or 평정
    증가)인 활동은 cost>=2여야 한다(강한 효과는 비용↑ 또는 부작용 축 동반)."""
    for (band, place), variants in PE.ACTIVITIES.items():
        for act in variants:
            deltas = act["deltas"]
            all_beneficial = all(
                v * _BENEFICIAL_DIRECTION.get(axis, 0) > 0
                for axis, v in deltas.items()
            )
            if all_beneficial:
                assert act["cost"] >= 2, (
                    f"{act['id']}: net-positive (all axes beneficial) but cost "
                    f"{act['cost']} < 2 -- deltas={deltas}"
                )


def test_home_place_activities_stay_cheap():
    # 스펙: 집은 항상 저렴하고 약하게 유지.
    for band in PE.PLAN_BANDS:
        for act in PE.ACTIVITIES[(band, "집")]:
            assert act["cost"] == 0
            assert all(abs(v) <= 2 for v in act["deltas"].values())


# --- I3: GET /plan의 forecast == 실제 정산 적용치(활동 기반) --------------- #
def test_plan_preview_activity_matches_settlement_activity():
    c = _client()
    seed = 7
    gid = _start(c, seed=seed, days=5)
    # 예산(5) 안에 확실히 들어오도록 그날의 활동 비용을 미리 조회해 구성.
    plan = {
        band: min(PE.PLAN_PLACES, key=lambda p: PE.activity_cost(seed, 0, band, p))
        for band in PE.PLAN_BANDS
    }
    assert sum(PE.activity_cost(seed, 0, b, plan[b]) for b in PE.PLAN_BANDS) <= PE.PLAN_BUDGET
    plan_body = c.get(f"/emo/{gid}/plan").json()
    bands = {b["band"]: b for b in plan_body["bands"]}
    chosen_opts = {
        band: next(o for o in bands[band]["options"] if o["place"] == place)
        for band, place in plan.items()
    }
    for band, place in plan.items():
        opt = chosen_opts[band]
        assert opt["activity_id"]
        assert opt["activity_name"]
        expected = PE.activity_for(seed, 0, band, place)
        assert opt["activity_id"] == expected["id"]
        assert opt["cost"] == expected["cost"]
        assert opt["forecast"] == expected["deltas"]

    post_r = c.post(f"/emo/{gid}/plan", json={"plan": plan})
    assert post_r.status_code == 200
    board = c.get(f"/emo/{gid}/board").json()
    choice_id = board["scenario"]["choices"][0]["id"]
    state = c.post(f"/emo/{gid}/choose",
                   json={"choice_id": choice_id, "coin_target": "meme"}).json()
    settlement = state["settlement"]
    place_steps = [s for s in settlement["emotion_steps"] if s["source"] == "place"]
    assert len(place_steps) == 3
    # 정산 스텝은 오전→오후→저녁 순서로 쌓인다(apply_place_effects) — 같은
    # 장소가 여러 밴드에 겹칠 수 있으므로(예: 집) place가 아니라 PLAN_BANDS
    # 순서로 짝짓는다.
    for band, step in zip(PE.PLAN_BANDS, place_steps):
        place = plan[band]
        opt = chosen_opts[band]
        assert step["place"] == place
        assert step["activity_id"] == opt["activity_id"]
        assert step["activity_name"] == opt["activity_name"]
        for axis, v in opt["forecast"].items():
            assert step["deltas"].get(axis, 0) == v, (band, place, axis)
        for axis, v in step["deltas"].items():
            if axis not in opt["forecast"]:
                assert v == 0, (band, place, axis, "forecast에 없는 축이 0이 아님")


# --- 정산 place 스텝 라벨이 활동명 기반인지 -------------------------------- #
def test_settlement_place_step_label_uses_activity_name():
    c = _client()
    seed = 7
    gid = _start(c, seed=seed, days=5)
    plan = {
        band: min(PE.PLAN_PLACES, key=lambda p: PE.activity_cost(seed, 0, band, p))
        for band in PE.PLAN_BANDS
    }
    assert sum(PE.activity_cost(seed, 0, b, plan[b]) for b in PE.PLAN_BANDS) <= PE.PLAN_BUDGET
    r = c.post(f"/emo/{gid}/plan", json={"plan": plan})
    assert r.status_code == 200
    board = c.get(f"/emo/{gid}/board").json()
    state = c.post(f"/emo/{gid}/choose",
                   json={"choice_id": board["scenario"]["choices"][0]["id"], "coin_target": "meme"}).json()
    place_steps = [s for s in state["settlement"]["emotion_steps"] if s["source"] == "place"]
    for step in place_steps:
        assert step["label"] == f"「{step['activity_name']}」 후"


# --- 예산 강제: cost-3 둘은 불가 + 세번째 밴드 >= 0 ------------------------- #
def test_budget_blocks_two_cost_three_activities_plus_nonnegative_third():
    # 오후/운동(gym_pm_spar, cost 3)과 저녁/펍(pub_pm_talk, cost 3)이 둘 다
    # 뽑히는 (seed,day)를 찾고, 세번째 밴드(오전)에 cost>=0인 아무 장소를
    # 더하면 예산 5를 넘어야 한다(3+3=6 > 5, 오전 최소 cost는 0이라도 이미 초과).
    seed = 0
    found = None
    for day in range(60):
        pm_gym = PE.activity_for(seed, day, "오후", "운동")
        pm_pub = PE.activity_for(seed, day, "저녁", "펍")
        if pm_gym["cost"] == 3 and pm_pub["cost"] == 3:
            found = day
            break
    assert found is not None, "60일 안에 두 cost-3 조합을 찾지 못함(rng 표본 문제)"

    c = _client()
    gid = _start(c, seed=seed, days=found + 1)
    for _ in range(found):
        board = c.get(f"/emo/{gid}/board").json()
        c.post(f"/emo/{gid}/choose",
               json={"choice_id": board["scenario"]["choices"][0]["id"], "coin_target": "meme"})

    am_cost = min(PE.activity_cost(seed, found, "오전", p) for p in PE.PLAN_PLACES)
    assert am_cost >= 0
    plan = {"오전": PE.PLAN_PLACES[0], "오후": "운동", "저녁": "펍"}
    total = (PE.activity_cost(seed, found, "오전", plan["오전"])
             + PE.activity_cost(seed, found, "오후", "운동")
             + PE.activity_cost(seed, found, "저녁", "펍"))
    assert total > PE.PLAN_BUDGET
    r = c.post(f"/emo/{gid}/plan", json={"plan": plan})
    assert r.status_code == 400


# --- I6: 미제출 시 기존 자동 루트(활동 시스템 도입 후에도 유지) ------------- #
def test_no_plan_keeps_legacy_route_with_activities_present():
    c = _client()
    gid = _start(c, seed=42, days=5)
    board = c.get(f"/emo/{gid}/board").json()
    state = c.post(f"/emo/{gid}/choose",
                   json={"choice_id": board["scenario"]["choices"][0]["id"], "coin_target": "meme"}).json()
    settlement = state["settlement"]
    assert not [s for s in settlement["emotion_steps"] if s["source"] == "place"]
