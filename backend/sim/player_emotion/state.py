"""T-1: 플레이어 감정 상태 자료구조.

4축(fear/greed/anxiety/restlessness) frozen dataclass + 순수 clamp/get/set 유틸.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from .config import AXIS_MAX, AXIS_MIN, EQUILIBRIUM

# T-37 — 4개 부정(함정) 축 + 긍정 축 '평정'(composure). 평정은 시장 노출이 아니라
# **플레이어의 원칙 있는 선택**으로만 오르내린다(자기통제의 성장 지표, 함정 4축과 직교).
NEGATIVE_AXES: tuple[str, ...] = ("fear", "greed", "anxiety", "restlessness")
AXES: tuple[str, ...] = (*NEGATIVE_AXES, "composure")


@dataclass(frozen=True)
class PlayerEmotionState:
    """플레이어 자기인식 감정 게이지. 함정 4축(기본 0) + 평정(긍정, 기본 중립 50)."""

    fear: float = 0
    greed: float = 0
    anxiety: float = 0
    restlessness: float = 0
    composure: float = EQUILIBRIUM   # 평정 — 중립(50)에서 시작


def _clamp_value(value: float) -> float:
    return max(AXIS_MIN, min(AXIS_MAX, value))


def clamp(state: PlayerEmotionState) -> PlayerEmotionState:
    """모든 축을 [AXIS_MIN, AXIS_MAX]로 클램핑한 새 상태를 반환한다(입력 불변)."""
    return PlayerEmotionState(
        fear=_clamp_value(state.fear),
        greed=_clamp_value(state.greed),
        anxiety=_clamp_value(state.anxiety),
        restlessness=_clamp_value(state.restlessness),
        composure=_clamp_value(state.composure),
    )


def get_axis(state: PlayerEmotionState, axis: str) -> float:
    """이름으로 축 값을 읽는다. 미지의 축 이름이면 ValueError."""
    if axis not in AXES:
        raise ValueError(f"unknown player_emotion axis: {axis!r}")
    return getattr(state, axis)


def set_axis(state: PlayerEmotionState, axis: str, value: float) -> PlayerEmotionState:
    """axis를 value로 설정한 새 상태를 반환한다(클램핑 적용, 입력 불변).

    미지의 축 이름이면 ValueError.
    """
    if axis not in AXES:
        raise ValueError(f"unknown player_emotion axis: {axis!r}")
    updated = replace(state, **{axis: value})
    return clamp(updated)
