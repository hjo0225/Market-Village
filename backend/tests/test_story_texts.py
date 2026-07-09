"""v2 스토리보강 스펙 §4 — story_texts.py 단위 테스트.

DAY_FRAMES 길이 20 / PLACE_FLAVOR 키가 실제 장소 상수 집합과 일치 /
GET /plan 응답에 morning 존재 / flavor 규칙이 NPC-aware(§2)임을 검증.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sim import emo_store, place_effects as PE, story_texts as ST
from sim.emo_api import router


def _client():
    emo_store._clear()
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


ANSWERS = {"q_panic": 0.5, "q_fomo": 0.5, "q_rumor": 0.5, "q_check": 0.5}


def _start(c, seed=42, days=5):
    return c.post("/emo/start", json={"answers": ANSWERS, "seed": seed, "days": days}).json()["game_id"]


# --- DAY_FRAMES ----------------------------------------------------------- #
def test_day_frames_has_20_entries():
    assert len(ST.DAY_FRAMES) == 20
    assert all(isinstance(t, str) and t for t in ST.DAY_FRAMES)


def test_day_frame_wraps_past_20_via_modulo():
    # total_days 생략(레거시 호출) — 이전 동작 그대로 전체 20개를 단순 순환.
    assert ST.day_frame(0) == ST.DAY_FRAMES[0]
    assert ST.day_frame(19) == ST.DAY_FRAMES[19]
    assert ST.day_frame(20) == ST.DAY_FRAMES[0]
    assert ST.day_frame(25) == ST.DAY_FRAMES[5]


# --- v3 §A: total_days를 주면 마지막 날·전야가 고정 핀 ---------------------- #
def test_day_frame_pins_last_day_and_eve_with_total_days():
    total = 10
    assert ST.day_frame(total - 1, total) == "마지막 날. 첫날과 같은 하늘."
    assert ST.day_frame(total - 2, total) == "전야. 마을이 평소보다 다정하다."
    assert ST.day_frame(total - 1, total) == ST.DAY_FRAMES[-1]
    assert ST.day_frame(total - 2, total) == ST.DAY_FRAMES[-2]


def test_day_frame_non_pinned_days_sequential_from_front_excluding_pinned():
    # 마지막 2개(전야·마지막 날)를 제외한 나머지 18개를 앞에서부터 순서대로.
    total = 10
    cycle = ST.DAY_FRAMES[:-2]
    for day in range(total - 2):   # day 0..7 (마지막 2일 제외)
        assert ST.day_frame(day, total) == cycle[day % len(cycle)]


def test_day_frame_pinned_frames_never_appear_in_non_pinned_days():
    total = 10
    pinned = {ST.DAY_FRAMES[-1], ST.DAY_FRAMES[-2]}
    for day in range(total - 2):
        assert ST.day_frame(day, total) not in pinned


def test_day_frame_wraps_within_cycle_when_total_days_exceeds_cycle_len():
    # 축소된 순환 목록(18개) 범위를 넘으면 그 안에서 wrap.
    cycle = ST.DAY_FRAMES[:-2]
    total = len(cycle) + 5   # 23 → day 18..22는 전야/마지막날 제외한 일반일
    # day 18(=len(cycle))은 wrap해 cycle[0]과 같아야 함(마지막 2일은 total-2, total-1).
    assert ST.day_frame(len(cycle), total) == cycle[0]


# --- PLACE_FLAVOR 키 == 실제 장소 상수 집합 -------------------------------- #
def test_place_flavor_keys_match_real_place_constants():
    assert set(ST.PLACE_FLAVOR) == set(PE.PLAN_PLACES)
    # place_effects.PLACE_FLAVOR는 하위 호환 별칭 — 단일 소스와 동일 객체/내용.
    assert PE.PLACE_FLAVOR == ST.PLACE_FLAVOR


def test_place_npc_flavor_keys_reference_real_places():
    places = set(PE.PLAN_PLACES)
    for (place, _npc_id) in ST.PLACE_NPC_FLAVOR:
        assert place in places


# --- GET /plan 응답에 morning 존재 ----------------------------------------- #
def test_plan_response_contains_morning():
    c = _client()
    gid = _start(c)
    body = c.get(f"/emo/{gid}/plan").json()
    assert "morning" in body
    assert body["morning"]["day"] == 0
    assert body["morning"]["text"] == ST.DAY_FRAMES[0]


def test_plan_response_morning_advances_and_pins_eve_and_last_day():
    # v3 §A — total_days(=25)를 아는 실제 플레이에서, 마지막 날(24)·전야(23)는
    # 항상 그 고정 프레임이어야 하고 그 외 날은 day_frame(day, total_days)와 일치.
    c = _client()
    total = 25
    gid = _start(c, days=total)
    plan = {"오전": "집", "오후": "집", "저녁": "집"}
    for expected_day in range(total):
        body = c.get(f"/emo/{gid}/plan").json()
        assert body["morning"]["day"] == expected_day
        assert body["morning"]["text"] == ST.day_frame(expected_day, total)
        if expected_day == total - 1:
            assert body["morning"]["text"] == "마지막 날. 첫날과 같은 하늘."
        if expected_day == total - 2:
            assert body["morning"]["text"] == "전야. 마을이 평소보다 다정하다."
        c.post(f"/emo/{gid}/plan", json={"plan": plan})
        board = c.get(f"/emo/{gid}/board").json()
        c.post(f"/emo/{gid}/choose", json={"choice_id": board["scenario"]["choices"][0]["id"]})


# --- flavor 규칙: NPC-aware(§2) -------------------------------------------- #
def test_plan_flavor_uses_npc_table_when_band_has_npc():
    # day 0, 오전, 카페 = fomo_scalper 단독 조우(personas 스케줄은 seed 무관 고정).
    c = _client()
    gid = _start(c, seed=42, days=5)
    body = c.get(f"/emo/{gid}/plan").json()
    band = next(b for b in body["bands"] if b["band"] == "오전")
    cafe = next(o for o in band["options"] if o["place"] == "카페")
    assert cafe["npcs"], "선행 조건: 이 밴드/장소에 NPC가 있어야 이 테스트가 유효함"
    npc_ids = sorted(n["npc_id"] for n in cafe["npcs"])
    expected = ST.PLACE_NPC_FLAVOR[("카페", npc_ids[0])]
    assert cafe["flavor"] == expected
    assert cafe["flavor"] != ST.PLACE_FLAVOR["카페"]


def test_plan_flavor_falls_back_to_place_flavor_when_no_npc():
    c = _client()
    gid = _start(c, seed=42, days=5)
    body = c.get(f"/emo/{gid}/plan").json()
    band = next(b for b in body["bands"] if b["band"] == "저녁")
    home = next(o for o in band["options"] if o["place"] == "집")
    assert not home["npcs"]
    assert home["flavor"] == ST.PLACE_FLAVOR["집"]


def test_place_flavor_helper_picks_sorted_first_npc_id():
    # 여러 NPC가 겹치는 밴드/장소(오전·일터=value_investor+contrarian)에서
    # sorted() 첫 번째(contrarian < value_investor)가 선택돼야 함.
    npc_ids = ["value_investor", "contrarian"]
    assert sorted(npc_ids)[0] == "contrarian"
    result = ST.place_flavor("일터", npc_ids)
    assert result == ST.PLACE_NPC_FLAVOR[("일터", "contrarian")]
