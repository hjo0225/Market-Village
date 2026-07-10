"""T-47a — 정적 성향 진단 모듈 disposition.py.

스펙: 성향분석.md (투자자정보 확인서 기반 + MBTI 스타일 4축 표현).
순수함수 검증 + 부록 D(타당성 체크리스트)를 테스트로 고정한다.
"""

from __future__ import annotations

import pytest

from sim import disposition as D
from sim.player_emotion.state import AXES

# ── 편의: 극단 답안 세트 ────────────────────────────────────────────────
ALL_MAX = {f"Q{i}": 4 for i in range(1, 13)}
ALL_MIN = {f"Q{i}": 1 for i in range(1, 13)}
# 성향분석.md 예시형 답안(적극투자형)
SPEC_EX = {
    "Q1": 4, "Q2": 3, "Q3": 4,
    "Q4": 4, "Q5": 3, "Q6": 4,
    "Q7": 4, "Q8": 3, "Q9": 4,
    "Q10": 2, "Q11": 2, "Q12": 2,
}


# ── 채점 공식 (§2) ──────────────────────────────────────────────────────
def test_raw_score_formula_max():
    # 12문항 + Q3(손실감내도) 2배 = 11*4 + 8 = 52
    assert D.score_answers(ALL_MAX)["raw_score"] == 52


def test_raw_score_formula_min():
    # 11*1 + 2 = 13
    assert D.score_answers(ALL_MIN)["raw_score"] == 13


def test_loss_tolerance_weighted_double():
    base = dict(ALL_MIN)  # raw 13, Q3=1
    bumped = dict(ALL_MIN, Q3=2)  # Q3 +1 → raw +2 (가중 2배)
    assert (
        D.score_answers(bumped)["raw_score"]
        - D.score_answers(base)["raw_score"]
        == 2
    )


# ── 유형 경계 (§2) ──────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "raw,expected",
    [
        (13, "안정형"), (20, "안정형"),
        (21, "안정추구형"), (28, "안정추구형"),
        (29, "위험중립형"), (36, "위험중립형"),
        (37, "적극투자형"), (44, "적극투자형"),
        (45, "공격투자형"), (52, "공격투자형"),
    ],
)
def test_declared_type_boundaries(raw, expected):
    assert D.declared_type(raw) == expected


def test_declared_type_max_answers_is_aggressive():
    assert D.diagnose(ALL_MAX)["declared_type"] == "공격투자형"
    assert D.diagnose(ALL_MIN)["declared_type"] == "안정형"


# ── 하위차원 정규화 0~100 (§2, 부록 D) ──────────────────────────────────
def test_capacity_attitude_normalized_extremes():
    lo = D.score_answers(ALL_MIN)
    hi = D.score_answers(ALL_MAX)
    assert lo["capacity_score"] == 0 and lo["attitude_score"] == 0
    assert hi["capacity_score"] == 100 and hi["attitude_score"] == 100


def test_normalization_within_0_100_for_all():
    # 부록 D: 정규화 공식이 0~100을 벗어나지 않는가
    for ans in (ALL_MAX, ALL_MIN, SPEC_EX):
        s = D.score_answers(ans)
        assert 0 <= s["capacity_score"] <= 100
        assert 0 <= s["attitude_score"] <= 100


# ── 기대값 테이블 (§3) ──────────────────────────────────────────────────
def test_expected_bias_table_exact():
    assert D.expected_bias("안정형") == {"loss": 60, "fomo": 20, "disp": 40, "over": 15, "panic": 55}
    assert D.expected_bias("안정추구형") == {"loss": 55, "fomo": 30, "disp": 45, "over": 25, "panic": 45}
    assert D.expected_bias("위험중립형") == {"loss": 45, "fomo": 45, "disp": 50, "over": 40, "panic": 35}
    assert D.expected_bias("적극투자형") == {"loss": 35, "fomo": 60, "disp": 45, "over": 60, "panic": 25}
    assert D.expected_bias("공격투자형") == {"loss": 30, "fomo": 75, "disp": 40, "over": 75, "panic": 20}


def test_expected_bias_maps_exactly_5_axes():
    # 부록 D: expected_bias 테이블이 2층 5축과 정확히 매핑되는가
    for t in D.DECLARED_TYPES:
        assert set(D.expected_bias(t).keys()) == {"loss", "fomo", "disp", "over", "panic"}


# ── seed 수집 & 충돌 (§1, §3-②) ─────────────────────────────────────────
def test_seeds_collected_from_choices():
    seeds = set(D.diagnose(ALL_MAX)["seeds"])
    assert {"greed", "fomo"} <= seeds  # Q1 score4
    assert "over" in seeds             # Q5 score4


