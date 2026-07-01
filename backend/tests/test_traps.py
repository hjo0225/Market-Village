"""T-101 · §8.2 6함정 분류 + §8.5 트리거 감지/정렬 검증.

6함정(F1 급락패닉 / F2 멘탈마모 / G1 익절거부 / G2 과대베팅 / M1 추격매수 /
M2 막차불안)을 명시 식별자로 모델링하고, §8.2/§11.5 조건으로 발동을 감지,
§8.5 STEP2 우선순위(단발>누적, 취약점 높은 함정 우선)로 1개를 선정한다.
순수함수.
"""

from __future__ import annotations

from sim import traps
from sim.traps import CrisisContext


# --- 분류 (§8.2) --------------------------------------------------------- #
def test_six_traps_defined():
    ids = {t.id for t in traps.ALL_TRAPS}
    assert ids == {"F1", "F2", "G1", "G2", "M1", "M2"}
    by = {t.id: t for t in traps.ALL_TRAPS}
    # 올바른 행동: F계열=보유유지, G1=차익실현, M계열=진입보류 (정반대 §8.2)
    assert by["F1"].correct_action == "hold"
    assert by["G1"].correct_action == "take_profit"
    assert by["M1"].correct_action == "hold_off"
    # 트리거 타입: F1·M1=단발, F2=누적, G1·G2=상태의존
    assert by["F1"].trigger_type == "single"
    assert by["M1"].trigger_type == "single"
    assert by["F2"].trigger_type == "cumulative"
    assert by["G1"].trigger_type == "state"
    # 그룹(공포/탐욕/FOMO)
    assert by["F1"].group == "fear" and by["G1"].group == "greed"
    assert by["M2"].group == "fomo"


# --- 트리거 감지 (§8.2 / §11.5 임계) ------------------------------------ #
def test_f1_crash_triggers():
    ctx = CrisisContext(change_pct=-16.0)
    assert "F1" in traps.detect_triggers(ctx)
    # −14%는 미발동
    assert "F1" not in traps.detect_triggers(CrisisContext(change_pct=-14.0))


def test_f2_wear_triggers_by_streak_or_gauge():
    assert "F2" in traps.detect_triggers(CrisisContext(dip_streak=4))
    assert "F2" in traps.detect_triggers(CrisisContext(wear_gauge=70.0))
    assert "F2" not in traps.detect_triggers(CrisisContext(dip_streak=3, wear_gauge=69.0))


def test_g1_g2_triggers():
    assert "G1" in traps.detect_triggers(CrisisContext(holding_profit_pct=30.0))
    assert "G1" not in traps.detect_triggers(CrisisContext(holding_profit_pct=29.0))
    # G2 = confidence≥75 AND 직전 수익 실현
    assert "G2" in traps.detect_triggers(
        CrisisContext(confidence=75.0, just_realized_profit=True)
    )
    assert "G2" not in traps.detect_triggers(
        CrisisContext(confidence=90.0, just_realized_profit=False)
    )


def test_m1_m2_triggers():
    assert "M1" in traps.detect_triggers(CrisisContext(unheld_surge_pct=20.0))
    assert "M1" not in traps.detect_triggers(CrisisContext(unheld_surge_pct=19.0))
    # M2 = FGI≥75 AND 군중 매수 우세
    assert "M2" in traps.detect_triggers(CrisisContext(fgi=80.0, crowd_buying=True))
    assert "M2" not in traps.detect_triggers(CrisisContext(fgi=80.0, crowd_buying=False))


def test_calm_day_no_triggers():
    assert traps.detect_triggers(CrisisContext()) == set()


# --- 정렬 (§8.5 STEP2) --------------------------------------------------- #
def test_prioritize_single_shock_first():
    # F1(단발) vs G1(상태의존) 동시 → 단발 먼저 (급한 불)
    chosen = traps.prioritize({"F1", "G1"}, vulnerability={"F1": 10, "G1": 99})
    assert chosen == "F1"


def test_prioritize_breaks_tie_by_vulnerability():
    # F1·M1 둘 다 단발 → 취약점 높은 함정 우선
    chosen = traps.prioritize({"F1", "M1"}, vulnerability={"F1": 30, "M1": 80})
    assert chosen == "M1"


def test_prioritize_empty_is_none():
    assert traps.prioritize(set(), vulnerability={}) is None


def test_prioritize_missing_vulnerability_defaults():
    # 취약점 정보 없으면 0으로 폴백 — 크래시하지 않음
    chosen = traps.prioritize({"F2", "G1"}, vulnerability={})
    assert chosen in {"F2", "G1"}
