"""T-4: 감정 압축 판정.

verdict = (greed + restlessness) - (fear + anxiety)
score가 config.OVERHEAT_THRESHOLD 이상이면 "과열",
config.WITHDRAWAL_THRESHOLD 이하면 "위축", 그 사이면 중립.
임계값은 config.py를 항상 참조한다(하드코딩 금지) — 호출 시점에
config 모듈 속성을 읽어 임계값 변경이 즉시 반영되게 한다.
"""

from __future__ import annotations

from . import config
from .state import PlayerEmotionState

OVERHEAT = "과열"
WITHDRAWAL = "위축"
NEUTRAL = "중립"


def compute_score(state: PlayerEmotionState) -> float:
    """(greed + restlessness) - (fear + anxiety)."""
    return (state.greed + state.restlessness) - (state.fear + state.anxiety)


def compute_verdict(state: PlayerEmotionState) -> str:
    """상태의 압축 점수를 config 임계값과 비교해 판정 문자열을 반환한다."""
    score = compute_score(state)
    if score >= config.OVERHEAT_THRESHOLD:
        return OVERHEAT
    if score <= config.WITHDRAWAL_THRESHOLD:
        return WITHDRAWAL
    return NEUTRAL
