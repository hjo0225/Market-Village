"""T-18: 동행배치 — 새 4축 엔진용 companion 결정 (얇은 어댑터).

기존 avoidance.py(순수 회피·클론 선택)와 personas.npc_scheds를 재사용한다.
옛 6함정 trap_scores 대신 4축 끌림: 클론(플레이어 거울)은 자기 감정에서 가장
높은(취약한) 축을 자극하는 NPC에게 끌린다 — npc_tone(T-10) 재사용. 동점은
id 사전순(결정론·회차 재현).
"""

from __future__ import annotations

from .npc_tone import npc_tone
from .player_emotion.state import AXES, PlayerEmotionState


def daily_candidates(place: str, schedules: dict[str, dict[int, str]]) -> list[str]:
    """그 장소에 일과가 있는 NPC들(정렬). schedules = {npc_id: {슬롯: 장소}}."""
    return sorted(
        npc for npc, sched in schedules.items() if place in sched.values()
    )


def pick_companion(
    candidates: list[str],
    emotion: PlayerEmotionState,
    designated: str | None = None,
) -> str | None:
    """후보 중 companion 1명. 플레이어가 designate하면 그를(후보일 때만), 아니면
    감정 최고 축을 가장 세게 자극하는 NPC. 후보 없으면 None."""
    if not candidates:
        return None
    if designated is not None and designated in candidates:
        return designated

    weak_axis = max(AXES, key=lambda a: getattr(emotion, a))
    return min(candidates, key=lambda n: (-npc_tone(n).get(weak_axis, 0.0), n))
