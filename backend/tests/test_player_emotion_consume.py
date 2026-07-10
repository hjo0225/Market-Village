"""T-51 (F4): 감정 소모 프리미티브 + 액션 플로어 게이트.

게시판 3액션(탐욕 매수 / 공포 매도 / 평정 유지)은 감정을 **현재값의 비율만큼 소모**한다.
소모량은 매매 규모의 원천이며(감정 비례), 감정이 플로어 미만이면 그 액션은 비활성이다.
"""
import pytest

from sim.player_emotion.config import AXIS_MAX, EMOTION_ACTION_FLOOR
from sim.player_emotion.deltas import can_act_on, consume_amount, consume_axis
from sim.player_emotion.state import PlayerEmotionState


def test_consume_amount_is_fraction_of_current_value():
    # DoD: 탐욕 80에서 20% 소모량 = 16 (상태 불변).
    s = PlayerEmotionState(greed=80)
    assert consume_amount(s, "greed", 0.2) == pytest.approx(16.0)


def test_consume_axis_reduces_axis_by_that_fraction():
    # DoD: 탐욕 80 → 20% 소모 → 64, 소모량 16.
    s = PlayerEmotionState(greed=80)
    new, consumed = consume_axis(s, "greed", 0.2)
    assert new.greed == pytest.approx(64.0)
    assert consumed == pytest.approx(16.0)


def test_consume_leaves_other_axes_untouched():
    s = PlayerEmotionState(greed=80, fear=30, composure=50)
    new, _ = consume_axis(s, "greed", 0.5)
    assert new.fear == 30 and new.composure == 50


def test_higher_emotion_consumes_more_proportionally():
    # 감정 비례(4b): 탐욕 90이 탐욕 20보다 더 큰 소모량 → 더 큰 매매.
    hi = consume_amount(PlayerEmotionState(greed=90), "greed", 0.2)
    lo = consume_amount(PlayerEmotionState(greed=20), "greed", 0.2)
    assert hi > lo


def test_consume_clamps_and_never_goes_below_zero():
    s = PlayerEmotionState(greed=0)
    new, consumed = consume_axis(s, "greed", 0.5)
    assert new.greed == 0
    assert consumed == 0


def test_consume_is_pure_and_does_not_mutate_input():
    original = PlayerEmotionState(greed=80)
    consume_axis(original, "greed", 0.5)
    assert original.greed == 80


def test_consume_fraction_out_of_range_raises():
    s = PlayerEmotionState(greed=80)
    with pytest.raises(ValueError):
        consume_amount(s, "greed", 1.5)
    with pytest.raises(ValueError):
        consume_amount(s, "greed", -0.1)


def test_consume_unknown_axis_raises():
    s = PlayerEmotionState()
    with pytest.raises(ValueError):
        consume_axis(s, "no_such_axis", 0.2)


def test_can_act_on_requires_emotion_at_or_above_floor():
    # "안 느끼는 감정으론 못 움직인다" — 플로어 미만이면 그 감정 기반 액션 비활성.
    at_floor = PlayerEmotionState(fear=EMOTION_ACTION_FLOOR)
    below = PlayerEmotionState(fear=EMOTION_ACTION_FLOOR - 1)
    assert can_act_on(at_floor, "fear") is True
    assert can_act_on(below, "fear") is False


def test_can_act_on_composure_uses_same_floor():
    # 평정(유지)도 같은 플로어 — 평정 고갈 시 유지 불가(충동에 캐브, 테마 정합).
    assert can_act_on(PlayerEmotionState(composure=AXIS_MAX), "composure") is True
    assert can_act_on(PlayerEmotionState(composure=0), "composure") is False
