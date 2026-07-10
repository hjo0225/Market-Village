"""정적 성향 진단 모듈 disposition.py.

스펙: 성향분석.md (전국투자자교육협의회 '투자 성향 진단표' 7문항 재구성 → 5단계).
순수함수 검증 + 타당성 체크리스트를 테스트로 고정한다.
"""

from __future__ import annotations

import pytest

from sim import disposition as D
from sim.player_emotion.state import AXES

# ── 편의: 극단 답안 세트(각 문항 최대/최소 점수) ────────────────────────
ALL_MAX = {q["id"]: max(o["points"] for o in q["options"]) for q in D.QUESTIONS}
ALL_MIN = {q["id"]: min(o["points"] for o in q["options"]) for q in D.QUESTIONS}
# 적극투자형 예시 답안(총점 39)
SPEC_EX = {"Q1": 8, "Q2": 3, "Q3": 6, "Q4": 4, "Q5": 4, "Q6": 6, "Q7": 8}


# ── 채점 공식 ───────────────────────────────────────────────────────────
def test_raw_score_max():
    # 10+5+10+6+6+6+10 = 53
    assert D.score_answers(ALL_MAX)["raw_score"] == 53


def test_raw_score_min():
    # 2+1+2+1+2+3+2 = 13
    assert D.score_answers(ALL_MIN)["raw_score"] == 13


def test_raw_score_spec_example():
    assert D.score_answers(SPEC_EX)["raw_score"] == 39


def test_invalid_answer_falls_back_to_mid():
    # 유효 옵션이 아닌 값은 중앙값으로 폴백(결정론)
    assert D.diagnose({"Q1": 999})["answers"]["Q1"] == 6


# ── 유형 경계 (원 진단표 컷오프 20/28/36/44/45) ─────────────────────────
@pytest.mark.parametrize(
    "raw,expected",
    [
        (13, "안정형"), (20, "안정형"),
        (21, "안정추구형"), (28, "안정추구형"),
        (29, "위험중립형"), (36, "위험중립형"),
        (37, "적극투자형"), (44, "적극투자형"),
        (45, "공격투자형"), (53, "공격투자형"),
    ],
)
def test_declared_type_boundaries(raw, expected):
    assert D.declared_type(raw) == expected


def test_extreme_answers_map_to_extreme_types():
    assert D.diagnose(ALL_MAX)["declared_type"] == "공격투자형"
    assert D.diagnose(ALL_MIN)["declared_type"] == "안정형"


# ── 하위차원 정규화 0~100 ───────────────────────────────────────────────
def test_capacity_attitude_normalized_extremes():
    lo = D.score_answers(ALL_MIN)
    hi = D.score_answers(ALL_MAX)
    assert lo["capacity_score"] == 0 and lo["attitude_score"] == 0
    assert hi["capacity_score"] == 100 and hi["attitude_score"] == 100


def test_normalization_within_0_100_for_all():
    for ans in (ALL_MAX, ALL_MIN, SPEC_EX, {}):
        s = D.score_answers(ans)
        assert 0 <= s["capacity_score"] <= 100
        assert 0 <= s["attitude_score"] <= 100


# ── 기대값 테이블 ───────────────────────────────────────────────────────
def test_expected_bias_table_exact():
    assert D.expected_bias("안정형") == {"loss": 60, "fomo": 20, "disp": 40, "over": 15, "panic": 55}
    assert D.expected_bias("공격투자형") == {"loss": 30, "fomo": 75, "disp": 40, "over": 75, "panic": 20}


def test_expected_bias_maps_exactly_5_axes():
    for t in D.DECLARED_TYPES:
        assert set(D.expected_bias(t).keys()) == set(D.BIAS_AXES)


# ── seed 수집 ───────────────────────────────────────────────────────────
def test_seeds_collected_from_choices():
    seeds = set(D.diagnose(ALL_MAX)["seeds"])
    assert {"greed", "over", "fomo"} <= seeds  # Q1=10
    conservative = set(D.diagnose(ALL_MIN)["seeds"])
    assert {"loss_aversion", "fear", "composure"} <= conservative


def test_no_seed_conflicts_now():
    assert D.diagnose(ALL_MAX)["seed_conflicts"] == []


# ── 하위차원 괴리 ───────────────────────────────────────────────────────
def test_subdimension_attitude_over_capacity():
    assert D.subdimension_pattern(attitude_score=90, capacity_score=20) == "attitude_over_capacity"


def test_subdimension_capacity_over_attitude():
    assert D.subdimension_pattern(attitude_score=20, capacity_score=90) == "capacity_over_attitude"


def test_subdimension_balanced_when_close():
    assert D.subdimension_pattern(attitude_score=55, capacity_score=50) == "balanced"


# ── 진단 스키마 ─────────────────────────────────────────────────────────
def test_diagnose_schema_keys_and_values():
    d = D.diagnose(SPEC_EX)
    for k in ("answers", "raw_score", "declared_type", "type_desc", "risk_grade",
              "capacity_score", "attitude_score", "seeds", "seed_conflicts",
              "expected_bias", "source"):
        assert k in d
    assert d["declared_type"] == "적극투자형"
    assert d["risk_grade"] == "2등급 이하"
    assert d["expected_bias"] == {"loss": 35, "fomo": 60, "disp": 45, "over": 60, "panic": 25}


def test_diagnose_has_no_mbti_fields():
    d = D.diagnose(SPEC_EX)
    assert not any(k.startswith("mbti") for k in d)


# ── build_initial_emotion_v2 (7문항 → 감정 초기화) ──────────────────────
def test_v2_aggressive_high_greed_low_fear():
    st = D.build_initial_emotion_v2(ALL_MAX)
    assert st.greed > 50 and st.fear < 50


def test_v2_conservative_high_fear_low_greed():
    st = D.build_initial_emotion_v2(ALL_MIN)
    assert st.fear > 50 and st.greed < 50


def test_v2_composure_starts_neutral():
    assert D.build_initial_emotion_v2(ALL_MAX).composure == 50
    assert D.build_initial_emotion_v2(ALL_MIN).composure == 50


def test_v2_empty_answers_neutral():
    st = D.build_initial_emotion_v2({})
    for axis in AXES:
        assert 45 <= getattr(st, axis) <= 55


def test_v2_deterministic_and_clamped():
    a = D.build_initial_emotion_v2(SPEC_EX)
    b = D.build_initial_emotion_v2(SPEC_EX)
    assert a == b
    for axis in AXES:
        assert 0 <= getattr(a, axis) <= 100


# ── 타당성 체크리스트 ───────────────────────────────────────────────────
def test_questions_shape():
    # 7문항, 각 최소 2선택지, 점수는 문항 내 유일한 양수
    assert len(D.QUESTIONS) == 7
    for q in D.QUESTIONS:
        pts = [o["points"] for o in q["options"]]
        assert len(q["options"]) >= 2
        assert all(p > 0 for p in pts)
        assert len(set(pts)) == len(pts)  # 문항 내 유일(역참조 전제)
        assert q["dim"] in ("capacity", "attitude")


def test_every_type_reachable():
    seen = {D.declared_type(raw) for raw in range(13, 54)}
    assert seen == set(D.DECLARED_TYPES)