def test_seed_conflict_disposition():
    # Q5=2(조금오르면 익절=disposition_sell) + Q2=3(존버=disposition_hold) → 충돌
    ans = dict(ALL_MIN, Q2=3, Q5=2)
    assert "disposition" in D.diagnose(ans)["seed_conflicts"]


def test_no_disposition_conflict_when_consistent():
    ans = dict(ALL_MAX, Q2=4, Q5=4)  # 존버 아님 + 목표가까지 안팜
    assert "disposition" not in D.diagnose(ans)["seed_conflicts"]


# ── 부록 C: 하위차원 괴리 ───────────────────────────────────────────────
def test_subdimension_attitude_over_capacity():
    # 태도(욕망) 높고 감당능력 낮음: attitude≫capacity
    assert D.subdimension_pattern(attitude_score=90, capacity_score=20) == "attitude_over_capacity"


def test_subdimension_capacity_over_attitude():
    assert D.subdimension_pattern(attitude_score=20, capacity_score=90) == "capacity_over_attitude"


def test_subdimension_balanced_when_close():
    assert D.subdimension_pattern(attitude_score=55, capacity_score=50) == "balanced"


# ── §4 스키마 ───────────────────────────────────────────────────────────
def test_diagnose_schema_keys_and_type():
    d = D.diagnose(SPEC_EX)
    for k in ("answers", "raw_score", "declared_type", "capacity_score",
              "attitude_score", "risk_grade", "mbti_type", "mbti_name",
              "mbti_axes", "seeds", "seed_conflicts", "expected_bias"):
        assert k in d
    assert d["raw_score"] == 43
    assert d["declared_type"] == "적극투자형"
    assert d["risk_grade"] == "2등급 이하"
    assert d["expected_bias"] == {"loss": 35, "fomo": 60, "disp": 45, "over": 60, "panic": 25}


def test_mbti_type_and_axes():
    d = D.diagnose({
        "Q1": 4, "Q2": 4, "Q3": 4,
        "Q4": 4, "Q5": 4, "Q6": 3,
        "Q7": 4, "Q8": 4, "Q9": 4,
        "Q10": 1, "Q11": 1, "Q12": 1,
    })
    assert d["mbti_type"] == "ALDR"
    assert d["mbti_name"] == "냉혈 설계자"
    assert d["mbti_axes"]["AS"]["selected"] == "A"
    assert d["mbti_axes"]["RE"]["selected"] == "R"


# ── build_initial_emotion_v2 (12문항 → 감정 초기화) ─────────────────────
def test_v2_aggressive_high_greed_low_fear():
    st = D.build_initial_emotion_v2(ALL_MAX)
    assert st.greed > 50
    assert st.fear < 50


def test_v2_conservative_high_fear_low_greed():
    st = D.build_initial_emotion_v2(ALL_MIN)
    assert st.fear > 50
    assert st.greed < 50


def test_v2_composure_starts_neutral():
    # T-37: 평정은 게임 중 원칙있는 선택으로만 성장 → 초기 중립 50
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


# ── 부록 D: 타당성 체크리스트 ───────────────────────────────────────────
def test_appendixD_questions_shape():
    # 12문항, 각 최소 3선택지, 점수 1~4
    assert len(D.QUESTIONS) == 12
    for q in D.QUESTIONS:
        assert len(q["options"]) >= 3
        for opt in q["options"]:
            assert 1 <= opt["score"] <= 4
            assert opt["pole"] in (-1, 1)


def test_appendixD_loss_tolerance_is_weighted():
    q3 = next(q for q in D.QUESTIONS if q["id"] == "Q3")
    assert q3["weight"] == 2
    assert all(q["weight"] == 1 for q in D.QUESTIONS if q["id"] != "Q3")


def test_appendixD_every_type_reachable():
    # 각 declared_type이 실제 도달 가능한 점수 범위인가(경계 검증)
    seen = {D.declared_type(raw) for raw in range(13, 53)}
    assert seen == set(D.DECLARED_TYPES)


def test_appendixD_neutral_option_may_lack_seed():
    # 중립 선택지는 seed 없음 허용 — Q1 score2(알아본다)는 seed 비어있음
    q1 = next(q for q in D.QUESTIONS if q["id"] == "Q1")
    mid = next(o for o in q1["options"] if o["score"] == 2)
    assert mid["seed"] == []


def test_appendixD_each_mbti_axis_has_three_questions():
    counts = {}
    for q in D.QUESTIONS:
        counts[q["axis"]] = counts.get(q["axis"], 0) + 1
    assert counts == {"AS": 3, "LQ": 3, "DF": 3, "RE": 3}
