"""T-18: 동행배치를 새 4축 엔진에 이어붙이기.

기존 avoidance.py(회피·클론 NPC 선택)·personas.npc_scheds를 재사용해, 매일
companion NPC를 결정한다. 옛 6함정 trap_scores 대신 4축 끌림 — 클론(플레이어
거울)은 자기 감정에서 가장 높은(취약한) 축을 자극하는 NPC에게 끌린다.
플레이어 개입: designate(지정)·avoid(스왑).
"""

import pytest

from sim.companion import daily_candidates, pick_companion
from sim.emo_game import EmoGameRun
from sim.player_emotion.state import PlayerEmotionState

EVENTS = ["market_crash", "market_surge", "market_volatile"]
RETURNS = [-0.2, 0.3, 0.05]
ANSWERS = {"q_panic": 0.5, "q_fomo": 0.5, "q_rumor": 0.5, "q_check": 0.5}


def _emo(**kw):
    base = dict(fear=50, greed=50, anxiety=50, restlessness=50)
    base.update(kw)
    return PlayerEmotionState(**base)


# --- 순수 함수 --------------------------------------------------------- #
def test_daily_candidates_by_place():
    scheds = {"a": {1: "카페", 4: "광장"}, "b": {2: "광장"}, "c": {3: "펍"}}
    assert daily_candidates("광장", scheds) == ["a", "b"]
    assert daily_candidates("펍", scheds) == ["c"]
    assert daily_candidates("운동", scheds) == []


def test_pick_companion_empty_is_none():
    assert pick_companion([], _emo()) is None


def test_pick_companion_drawn_to_weakest_axis():
    # 공포가 가장 높은 플레이어 → 공포 톤이 가장 센 NPC에 끌림.
    who = pick_companion(["doomposter", "cheerleader"], _emo(fear=90))
    assert who == "doomposter"
    # 탐욕이 가장 높으면 탐욕 톤 센 쪽.
    who2 = pick_companion(["doomposter", "bull_hoper"], _emo(greed=95))
    assert who2 == "bull_hoper"


def test_pick_companion_respects_designation():
    who = pick_companion(["doomposter", "cheerleader"], _emo(fear=90), designated="cheerleader")
    assert who == "cheerleader"
    # 지정이 후보에 없으면 무시(자동 선택).
    who2 = pick_companion(["doomposter", "cheerleader"], _emo(fear=90), designated="nobody")
    assert who2 == "doomposter"


# --- EmoGameRun 통합 --------------------------------------------------- #
def test_run_determines_daily_companion_idempotently():
    r = EmoGameRun.new(ANSWERS, EVENTS, RETURNS, seed=42)
    c1 = r.companion()
    c2 = r.companion()
    assert c1 is not None
    assert c1 == c2                     # 멱등 GET


def test_designate_sets_companion():
    r = EmoGameRun.new(ANSWERS, EVENTS, RETURNS, seed=42)
    cands = daily_candidates(r.clone_route[r.day], r.schedules)
    other = next(c for c in cands if c != r.companion())
    r.designate(other)
    assert r.companion() == other


def test_designate_rejects_non_candidate():
    r = EmoGameRun.new(ANSWERS, EVENTS, RETURNS, seed=42)
    with pytest.raises(ValueError):
        r.designate("value_investor_that_is_not_here_xyz")


def test_avoid_swaps_route_and_recomputes():
    r = EmoGameRun.new(ANSWERS, EVENTS, RETURNS, seed=42)
    before = list(r.clone_route)
    r.avoid(0, 1)
    assert r.clone_route[0] == before[1]
    assert r.clone_route[1] == before[0]


def test_companion_advances_with_days():
    r = EmoGameRun.new(ANSWERS, EVENTS, RETURNS, seed=42)
    r.choose("hold")
    # day1 진입 → companion 재결정(또는 None 가능).
    assert r.day == 1
    _ = r.companion()   # 예외 없이 조회 가능


def test_companion_survives_serialization():
    r = EmoGameRun.new(ANSWERS, EVENTS, RETURNS, seed=42)
    r.designate(daily_candidates(r.clone_route[0], r.schedules)[0])
    doc = r.to_doc()
    restored = EmoGameRun.from_doc(doc)
    assert restored.companion() == r.companion()
    assert restored.clone_route == r.clone_route
