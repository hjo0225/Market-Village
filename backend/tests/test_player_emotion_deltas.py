"""T-3: 감정 델타 엔진 테스트.

이벤트 ID -> 축별 델타 적용 + 클램핑을 검증한다.
"""
import pytest

from sim.player_emotion.config import AXIS_MAX, AXIS_MIN, EQUILIBRIUM
from sim.player_emotion.deltas import (
    EVENT_DELTAS,
    apply_delta,
    apply_event,
    decay_toward_equilibrium,
)
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


# --- T-27: 감쇠·평형 (4b) + 포화 방지 --------------------------------------- #
def test_decay_pulls_high_axis_down_and_low_axis_up_toward_equilibrium():
    s = PlayerEmotionState(fear=10, greed=90, anxiety=50, restlessness=100)
    d = decay_toward_equilibrium(s, rate=0.15)
    assert 10 < d.fear < EQUILIBRIUM          # 낮은 축은 평형으로 올라온다
    assert EQUILIBRIUM < d.greed < 90         # 높은 축은 평형으로 내려온다
    assert d.anxiety == EQUILIBRIUM           # 평형값은 불변
    assert 50 < d.restlessness < 100


def test_decay_rate_zero_is_identity():
    s = PlayerEmotionState(fear=10, greed=90, anxiety=33, restlessness=77)
    assert decay_toward_equilibrium(s, rate=0.0) == s


def test_repeated_buy_never_saturates_any_axis_with_decay():
    """T-27 핵심 회귀: 매일 매수(chase 델타)만 반복해도 감쇠 덕에 어떤 축도
    100에 고정되지 않는다(steady = 평형 + 델타/감쇠율 < 100). 사용자 "구매하면
    무조건 탐욕 100"의 구조적 방지."""
    from sim.scenario import get_choice
    chase = get_choice("market_surge", "chase")["deltas"]
    e = PlayerEmotionState(fear=36, greed=65, anxiety=41, restlessness=58)
    for _ in range(60):
        e = decay_toward_equilibrium(e)   # 밤사이 회귀
        e = apply_delta(e, chase)          # 낮에 또 추격매수
    for axis in ("fear", "greed", "anxiety", "restlessness"):
        assert getattr(e, axis) < AXIS_MAX, f"{axis} 포화({getattr(e, axis)})"


def test_without_decay_repeated_buy_would_saturate_greed():
    """대조군: 감쇠(rate=0)가 없으면 같은 반복 매수가 greed를 천장에 고정시킨다 —
    감쇠가 포화를 막는 장치임을 증명."""
    from sim.scenario import get_choice
    chase = get_choice("market_surge", "chase")["deltas"]
    e = PlayerEmotionState(fear=36, greed=65, anxiety=41, restlessness=58)
    for _ in range(60):
        e = decay_toward_equilibrium(e, rate=0.0)   # 무감쇠
        e = apply_delta(e, chase)
    assert e.greed == AXIS_MAX   # 감쇠 없으면 포화
