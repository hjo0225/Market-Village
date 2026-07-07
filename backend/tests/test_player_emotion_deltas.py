"""T-3: 감정 델타 엔진 테스트.

이벤트 ID -> 축별 델타 적용 + 클램핑을 검증한다.
"""
import pytest

from sim.player_emotion.config import AXIS_MAX, AXIS_MIN
from sim.player_emotion.deltas import EVENT_DELTAS, apply_event
from sim.player_emotion.state import PlayerEmotionState


def test_event_delta_table_has_market_crash_entry():
    assert "market_crash" in EVENT_DELTAS
    assert EVENT_DELTAS["market_crash"] == {"fear": 20, "anxiety": 10}


def test_apply_event_adds_delta_to_matching_axes():
    state = PlayerEmotionState(fear=10, anxiety=5)
    updated = apply_event(state, "market_crash")
    assert updated.fear == 30
    assert updated.anxiety == 15


def test_apply_event_leaves_axes_not_in_delta_unchanged():
    state = PlayerEmotionState(fear=10, greed=40, anxiety=5, restlessness=7)
    updated = apply_event(state, "market_crash")
    assert updated.greed == 40
    assert updated.restlessness == 7


def test_apply_event_market_surge_moves_greed_and_restlessness():
    state = PlayerEmotionState()
    updated = apply_event(state, "market_surge")
    assert updated.greed == EVENT_DELTAS["market_surge"]["greed"]
    assert updated.restlessness == EVENT_DELTAS["market_surge"]["restlessness"]


def test_apply_event_rumor_spread_moves_anxiety():
    state = PlayerEmotionState()
    updated = apply_event(state, "rumor_spread")
    assert updated.anxiety == EVENT_DELTAS["rumor_spread"]["anxiety"]


def test_apply_event_check_portfolio_moves_restlessness():
    state = PlayerEmotionState()
    updated = apply_event(state, "check_portfolio")
    assert updated.restlessness == EVENT_DELTAS["check_portfolio"]["restlessness"]


def test_apply_event_clamps_result_above_max():
    state = PlayerEmotionState(fear=AXIS_MAX - 5)
    updated = apply_event(state, "market_crash")
    assert updated.fear == AXIS_MAX


def test_apply_event_clamps_result_below_min():
    state = PlayerEmotionState(fear=AXIS_MIN + 5)
    updated = apply_event(state, "market_calm")
    assert updated.fear == AXIS_MIN


def test_apply_event_is_pure_and_does_not_mutate_input():
    original = PlayerEmotionState(fear=10)
    apply_event(original, "market_crash")
    assert original.fear == 10  # 입력은 그대로


def test_apply_event_unknown_id_raises():
    state = PlayerEmotionState()
    with pytest.raises(ValueError):
        apply_event(state, "no_such_event")


def test_event_deltas_is_data_only_table_addable_without_code_change():
    # 델타 테이블은 이벤트ID -> {축: 값} dict 데이터여야 한다(함수 아님).
    for event_id, delta in EVENT_DELTAS.items():
        assert isinstance(event_id, str)
        assert isinstance(delta, dict)
        for axis, value in delta.items():
            assert axis in ("fear", "greed", "anxiety", "restlessness")
            assert isinstance(value, (int, float))
