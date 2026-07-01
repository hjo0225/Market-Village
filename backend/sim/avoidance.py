"""§9.2.1 회피 + §9.2.1b 클론의 NPC 선택 — 교류에 대한 플레이어 개입 (순수).

교류는 배치가 아니라 자연 발생(동선 겹침). 플레이어가 줄 수 있는 개입은 *회피* —
전날 밤 일과 항목 하나의 순서만 바꿔 만나기 싫은 NPC를 피한다(트레이드오프: 피한
자리에 누가 올지는 가봐야 안다).

같은 슬롯·장소에 NPC 여럿이 모이면 클론이 한 명을 골라 1:1 대화한다. 누구를
고르냐는 플레이어가 아니라 클론 성격 — *가장 약한 함정을 자극하는 NPC*에게 끌릴
확률이 높다(거울: "거북이도 있었는데 왜 하필 개구리한테…"). §11.4·§8.5와 같은
수치 기반이라 회차 재현(기둥3).
"""

from __future__ import annotations


def avoid(schedule: dict[int, str], slot_a: int, slot_b: int) -> dict[int, str]:
    """일과 항목 하나의 순서만 변경 = 두 슬롯의 내용을 맞바꾼다(원본 불변)."""
    out = dict(schedule)
    if slot_a in out and slot_b in out:
        out[slot_a], out[slot_b] = out[slot_b], out[slot_a]
    return out


def clone_picks_npc(
    candidates: list[str],
    clone_trap_scores: dict[str, float],
    npc_stim: dict[str, str | None],
) -> str | None:
    """§9.2.1b — 클론이 후보 NPC 중 한 명 선택. 가장 약한 함정을 자극하는 쪽에 끌림.

    npc_stim[npc] = 그 NPC가 자극하는 함정 id(없으면 None=안정형). 자극형 NPC는
    클론의 해당 함정 취약점만큼 매력적이고, 안정형은 가장 후순위. 동점은 id 사전순
    (결정론 → 회차 재현).
    """
    if not candidates:
        return None

    def attractiveness(npc: str) -> float:
        trap = npc_stim.get(npc)
        if trap is None:
            return -1.0                       # 안정형: 가장 덜 끌림
        return clone_trap_scores.get(trap, 0.0)

    # 매력도 내림차순, 동점은 id 오름차순
    return min(candidates, key=lambda n: (-attractiveness(n), n))
