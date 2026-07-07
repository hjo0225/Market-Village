"""T-6: 플레이어 감정 변화 로그.

매 턴 4축 스냅샷을 시계열로 누적·조회하는 순수 자료구조/함수.
"""

from __future__ import annotations

from dataclasses import dataclass

from .state import PlayerEmotionState


@dataclass(frozen=True)
class EmotionSnapshot:
    """특정 턴의 감정 상태 스냅샷."""

    turn: int
    state: PlayerEmotionState


@dataclass(frozen=True)
class EmotionLog:
    """감정 스냅샷의 시계열 누적. 기본값은 빈 로그."""

    snapshots: tuple[EmotionSnapshot, ...] = ()


def record_snapshot(log: EmotionLog, turn: int, state: PlayerEmotionState) -> EmotionLog:
    """turn 시점의 state 스냅샷을 log 끝에 추가한 새 EmotionLog를 반환한다(입력 불변)."""
    new_snapshot = EmotionSnapshot(turn=turn, state=state)
    return EmotionLog(snapshots=log.snapshots + (new_snapshot,))


def query_timeseries(log: EmotionLog) -> list[EmotionSnapshot]:
    """기록된 스냅샷을 기록 순서 그대로 리스트로 반환한다."""
    return list(log.snapshots)
