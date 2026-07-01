"""N5 인터뷰 온보딩: 적응형 문항, 결정론 변환, 폴백, 무경험 분기."""

from __future__ import annotations

from sim.interview import build_player_persona, next_question
from sim.models import Persona


def test_next_question_returns_question_then_none_at_cap():
    answers = {}
    asked = []
    for _ in range(10):
        q = next_question(answers)
        if q is None:
            break
        asked.append(q["id"])
        # 답을 채워 진행 (첫 옵션 선택)
        answers[q["id"]] = q["options"][0]["value"]
    assert 5 <= len(asked) <= 7, f"문항 상한 5~7: {asked}"
    assert next_question(answers) is None


def test_inexperienced_branch_inserts_time_preference():
    # 경험 문항에 '무경험' 응답 → 시점선호 심리테스트 분기
    answers = {"q_experience": "none"}
    seen = {"q_experience"}
    for _ in range(8):
        q = next_question(answers)
        if q is None:
            break
        seen.add(q["id"])
        answers[q["id"]] = q["options"][0]["value"]
    assert "q_time_pref" in seen, "무경험자는 시점선호 문항을 받아야 함"


def test_build_persona_deterministic():
    answers = {"q_experience": "exp", "q_panic": 1.0, "q_fomo": 0.0, "q_rumor": 1.0}
    a = build_player_persona(answers)
    b = build_player_persona(answers)
    assert isinstance(a, Persona)
    assert a.model_dump() == b.model_dump()


def test_high_panic_answers_raise_default_fear():
    calm = build_player_persona({"q_panic": 0.0, "q_fomo": 0.0})
    panicky = build_player_persona({"q_panic": 1.0, "q_fomo": 0.0})
    assert panicky.default_fear > calm.default_fear


def test_empty_answers_neutral_fallback():
    p = build_player_persona({})
    assert isinstance(p, Persona)
    assert p.default_fear == 50.0 and p.default_greed == 50.0
    assert p.cash_pool and p.portfolio_symbol_pool
