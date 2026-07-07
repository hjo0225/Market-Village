"""T-9: 게시판 강제노출 → 플레이어 감정 델타 (얇은 어댑터).

board_v2의 게시글/댓글 생성(threads)만 표시용으로 재사용하고, 노출 자체는
player_emotion 델타(T-3 apply_event)로, 선택지는 T-8 시나리오 델타로 플레이어
4축에 적용한다. board_v2.agent_deltas/crowd_delta(NPC 결합부)는 사용하지 않는다.
"""

import random

import pytest

from sim.board_exposure import (
    EVENT_TO_CONTEXT,
    apply_choice,
    build_board_exposure,
)
from sim.player_emotion.state import PlayerEmotionState


def _neutral():
    return PlayerEmotionState(fear=50, greed=50, anxiety=50, restlessness=50)


def test_exposure_returns_display_threads_and_scenario():
    out = build_board_exposure("market_crash", _neutral(), random.Random(1))
    assert out["threads"], "게시글이 비어있음"
    assert out["verdict"] in ("up", "down", "split")
    assert out["scenario"]["text"].strip()
    assert len(out["scenario"]["choices"]) == 3


def test_all_four_events_map_to_a_board_context():
    for ev in ("market_crash", "market_surge", "rumor_spread", "market_volatile"):
        assert ev in EVENT_TO_CONTEXT
        out = build_board_exposure(ev, _neutral(), random.Random(3))
        assert out["context"] == EVENT_TO_CONTEXT[ev]


def test_exposure_applies_player_delta_immediately():
    # 노출 즉시 델타(T-3 apply_event). 급락 → fear 상승.
    out = build_board_exposure("market_crash", _neutral(), random.Random(2))
    assert isinstance(out["emotion_after"], PlayerEmotionState)
    assert out["emotion_after"].fear > out["emotion_before"].fear


def test_no_npc_coupling_exposed():
    # 플레이어 대면 페이로드에 NPC 결합부를 노출하지 않는다.
    out = build_board_exposure("market_surge", _neutral(), random.Random(4))
    assert "agent_deltas" not in out
    assert "crowd_delta" not in out


def test_deterministic_given_same_seed():
    a = build_board_exposure("rumor_spread", _neutral(), random.Random(7))
    b = build_board_exposure("rumor_spread", _neutral(), random.Random(7))
    assert a["threads"] == b["threads"]
    assert a["emotion_after"] == b["emotion_after"]


def test_apply_choice_applies_scenario_delta():
    # 급락 'cut'(손절) 선택 → fear 추가 상승.
    before = _neutral()
    after = apply_choice(before, "market_crash", "cut")
    assert isinstance(after, PlayerEmotionState)
    assert after.fear > before.fear


def test_apply_choice_rejects_unknown_choice():
    with pytest.raises(ValueError):
        apply_choice(_neutral(), "market_crash", "nope")


def test_build_rejects_unknown_event():
    with pytest.raises(ValueError):
        build_board_exposure("nope", _neutral(), random.Random(1))
