"""T-1: 플레이어 감정 상태 자료구조 테스트.

4축(fear/greed/anxiety/restlessness) 객체 생성, 범위 밖 값 클램핑,
상태 갱신이 순수함수인지 검증한다.
"""
import pytest

from sim.player_emotion.config import AXIS_MIN, AXIS_MAX
from sim.player_emotion.state import (
    PlayerEmotionState,
    clamp,
    get_axis,
    set_axis,
)


def test_default_state_has_four_axes_at_zero():
    state = PlayerEmotionState()
    assert state.fear == 0
    assert state.greed == 0
    assert state.anxiety == 0
    assert state.restlessness == 0


def test_can_construct_with_explicit_values():
    state = PlayerEmotionState(fear=10, greed=20, anxiety=30, restlessness=40)
    assert state.fear == 10
    assert state.greed == 20
    assert state.anxiety == 30
    assert state.restlessness == 40


def test_clamp_caps_values_above_max():
    state = PlayerEmotionState(
        fear=AXIS_MAX + 50,
        greed=AXIS_MAX + 1,
        anxiety=AXIS_MAX + 999,
        restlessness=AXIS_MAX + 1,
    )
    clamped = clamp(state)
    assert clamped.fear == AXIS_MAX
    assert clamped.greed == AXIS_MAX
    assert clamped.anxiety == AXIS_MAX
    assert clamped.restlessness == AXIS_MAX


def test_clamp_floors_values_below_min():
    state = PlayerEmotionState(
        fear=AXIS_MIN - 50,
        greed=AXIS_MIN - 1,
        anxiety=AXIS_MIN - 999,
        restlessness=AXIS_MIN - 1,
    )
    clamped = clamp(state)
    assert clamped.fear == AXIS_MIN
    assert clamped.greed == AXIS_MIN
    assert clamped.anxiety == AXIS_MIN
    assert clamped.restlessness == AXIS_MIN


def test_clamp_is_pure_and_does_not_mutate_input():
    original = PlayerEmotionState(fear=AXIS_MAX + 10)
    clamp(original)
    assert original.fear == AXIS_MAX + 10  # 입력은 그대로


def test_get_axis_reads_named_axis():
    state = PlayerEmotionState(fear=5, greed=6, anxiety=7, restlessness=8)
    assert get_axis(state, "fear") == 5
    assert get_axis(state, "greed") == 6
    assert get_axis(state, "anxiety") == 7
    assert get_axis(state, "restlessness") == 8


def test_get_axis_unknown_name_raises():
    state = PlayerEmotionState()
    with pytest.raises(ValueError):
        get_axis(state, "confidence")


def test_set_axis_returns_new_state_without_mutating_original():
    original = PlayerEmotionState(fear=0)
    updated = set_axis(original, "fear", 42)
    assert original.fear == 0
    assert updated.fear == 42
    assert updated is not original


def test_set_axis_clamps_out_of_range_value():
    original = PlayerEmotionState()
    updated = set_axis(original, "greed", AXIS_MAX + 100)
    assert updated.greed == AXIS_MAX


def test_set_axis_unknown_name_raises():
    state = PlayerEmotionState()
    with pytest.raises(ValueError):
        set_axis(state, "trust", 10)


def test_state_is_immutable_dataclass():
    state = PlayerEmotionState()
    with pytest.raises(Exception):
        state.fear = 99  # frozen dataclass여야 함
