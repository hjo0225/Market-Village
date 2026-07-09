"""v3 §D1 — 진단 결과 화면(설문 직후): diagnosis_report.build_diagnosis +
POST /emo/start 응답의 diagnosis 필드.

axes/contributions/summary 스키마 검증 + 문항별 기여 분해가 QUESTIONS 점수
산식과 일치하는지(신규 계산은 점수 역추적뿐) + declared_type별 정적 요약 +
고정 마무리 문장.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sim import diagnosis_report as DR
from sim import disposition as D
from sim import emo_store
from sim.emo_api import router

ALL_MAX = {"Q1": 4, "Q2": 4, "Q3": 4, "Q4": 4, "Q5": 4, "Q6": 4, "Q7": 4}
ALL_MIN = {"Q1": 1, "Q2": 1, "Q3": 1, "Q4": 1, "Q5": 1, "Q6": 1, "Q7": 1}


def _client():
    emo_store._clear()
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# --- 스키마 ------------------------------------------------------------- #
def test_build_diagnosis_top_level_shape():
    diag = DR.build_diagnosis(ALL_MAX)
    assert set(diag) == {"declared_type", "axes", "contributions", "summary"}


def test_declared_type_matches_disposition_diagnose():
    diag = DR.build_diagnosis(ALL_MAX)
    assert diag["declared_type"] == D.diagnose(ALL_MAX)["declared_type"]
    assert diag["declared_type"] == "공격투자형"


def test_axes_has_capacity_and_attitude_with_scores_and_max():
    diag = DR.build_diagnosis(ALL_MAX)
    by_axis = {a["axis"]: a for a in diag["axes"]}
    assert set(by_axis) == {"capacity", "attitude"}
    for a in diag["axes"]:
        assert set(a) == {"axis", "label", "score", "max"}
        assert a["max"] == 100
    expected = D.diagnose(ALL_MAX)
    assert by_axis["capacity"]["score"] == expected["capacity_score"]
    assert by_axis["attitude"]["score"] == expected["attitude_score"]


# --- contributions: 문항별 기여 분해(점수 역추적) ------------------------ #
def test_contributions_one_row_per_question():
    diag = DR.build_diagnosis(ALL_MAX)
    assert len(diag["contributions"]) == len(D.QUESTIONS)
    assert [c["q"] for c in diag["contributions"]] == [q["id"] for q in D.QUESTIONS]


def test_contributions_row_shape_and_axis_matches_question_dim():
    diag = DR.build_diagnosis(ALL_MAX)
    q_by_id = {q["id"]: q for q in D.QUESTIONS}
    for c in diag["contributions"]:
        assert set(c) == {"q", "q_label", "choice_label", "axis", "points"}
        assert c["axis"] == q_by_id[c["q"]]["dim"]
        assert c["q_label"] == q_by_id[c["q"]]["text"]


def test_contributions_points_equal_score_times_weight():
    diag = DR.build_diagnosis(ALL_MAX)
    q_by_id = {q["id"]: q for q in D.QUESTIONS}
    for c in diag["contributions"]:
        q = q_by_id[c["q"]]
        # ALL_MAX → 모든 문항 최고 선택지(score=4) 선택.
        assert c["points"] == 4 * q["weight"]


def test_contributions_q5_weighted_double_reflected_in_points():
    diag = DR.build_diagnosis(ALL_MAX)
    q5 = next(c for c in diag["contributions"] if c["q"] == "Q5")
    assert q5["points"] == 8   # score 4 × weight 2


def test_contributions_choice_label_matches_chosen_option():
    diag = DR.build_diagnosis(ALL_MAX)
    q1 = next(c for c in diag["contributions"] if c["q"] == "Q1")
    assert q1["choice_label"] == "바로 산다. 기회는 안 기다려준다"


def test_contributions_reflect_min_answers_different_labels_and_points():
    diag = DR.build_diagnosis(ALL_MIN)
    q1 = next(c for c in diag["contributions"] if c["q"] == "Q1")
    assert q1["choice_label"] == "다들 탈 때가 제일 위험하다. 무시"
    assert q1["points"] == 1


def test_contributions_missing_answer_falls_back_to_neutral_score_2():
    diag = DR.build_diagnosis({})   # 전부 누락 → disposition._score 폴백 2
    for c in diag["contributions"]:
        q = next(q for q in D.QUESTIONS if q["id"] == c["q"])
        assert c["points"] == 2 * q["weight"]


# --- summary: declared_type별 2줄 + 고정 마무리 -------------------------- #
def test_summary_ends_with_fixed_closing_line():
    for answers in (ALL_MAX, ALL_MIN):
        diag = DR.build_diagnosis(answers)
        assert diag["summary"][-1] == (
            "클론은 이 성향대로 열흘을 산다. 진짜 당신과 같은지는, 끝에 확인하자."
        )


def test_summary_has_two_type_lines_plus_closing():
    diag = DR.build_diagnosis(ALL_MAX)
    assert len(diag["summary"]) == 3


def test_summary_differs_by_declared_type():
    max_summary = DR.build_diagnosis(ALL_MAX)["summary"]
    min_summary = DR.build_diagnosis(ALL_MIN)["summary"]
    assert max_summary[:2] != min_summary[:2]


def test_summary_covers_all_five_declared_types_without_crash():
    for dtype in D.DECLARED_TYPES:
        lines = DR._summary(dtype)
        assert len(lines) == 3
        assert lines[-1].startswith("클론은 이 성향대로")


# --- API 계약: POST /emo/start ------------------------------------------ #
def test_start_response_includes_diagnosis():
    c = _client()
    body = c.post("/emo/start", json={"answers": ALL_MAX, "seed": 1, "days": 5}).json()
    assert "diagnosis" in body
    assert body["diagnosis"]["declared_type"] == "공격투자형"
    assert len(body["diagnosis"]["contributions"]) == len(D.QUESTIONS)


def test_start_response_diagnosis_deterministic_same_answers():
    c = _client()
    b1 = c.post("/emo/start", json={"answers": ALL_MAX, "seed": 1, "days": 5}).json()
    b2 = c.post("/emo/start", json={"answers": ALL_MAX, "seed": 2, "days": 7}).json()
    assert b1["diagnosis"] == b2["diagnosis"]   # 진단은 답안에만 의존(seed/days 무관)
