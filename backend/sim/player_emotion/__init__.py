"""player_emotion — 플레이어 자기인식 감정 게이지(4축: fear/greed/anxiety/restlessness).

기존 sim.agent_state(NPC 런타임 5축)·sim.interview(정적 Persona 트레잇)와는
원점·주체·소비처가 다른 완전히 독립된 시스템이다. 이름 충돌을 피하기 위해
공개 타입/모듈에는 player_emotion 접두를 사용한다.
"""

from .config import AXIS_MIN, AXIS_MAX, OVERHEAT_THRESHOLD, WITHDRAWAL_THRESHOLD
from .deltas import EVENT_DELTAS, apply_event
from .state import PlayerEmotionState, clamp, get_axis, set_axis
from .verdict import NEUTRAL, OVERHEAT, WITHDRAWAL, compute_score, compute_verdict

__all__ = [
    "AXIS_MIN",
    "AXIS_MAX",
    "OVERHEAT_THRESHOLD",
    "WITHDRAWAL_THRESHOLD",
    "PlayerEmotionState",
    "clamp",
    "get_axis",
    "set_axis",
    "EVENT_DELTAS",
    "apply_event",
    "OVERHEAT",
    "WITHDRAWAL",
    "NEUTRAL",
    "compute_score",
    "compute_verdict",
]
