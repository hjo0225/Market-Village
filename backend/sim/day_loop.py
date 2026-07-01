"""§12 일일 루프 — 8슬롯 하루 구조 + 일과 셔플 + 확률 외란 (순수/결정론).

동선 겹침(§9.2.1b)·교류 발생을 계산하려면 하루가 명확한 이산 칸으로 나뉘어야 한다:
8슬롯 = 4시간대(오전/점심/오후/저녁) × 2(§12.1b). 일과 행동 *종류*는 고정 메뉴이고
*순서*만 회차마다 셔플된다(§12.2) — 통제변인 유지 + 마을이 매번 살아 보임. 단
**순서발 감정효과는 0**(카페 먼저 갔다고 기분 좋아지는 일 없음).

확률 외란(§12.3): 일과 사이 작은 사건이 20%/일 발생, ±2~4 감정 변동. 단 매매를
직접 강제하지 않는다 — "방아쇠는 당기되 결과를 결정하지 않는다."
"""

from __future__ import annotations

import random

from . import tuning as T

TIMESLOTS = ("오전", "점심", "오후", "저녁")


def day_slots() -> list[dict]:
    """8슬롯(1~8)에 시간대 라벨을 붙여 반환."""
    return [{"index": i + 1, "timeslot": TIMESLOTS[i // 2]} for i in range(8)]


def shuffle_schedule(menu: list[str], rng: random.Random) -> list[str]:
    """일과 순서를 셔플(종류 집합 불변). 결정론(시드 rng)."""
    out = list(menu)
    rng.shuffle(out)
    return out


def schedule_emotion_effect(schedule: list[str]) -> float:
    """§12.2 — 순서발 효과 금지. 어떤 순서든 감정 효과는 항상 0."""
    return 0.0


def overlap_meetings(
    clone_sched: dict[int, str], npc_scheds: dict[str, dict[int, str]]
) -> dict[int, list[str]]:
    """같은 슬롯·같은 장소에 도착한 NPC들 → 1:1 대화 후보(§9.2.2).

    여럿이 겹치면 후보를 모두 반환한다. 그중 누구와 대화할지(§9.2.1b 클론이 약점
    강한 쪽으로 끌림)는 별도 판정(resistance/clone)의 몫.
    """
    meetings: dict[int, list[str]] = {}
    for slot, place in clone_sched.items():
        present = [
            nid for nid, sched in npc_scheds.items() if sched.get(slot) == place
        ]
        if present:
            meetings[slot] = present
    return meetings


def roll_disturbance(rng: random.Random) -> dict | None:
    """§12.3 — 20%/일 확률로 ±2~4 외란. 없으면 None. 매매는 강제하지 않는다."""
    if rng.random() >= T.DISTURBANCE_PROB:
        return None
    lo, hi = T.DISTURBANCE_SIZE_RANGE
    size = rng.uniform(lo, hi)
    sign = 1 if rng.random() < 0.5 else -1
    return {"sign": sign, "size": round(size, 2), "delta": round(sign * size, 2)}


def clone_disturbance(clone_spec, rng: random.Random) -> dict | None:
    """§5.4 — 일과 외란이 떴을 때 클론 고유 이벤트(커피 쏟음 등)로 채운다.

    효과는 작게(§12.3): delta는 멘탈회복에 ±2~4. None이면 평온한 하루.
    """
    d = roll_disturbance(rng)
    if d is None:
        return None
    events = getattr(clone_spec, "unique_events", None) or [
        {"id": "ordinary_day", "trigger": "평범한 하루", "effect": "감정 미동"}]
    ev = events[rng.randrange(len(events))]
    return {"id": ev["id"], "trigger": ev["trigger"], "effect": ev["effect"],
            "delta": d["delta"]}
