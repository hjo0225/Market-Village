"""T-4: 감정 압축 판정 테스트.

verdict = (greed + restlessness) - (fear + anxiety)
score가 config.OVERHEAT_THRESHOLD 이상이면 "과열",
config.WITHDRAWAL_THRESHOLD 이하면 "위축", 그 사이면 중립을 반환한다.
config의 임계값을 바꾸면 경계가 이동하는지도 검증한다.
"""
from sim.player_emotion import config
from sim.player_emotion.state import PlayerEmotionState
from sim.player_emotion.verdict import NEUTRAL, OVERHEAT, WITHDRAWAL, compute_verdict


def test_neutral_state_is_neutral():
    state = PlayerEmotionState()
    assert compute_verdict(state) == NEUTRAL


def test_high_greed_and_restlessness_is_overheat():
    state = PlayerEmotionState(greed=50, restlessness=50)
    # score = (50+50) - (0+0) = 100 >= 30
    assert compute_verdict(state) == OVERHEAT


def test_high_fear_and_anxiety_is_withdrawal():
    state = PlayerEmotionState(fear=50, anxiety=50)
    # score = (0+0) - (50+50) = -100 <= -30
    assert compute_verdict(state) == WITHDRAWAL


def test_score_exactly_at_overheat_threshold_is_overheat():
    state = PlayerEmotionState(greed=config.OVERHEAT_THRESHOLD)
    # score = 30 - 0 = 30 == threshold -> 과열 (경계 포함)
    assert compute_verdict(state) == OVERHEAT


def test_score_exactly_at_withdrawal_threshold_is_withdrawal():
    state = PlayerEmotionState(fear=abs(config.WITHDRAWAL_THRESHOLD))
    # score = 0 - 30 = -30 == threshold -> 위축 (경계 포함)
    assert compute_verdict(state) == WITHDRAWAL


def test_score_just_inside_bounds_is_neutral():
    state = PlayerEmotionState(greed=config.OVERHEAT_THRESHOLD - 1)
    assert compute_verdict(state) == NEUTRAL


def test_changing_threshold_moves_the_boundary(monkeypatch):
    state = PlayerEmotionState(greed=10)  # score = 10
    assert compute_verdict(state) == NEUTRAL
    monkeypatch.setattr(config, "OVERHEAT_THRESHOLD", 10)
    assert compute_verdict(state) == OVERHEAT
