"""§11.4 개입 시스템 — A/B/C 전략 + 래포 + 4요소 저항식 (순수 규칙).

황금률(§11.1): 저항의 원인은 100% 투명(무력감 방지), 극복은 결코 100% 불가
(꼭두각시 방지). 개입 성공 = f(래포, 전략 적합도, 격앙도, 기질 바닥)(§11.4.3).

세 버튼(A/B/C)은 클론을 멈추게 하는 서로 다른 심리적 지렛대(§11.4.2):
  A 과거 찌르기  — 과거 기록 직면 → 수치심·후회 (자존심 센 클론엔 역효과)
  B 함정 직시    — 감정에 이름 붙여 메타인지 (이미 극도 격앙이면 무효)
  C 감정 다독임  — 정서적 안정 (탐욕 계열엔 약함)

⚠️ 여기 '래포'는 클론↔플레이어 유대다. 코드의 trust(감정 5축)는 '정보 신뢰'로
완전히 다른 값(§11.4.3) — 이 모듈은 trust를 인자로 받지 않는다(구조적 분리).

수치는 전부 §11.5(sim.tuning)에서 읽는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import tuning as T
from .traps import Trap

STRATEGY_A = "A_과거찌르기"
STRATEGY_B = "B_함정직시"
STRATEGY_C = "C_감정다독임"
STRATEGIES = (STRATEGY_A, STRATEGY_B, STRATEGY_C)

# 격앙도가 이 값 이상이면 B(이성적 호소)는 무효 ("알아 근데 못 멈춰", §11.4.2)
_B_NUMB_ESCALATION = 70.0
# 래포 누적 폭(§11.4.4) — §11.5에 명시 없음, 튜닝 출발점
_RAPPORT_STEP = 8.0


@dataclass
class CloneProfile:
    """저항 판정이 읽는 클론의 1층 기질 + 성향 플래그(§5 인터뷰 산출)."""

    trap_scores: dict[str, float] = field(default_factory=dict)  # F1.. → 취약점 0~100
    weakness_threshold: float = 50.0   # trap_score ≥ 이면 '약점 함정'
    prideful: bool = False             # 자존심 센 → A 역효과
    self_aware: bool = False           # 자기인식 → B 적합
    anxious: bool = False              # 불안형 → C 적합
    learns_from_past: bool = False     # 과거서 배움 → A 적합

    def is_weak(self, trap_id: str) -> bool:
        return self.trap_scores.get(trap_id, 0.0) >= self.weakness_threshold


def strategy_fit(
    strategy: str, trap: Trap, clone: CloneProfile, escalation: float
) -> float:
    """고른 전략이 이 클론·상황에 맞는가 → +20 / 0 / −30 (§11.4.2)."""
    if strategy == STRATEGY_A:
        if clone.prideful:
            return T.STRATEGY_BACKFIRE        # 가장 명확한 역효과(§11.4.2b)
        if clone.learns_from_past:
            return T.STRATEGY_FIT_BONUS
        return T.STRATEGY_NEUTRAL
    if strategy == STRATEGY_B:
        if escalation >= _B_NUMB_ESCALATION:
            return T.STRATEGY_NEUTRAL          # 이미 극도 격앙 → 무효
        if clone.self_aware:
            return T.STRATEGY_FIT_BONUS
        return T.STRATEGY_NEUTRAL
    if strategy == STRATEGY_C:
        if trap.group == "greed":
            return T.STRATEGY_NEUTRAL          # 탐욕엔 약함(불안이 아니라 욕심)
        if clone.anxious or trap.group == "fear":
            return T.STRATEGY_FIT_BONUS
        return T.STRATEGY_NEUTRAL
    return T.STRATEGY_NEUTRAL


def intervention_success(
    rapport: float,
    strategy: str,
    clone: CloneProfile,
    trap: Trap,
    escalation: float,
) -> float:
    """§11.5.3 개입 성공 확률(%).

    base 50 + (래포−50)×0.4 + 전략적합(+20/0/−30) − 격앙×0.5
    최종 = clamp(합, 0, 기질바닥 상한[약점70 / 비약점95]).
    """
    fit = strategy_fit(strategy, trap, clone, escalation)
    raw = (
        T.RESIST_BASE
        + (rapport - T.RAPPORT_MID) * T.RAPPORT_SCALE
        + fit
        - escalation * T.ESCALATION_SCALE
    )
    floor = T.trait_floor(clone.is_weak(trap.id))
    return T.clamp(raw, 0.0, floor)


def update_rapport(rapport: float, was_right: bool) -> float:
    """§11.4.4 — '팔지마'→반등이면 ↑, '사지마'→폭등이면 ↓. 클램프 0~100."""
    step = _RAPPORT_STEP if was_right else -_RAPPORT_STEP
    return T.clamp(rapport + step, 0.0, 100.0)


def failure_reason(
    rapport: float,
    strategy: str,
    clone: CloneProfile,
    trap: Trap,
    escalation: float,
) -> str:
    """§11.4.5 — 개입이 씹힌 이유를 사람이 읽게 표시 (무력감 방지 §11.3)."""
    parts: list[str] = []
    if rapport < 40.0:
        parts.append("래포 낮음(과거 틀린 조언)")
    if escalation >= _B_NUMB_ESCALATION:
        parts.append("격앙도 임계 초과(이미 극도 함정)")
    if strategy_fit(strategy, trap, clone, escalation) == T.STRATEGY_BACKFIRE:
        parts.append("전략 역효과(자존심+과거찌르기)")
    if clone.is_weak(trap.id):
        parts.append(f"약점 함정 {trap.id}(기질 바닥)")
    if not parts:
        parts.append("운나쁜 판정")
    return " + ".join(parts) + " → 무시됨"
