"""§5.3 대화형 심층 인터뷰 — LLM은 표현+판단만, 출력 스키마는 고정(§5.3.2 가드레일).

"우리가 18개 문항을 직접 쓰지 않는다"(§5.3) — 하지만 무엇을 캐낼지·어떤 순서로
캐낼지의 **구조**는 `sim.interview`의 결정론 흐름을 그대로 쓴다(가드레일1: 출력
스키마 고정). LLM은 두 자리에만 opt-in으로 얹힌다:
  (1) 질문 **표현** — 같은 qid라도 이전 답변 톤에 맞춰 대화체로 다듬음.
  (2) 답변 **해석** — 플레이어의 자유 텍스트를 기존 옵션 수치 스케일로 판단
      (§5.3.2 가드레일2: 판단 근거는 옵션 라벨 매칭에서 나옴).

키 없이도(오프라인 키워드 매칭) 완전히 플레이 가능해야 한다 — LLM은 실패하면
조용히 오프라인 결과로 폴백한다(§8.6.3처럼 결정에 영향 없음, 여기선 '표현+해석'
자체가 산출물이라 폴백 = 동일 산출물의 결정론 버전).
"""

from __future__ import annotations

from . import interview as IV


def next_question_llm(answers: dict, use_llm: bool = False) -> dict | None:
    """다음 질문 — 구조(qid·순서)는 IV.next_question 그대로, 표현만 opt-in LLM."""
    q = IV.next_question(answers)
    if q is None or not use_llm:
        return q
    text = _llm_rephrase(q, answers)
    if text is None:
        return q
    return {**q, "text": text}


def interpret_answer(qid: str, text: str, use_llm: bool = False) -> object:
    """자유 텍스트 답변 → 기존 옵션 스케일의 값(§5.3.2 출력 스키마 고정).

    오프라인: 텍스트에 옵션 라벨이 부분 문자열로 있으면 그 옵션 값(가장 긴 매칭
    우선). 매치 없으면 중립(수치형은 중앙값, 범주형은 첫 옵션). LLM opt-in이면
    먼저 LLM 판단을 시도하고, 실패하면 오프라인 매칭으로 폴백.
    """
    q = IV.question_by_id(qid)
    if q is None:
        return 0.5

    if use_llm:
        v = _llm_score(qid, text, q)
        if v is not None:
            return v

    return _offline_match(text, q["options"])


def _offline_match(text: str, options: list[dict]) -> object:
    best = None
    best_len = -1
    for opt in options:
        label = opt["label"]
        if label in text and len(label) > best_len:
            best = opt["value"]
            best_len = len(label)
    if best is not None:
        return best
    return _neutral_value(options)


def _neutral_value(options: list[dict]) -> object:
    values = [o["value"] for o in options]
    if all(isinstance(v, (int, float)) for v in values):
        s = sorted(values)
        mid = len(s) // 2
        return s[mid] if len(s) % 2 == 1 else (s[mid - 1] + s[mid]) / 2
    return values[0]


def _llm_rephrase(q: dict, answers: dict) -> str | None:
    """(opt-in) 질문을 이전 답변 톤에 맞춰 대화체로. 실패/키없음은 None."""
    try:
        from .llm import LLMClient
        client = LLMClient()
        prompt = (
            f"투자 성향 인터뷰 문항 하나를 대화체 한국어 한 문장으로 자연스럽게 "
            f"바꿔줘. 원문: \"{q['text']}\". 지금까지 답변 수: {len(answers)}개 "
            f"(많을수록 더 진지한 상담 톤으로, §5.3.3). 문장만 출력, 설명 없이."
        )
        out = client.chat(system="너는 투자 심리 인터뷰어다. 질문 한 문장만 출력한다.",
                          user=prompt)
        out = (out or "").strip()
        return out or None
    except Exception:
        return None


def _llm_score(qid: str, text: str, q: dict) -> object | None:
    """(opt-in) 자유 텍스트를 옵션 스케일로 LLM이 판단. 실패는 None(오프라인 폴백)."""
    try:
        from .llm import LLMClient
        client = LLMClient()
        opts = ", ".join(f"{o['label']}={o['value']}" for o in q["options"])
        prompt = (
            f"질문: \"{q['text']}\"\n답변: \"{text}\"\n"
            f"이 답변을 아래 보기 중 가장 가까운 값으로 판단해 그 값만 출력해: {opts}"
        )
        out = client.chat(system="숫자 또는 값 하나만 출력한다.", user=prompt)
        out = (out or "").strip()
        for opt in q["options"]:
            if str(opt["value"]) == out:
                return opt["value"]
        return float(out)
    except Exception:
        return None
