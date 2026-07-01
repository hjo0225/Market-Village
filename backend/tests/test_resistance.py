"""T-105 · §11.4 개입 시스템 — A/B/C 전략 + 래포 + 4요소 저항식.

황금률(§11.1): 저항의 원인은 100% 투명, 극복은 결코 100% 불가.
개입 성공 = f(래포, 전략 적합도, 격앙도, 기질 바닥)  (§11.4.3 / §11.5.3).
래포(클론↔플레이어 유대)는 trust(정보 신뢰)와 다른 값(§11.4.3 ⚠️).
"""

from __future__ import annotations

from sim import resistance as R
from sim.resistance import CloneProfile
from sim.traps import get_trap

F1 = get_trap("F1")   # fear, 약점 가정
G2 = get_trap("G2")   # greed


def _clone(**kw):
    base = dict(trap_scores={"F1": 80.0, "G2": 80.0}, weakness_threshold=50.0)
    base.update(kw)
    return CloneProfile(**base)


def test_three_strategies():
    assert set(R.STRATEGIES) == {R.STRATEGY_A, R.STRATEGY_B, R.STRATEGY_C}
    assert "과거" in R.STRATEGY_A and "직시" in R.STRATEGY_B and "다독" in R.STRATEGY_C


def test_base_formula_midpoint():
    # 래포 50, 중립전략, 격앙 0, 비약점 → 50%
    clone = _clone(trap_scores={"F1": 10.0})  # F1 비약점
    p = R.intervention_success(50.0, R.STRATEGY_B, clone, F1, escalation=0.0)
    assert abs(p - 50.0) < 1e-9


def test_rapport_raises_success():
    clone = _clone(trap_scores={"F1": 10.0})
    # 래포 100 → (100−50)*0.4 = +20 → 70 (중립전략 가정: B는 self_aware 아니면 중립)
    p = R.intervention_success(100.0, R.STRATEGY_B, clone, F1, escalation=0.0)
    assert abs(p - 70.0) < 1e-9


def test_escalation_penalty():
    clone = _clone(trap_scores={"F1": 10.0})
    # 격앙도 100 → −50 → base 50 − 50 = 0
    p = R.intervention_success(50.0, R.STRATEGY_B, clone, F1, escalation=100.0)
    assert p == 0.0


def test_strategy_fit_bonus_for_self_aware_B():
    clone = _clone(trap_scores={"F1": 10.0}, self_aware=True)
    # B 함정직시 + 자기인식 클론 + 낮은 격앙 → +20 적합
    p = R.intervention_success(50.0, R.STRATEGY_B, clone, F1, escalation=0.0)
    assert abs(p - 70.0) < 1e-9


def test_strategy_backfire_prideful_plus_A():
    clone = _clone(trap_scores={"F1": 10.0}, prideful=True)
    # A 과거찌르기 + 자존심 센 클론 → −30 역효과 (§11.4.2b 가장 명확한 역효과)
    p = R.intervention_success(50.0, R.STRATEGY_A, clone, F1, escalation=0.0)
    assert abs(p - 20.0) < 1e-9


def test_trait_floor_caps_weak_trap():
    # 약점 함정(F1 score 80 ≥ 50)은 모든 게 좋아도 70% 상한 (§11.1 30% 무조건 무시)
    clone = _clone(self_aware=True)  # F1=80 → 약점
    p = R.intervention_success(100.0, R.STRATEGY_B, clone, F1, escalation=0.0)
    # raw = 50 + 20(래포) + 20(적합) = 90 → 약점 상한 70
    assert p == 70.0


def test_nonweak_trap_higher_ceiling():
    clone = _clone(trap_scores={"F1": 10.0}, self_aware=True)
    # raw = 50 + 20(래포) + 20(적합 B+자기인식) = 90, 비약점 상한 95 → 90 그대로
    p = R.intervention_success(100.0, R.STRATEGY_B, clone, F1, escalation=0.0)
    assert abs(p - 90.0) < 1e-9


def test_update_rapport_accumulates_and_clamps():
    assert R.update_rapport(50.0, was_right=True) > 50.0
    assert R.update_rapport(50.0, was_right=False) < 50.0
    assert R.update_rapport(100.0, was_right=True) == 100.0   # 상한 클램프
    assert R.update_rapport(0.0, was_right=False) == 0.0      # 하한 클램프


def test_failure_reason_names_factors():
    clone = _clone(prideful=True)
    reason = R.failure_reason(20.0, R.STRATEGY_A, clone, F1, escalation=90.0)
    assert "래포" in reason          # 래포 낮음
    assert "격앙" in reason          # 격앙도 임계 초과
    assert "→" in reason             # "...→ 무시됨" 형태


def test_rapport_is_not_trust():
    # 구조적 분리: resistance는 trust(정보신뢰)를 인자로 받지 않는다.
    import inspect

    sig = inspect.signature(R.intervention_success)
    assert "rapport" in sig.parameters
    assert "trust" not in sig.parameters
