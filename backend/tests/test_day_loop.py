"""T-107 · §12 일일 루프 — 8슬롯 + 일과 셔플 + 확률 외란.

하루 = 4시간대 × 2슬롯 = 8슬롯(§12.1b). 일과 행동 종류는 고정, 순서만 회차마다
셔플(§12.2) — **순서발 감정효과 금지**. 일과 동선이 NPC와 같은 슬롯·장소에 겹치면
1:1 대화 발생(§9.2.2). 확률 외란은 20%/일·±2~4, 매매를 강제하지 않는다(§12.3).
"""

from __future__ import annotations

import random

from sim import day_loop as DL

MENU = ["카페", "일터", "광장", "운동", "집_차트"]


def test_eight_slots_four_timeslots():
    slots = DL.day_slots()
    assert len(slots) == 8
    assert [s["index"] for s in slots] == list(range(1, 9))
    # 4시간대 × 2 (오전/점심/오후/저녁)
    assert {s["timeslot"] for s in slots} == {"오전", "점심", "오후", "저녁"}
    assert [s["timeslot"] for s in slots[:2]] == ["오전", "오전"]
    assert [s["timeslot"] for s in slots[6:]] == ["저녁", "저녁"]


def test_shuffle_preserves_action_set():
    out = DL.shuffle_schedule(MENU, random.Random(3))
    assert sorted(out) == sorted(MENU)   # 종류 집합 불변(통제변인 §12.2)


def test_shuffle_deterministic():
    a = DL.shuffle_schedule(MENU, random.Random(3))
    b = DL.shuffle_schedule(MENU, random.Random(3))
    assert a == b


def test_order_has_no_emotion_effect():
    # §12.2 순서발 효과 금지 — 어떤 순서든 감정 결과는 동일(0)
    s1 = DL.shuffle_schedule(MENU, random.Random(1))
    s2 = DL.shuffle_schedule(MENU, random.Random(2))
    assert DL.schedule_emotion_effect(s1) == DL.schedule_emotion_effect(s2) == 0.0


def test_overlap_meetings():
    clone = {1: "카페", 3: "광장", 5: "일터"}
    npcs = {
        "turtle": {1: "카페", 3: "운동"},      # 슬롯1 카페에서 겹침
        "frog": {3: "광장", 5: "집"},          # 슬롯3 광장에서 겹침
        "quant": {2: "일터"},                  # 안 겹침
    }
    meetings = DL.overlap_meetings(clone, npcs)
    assert meetings.get(1) == ["turtle"]
    assert meetings.get(3) == ["frog"]
    assert 5 not in meetings  # 슬롯5 일터에 온 NPC 없음


def test_overlap_multiple_npcs_same_slot():
    clone = {4: "광장"}
    npcs = {"a": {4: "광장"}, "b": {4: "광장"}, "c": {4: "집"}}
    meetings = DL.overlap_meetings(clone, npcs)
    assert set(meetings[4]) == {"a", "b"}  # 여럿이면 후보 모두(클론이 한 명 고름은 별도)


def test_disturbance_none_when_no_roll():
    # 0.9 > 0.20 → 외란 없음
    rng = random.Random()
    rng.random = lambda: 0.9  # type: ignore
    assert DL.roll_disturbance(rng) is None


def test_disturbance_size_and_bidirectional():
    # 외란 발생 시 크기 ±2~4, 매매 강제 키 없음(§12.3)
    found_pos = found_neg = False
    for seed in range(200):
        d = DL.roll_disturbance(random.Random(seed))
        if d is None:
            continue
        assert 2.0 <= abs(d["delta"]) <= 4.0
        assert "action" not in d and "trade" not in d  # 매매 강제 안 함
        found_pos = found_pos or d["delta"] > 0
        found_neg = found_neg or d["delta"] < 0
    assert found_pos and found_neg  # 양방향(좋은 것·나쁜 것 섞임)


def test_disturbance_probability_about_20pct():
    rng = random.Random(99)
    hits = sum(1 for _ in range(4000) if DL.roll_disturbance(rng) is not None)
    assert 0.15 <= hits / 4000 <= 0.25
