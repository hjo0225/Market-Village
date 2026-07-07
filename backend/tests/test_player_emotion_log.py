"""T-6: 플레이어 감정 변화 로그 테스트.

매 턴 4축 스냅샷 기록과 시계열 조회가 순수함수로 동작하는지 검증한다.
"""
import pytest

from sim.player_emotion.log import (
    EmotionLog,
    EmotionSnapshot,
    query_timeseries,
    record_snapshot,
)
from sim.player_emotion.state import PlayerEmotionState


def test_empty_log_has_empty_timeseries():
    log = EmotionLog()
    assert query_timeseries(log) == []


def test_record_snapshot_appends_entry_with_turn_and_state():
    log = EmotionLog()
    state = PlayerEmotionState(fear=10, greed=20, anxiety=30, restlessness=40)
    updated = record_snapshot(log, turn=1, state=state)
    timeseries = query_timeseries(updated)
    assert len(timeseries) == 1
    assert timeseries[0].turn == 1
    assert timeseries[0].state == state


def test_record_snapshot_is_pure_and_does_not_mutate_original_log():
    log = EmotionLog()
    state = PlayerEmotionState(fear=5)
    updated = record_snapshot(log, turn=1, state=state)
    assert query_timeseries(log) == []
    assert updated is not log


def test_multiple_records_accumulate_in_order():
    log = EmotionLog()
    state1 = PlayerEmotionState(fear=1)
    state2 = PlayerEmotionState(fear=2)
    state3 = PlayerEmotionState(fear=3)
    log = record_snapshot(log, turn=1, state=state1)
    log = record_snapshot(log, turn=2, state=state2)
    log = record_snapshot(log, turn=3, state=state3)
    timeseries = query_timeseries(log)
    assert [snap.turn for snap in timeseries] == [1, 2, 3]
    assert [snap.state for snap in timeseries] == [state1, state2, state3]


def test_query_timeseries_returns_list_type():
    log = EmotionLog()
    log = record_snapshot(log, turn=1, state=PlayerEmotionState())
    result = query_timeseries(log)
    assert isinstance(result, list)


def test_recording_at_same_turn_twice_keeps_both_entries():
    # 같은 턴에 두 번 기록해도 각각 별도 항목으로 누적된다(덮어쓰지 않음).
    log = EmotionLog()
    state_a = PlayerEmotionState(fear=1)
    state_b = PlayerEmotionState(fear=2)
    log = record_snapshot(log, turn=1, state=state_a)
    log = record_snapshot(log, turn=1, state=state_b)
    timeseries = query_timeseries(log)
    assert len(timeseries) == 2
    assert timeseries[0].state == state_a
    assert timeseries[1].state == state_b


def test_emotion_snapshot_is_immutable():
    snapshot = EmotionSnapshot(turn=1, state=PlayerEmotionState())
    with pytest.raises(Exception):
        snapshot.turn = 2  # frozen dataclass여야 함


def test_emotion_log_is_immutable():
    log = EmotionLog()
    with pytest.raises(Exception):
        log.snapshots = ()  # frozen dataclass여야 함
