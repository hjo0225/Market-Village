"""T-212 · §5.3 대화형 심층 인터뷰 — LLM은 표현+판단만, 출력 스키마는 고정.

기존 interview.py의 구조화된 질문 흐름(qid·상한 5~7)을 뼈대로 두고: (1) 질문
텍스트는 LLM이 대화 흐름에 맞춰 다듬을 수 있음(opt-in, §5.3 "우리가 문항을 직접
쓰지 않는다"), (2) 자유 텍스트 답변은 0~1 수치로 해석되어(§5.3.2 가드레일1: 출력
스키마 고정) 기존 build_clone_spec/build_player_persona와 100% 호환된다.
LLM 없이도(오프라인 키워드 매칭) 완전히 플레이 가능해야 한다(자율 검증 가능).
"""

from __future__ import annotations

from sim import interview_llm as ILLM
from sim import interview as IV
from sim import clone_spec as CS


def test_next_question_offline_matches_base_flow():
    q = ILLM.next_question_llm({}, use_llm=False)
    assert q == IV.next_question({})   # LLM 끄면 기존 구조화 흐름과 동일(회귀 0)


def test_next_question_none_when_flow_exhausted():
    answers = {"q_experience": "exp", "q_panic": 1.0, "q_fomo": 1.0,
              "q_rumor": 1.0, "q_check": 1.0}
    assert ILLM.next_question_llm(answers, use_llm=False) is None


def test_interpret_answer_matches_panic_option_offline():
    # 자유 텍스트가 "바로 손절" 옵션 라벨과 겹치면 그 옵션 수치(1.0)로 해석
    v = ILLM.interpret_answer("q_panic", "그냥 바로 손절하고 나올 것 같아요", use_llm=False)
    assert v == 1.0


def test_interpret_answer_matches_hold_option_offline():
    v = ILLM.interpret_answer("q_panic", "그냥 버틴다 저는", use_llm=False)
    assert v == 0.0


def test_interpret_answer_no_match_falls_back_neutral():
    v = ILLM.interpret_answer("q_panic", "글쎄요 잘 모르겠어요", use_llm=False)
    assert v == 0.5


def test_interpret_answer_unknown_qid_neutral():
    assert ILLM.interpret_answer("q_nonexistent", "아무말", use_llm=False) == 0.5


def test_full_conversation_produces_valid_clone_spec():
    # 자유 텍스트 인터뷰 전체 흐름 → build_clone_spec과 호환되는 answers dict
    answers: dict = {}
    free_texts = {
        "q_experience": "네 투자 좀 해봤어요",
        "q_panic": "패닉 오면 바로 손절해요",
        "q_fomo": "급등장엔 저도 모르게 추격매수 해요",
        "q_rumor": "루머 뜨면 많이 흔들려요",
        "q_check": "하루 종일 시세창 보고 있어요",
    }
    while True:
        q = ILLM.next_question_llm(answers, use_llm=False)
        if q is None:
            break
        qid = q["id"]
        answers[qid] = ILLM.interpret_answer(qid, free_texts.get(qid, ""), use_llm=False)
    spec = CS.build_clone_spec(answers)
    assert spec.trap_scores["F1"] >= 90.0   # 손절+추격 텍스트 → 취약점 반영
    assert spec.trap_scores["M1"] >= 90.0


def test_llm_opt_in_uses_injected_client(monkeypatch):
    # ⚠️ 이 환경 OS에 실 OPENAI_API_KEY가 있어 진짜 LLMClient()는 실제 과금 호출을
    # 낸다. FakeLLM(오프라인 결정론 더블, sim/llm.py 제공)로 monkeypatch해 검증한다.
    import sim.llm as llmmod

    fake = llmmod.FakeLLM(response="급락장이 오면 어떤 마음이 드시나요?")
    monkeypatch.setattr(llmmod, "LLMClient", lambda *a, **kw: fake)
    q = ILLM.next_question_llm({}, use_llm=True)
    assert q is not None and q["text"] == "급락장이 오면 어떤 마음이 드시나요?"
    assert fake.calls  # 실제로 (가짜) 클라이언트가 호출됐다


def test_llm_opt_in_degrades_safely_on_failure(monkeypatch):
    import sim.llm as llmmod

    def _boom(*a, **kw):
        raise llmmod.LLMError("network down")
    monkeypatch.setattr(llmmod, "LLMClient", _boom)
    # LLM 호출이 터져도 예외 없이 오프라인 결과로 폴백
    q = ILLM.next_question_llm({}, use_llm=True)
    assert q == IV.next_question({})
    v = ILLM.interpret_answer("q_panic", "바로 손절", use_llm=True)
    assert v == 1.0  # 오프라인 키워드 매칭 결과로 폴백
