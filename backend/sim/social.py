"""§9.2.2/§9.2.3 교류 — 1:1 권유 + FGI 단톡방 개입 (순수/결정론).

1:1 권유(§9.2.2): 위기 개입(§11.4)과 **같은 문법**(래포+격앙, roll<성공률→성공) —
단 전략 A/B/C 대신 격화/안정 방향 하나만(가볍고 빈번한 평소 관리). 위기 개입과
**같은 래포 풀**을 공유한다(§11.4.4) — 여기서도 `resistance.update_rapport`를
그대로 쓴다.

FGI 단톡방(§9.2.3): 익명 참여자로 글을 얹는 것이라 **래포가 안 통한다**(그래서
`fgi_post`는 rapport를 받지 않는다). 톤-감정 적합으로만 먹히고, 약하고 불확실
(묻힐 수 있음), 군중 자체가 이미 극단이면 흡수되어 아예 안 먹힌다(§9.3 폭주방지
정합).
"""

from __future__ import annotations

from . import resistance as RES
from . import tuning as T

# --------------------------------------------------------------------------- #
# 1:1 권유 (§9.2.2)
# --------------------------------------------------------------------------- #
DIRECTION_CALM = "calm"
DIRECTION_ESCALATE = "escalate"


def persuade_success(rapport: float, escalation: float = 0.0) -> float:
    """§9.2.2 — 위기개입과 같은 문법(§11.5.3), 전략적합 항만 뺌(구조 단순화).

    base 50 + (래포−50)×0.4 − 격앙×0.5, clamp(0, 95) — 대화 권유는 결코 100%
    먹히지 않는다(가볍지만 확실하진 않음).
    """
    raw = T.RESIST_BASE + (rapport - T.RAPPORT_MID) * T.RAPPORT_SCALE - escalation * T.ESCALATION_SCALE
    return T.clamp(raw, 0.0, 95.0)


def apply_persuasion(
    direction: str, stat_name: str, stats: dict[str, float],
    rapport: float, roll: float = 100.0, escalation: float = 0.0,
) -> dict:
    """권유 1건 적용 — 성공하면 방향대로 관련 스탯 ±(§11.5.4 대화권유 보정 3),
    실패해도 성공해도 래포는 갱신된다(같은 풀, §11.4.4). roll<성공률 → 성공.
    """
    prob = persuade_success(rapport, escalation)
    accepted = roll < prob
    new_stats = dict(stats)
    if accepted and stat_name in new_stats:
        delta = T.PERSUASION_BONUS if direction == DIRECTION_CALM else -T.PERSUASION_BONUS
        new_stats[stat_name] = T.clamp(new_stats[stat_name] + delta, T.STAT_MIN, T.STAT_MAX)
    new_rapport = RES.update_rapport(rapport, accepted)
    return {"accepted": accepted, "success_prob": prob, "stats": new_stats, "rapport": new_rapport}


# --------------------------------------------------------------------------- #
# FGI 단톡방 (§9.2.3) — 익명 참여자, 래포 무관, 약하고 불확실
# --------------------------------------------------------------------------- #
# PRD §11.5엔 FGI 전용 수치가 없음 — 1:1(±3)보다 확실히 작게 잡은 튜닝 출발점.
_FGI_MAGNITUDE = 2.0
_FGI_APPLY_CHANCE = 40.0     # 0~100 스케일. 여러 목소리 중 하나라 안 먹힐 수 있음.
_FGI_ABSORB_THRESHOLD = 90.0  # 이미 만렙으로 들끓는 방이면 플레이어 글이 묻힘.

_TONE_DIRECTION = {"calm": -1, "clarify": -1, "fear_join": 1}


def fgi_post(
    tone: str, crowd_mood: float, clone_stat_value: float, roll: float = 100.0,
) -> dict:
    """단톡방에 톤 하나를 얹는다. crowd_mood는 군중 과열도(높을수록 들끓음).

    이미 만렙(≥90)으로 들끓으면 흡수(안 먹힘, §9.3 폭주방지). 아니면 확률적으로
    (roll<40) 군중을 톤 방향으로, 클론은 그 절반만 반대(완화)로 살짝 민다.
    """
    if crowd_mood >= _FGI_ABSORB_THRESHOLD:
        return {"crowd_mood": crowd_mood, "clone_stat_value": clone_stat_value,
                "clone_delta_applied": 0.0, "absorbed": True}
    if roll >= _FGI_APPLY_CHANCE:
        return {"crowd_mood": crowd_mood, "clone_stat_value": clone_stat_value,
                "clone_delta_applied": 0.0, "absorbed": False}

    direction = _TONE_DIRECTION.get(tone, 0)
    new_crowd = T.clamp(crowd_mood + direction * _FGI_MAGNITUDE, 0.0, 100.0)
    clone_delta = -direction * _FGI_MAGNITUDE * 0.5   # 군중 진정 → 클론 내성 소폭↑
    new_clone = T.clamp(clone_stat_value + clone_delta, T.STAT_MIN, T.STAT_MAX)
    return {"crowd_mood": new_crowd, "clone_stat_value": new_clone,
            "clone_delta_applied": clone_delta, "absorbed": False}
