"""T-3: 감정 델타 엔진 테스트.

이벤트 ID -> 축별 델타 적용 + 클램핑을 검증한다.
"""
import pytest

from sim.player_emotion.config import AXIS_MAX, AXIS_MIN
from sim.player_emotion.deltas import EVENT_DELTAS, apply_event
from sim.player_emotion.state import PlayerEmotionState


def test_event_delta_table_has_market_crash_entry():
    # 양방향(pole): 급락은 위축극(fear/anxiety) ↑ & 과열극(greed/restlessness) ↓.
    assert "market_crash" in EVENT_DELTAS
    d = EVENT_DELTAS["market_crash"]
    assert d["fear"] > 0 and d["anxiety"] > 0
    assert d["greed"] < 0 and d["restlessness"] < 0


def test_apply_event_moves_both_poles_bidirectionally():
    # 급락 → 위축극 상승, 과열극 하강(좋은 이벤트가 실제로 반대극을 내려줌).
    state = PlayerEmotionState(fear=30, greed=40, anxiety=30, restlessness=40)
    updated = apply_event(state, "market_crash")
    assert updated.fear > 30 and updated.anxiety > 30      # 위축극 ↑
    assert updated.greed < 40 and updated.restlessness < 40  # 과열극 ↓


def test_apply_event_surge_is_opposite_of_crash():
    # 급등 → 과열극 ↑ & 위축극 ↓ (급락과 정반대 방향).
    state = PlayerEmotionState(fear=40, greed=30, anxiety=40, restlessness=30)
    updated = apply_event(state, "market_surge")
    assert updated.greed > 30 and updated.restlessness > 30  # 과열극 ↑
    assert updated.fear < 40 and updated.anxiety < 40        # 위축극 ↓


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
