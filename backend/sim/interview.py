"""N5 인터뷰 온보딩 — 답변(생활패턴/감정트리거/투자성향) → 거울 클론 Persona.

적응형 문항(이전 답에 따라 분기), 5~7문항 상한(이탈 방지). 변환은 결정론
규칙(같은 답=같은 스펙). 무경험자는 시점선호 심리테스트로 성향을 추정한다.
온보딩 1회 LLM은 선택(여기선 결정론 규칙만으로 충분).
"""

from __future__ import annotations

from .models import AgentType, Persona
from .player_emotion.state import PlayerEmotionState, clamp

# 기본 문항 순서. 첫 문항으로 경험 유무를 물어 분기한다.
_QUESTIONS: dict[str, dict] = {
    "q_experience": {
        "id": "q_experience",
        "text": "투자(코인/주식) 경험이 있나요?",
        "options": [
            {"label": "있다", "value": "exp"},
            {"label": "거의 없다", "value": "none"},
        ],
    },
    "q_time_pref": {
        "id": "q_time_pref",
        "text": "지금 500원 vs 한 달 뒤 1000원, 무엇을 택하나요?",
        "options": [
            {"label": "지금 500원", "value": 1.0},     # 현재선호↑ → 충동성↑
            {"label": "한 달 뒤 1000원", "value": 0.0},
        ],
    },
    "q_panic": {
        "id": "q_panic",
        "text": "급락장에서 당신의 첫 반응은?",
        "options": [
            {"label": "바로 손절", "value": 1.0},
            {"label": "일부 정리", "value": 0.5},
            {"label": "버틴다", "value": 0.0},
        ],
    },
    "q_fomo": {
        "id": "q_fomo",
        "text": "급등장에서 당신은?",
        "options": [
            {"label": "추격매수", "value": 1.0},
            {"label": "조금만", "value": 0.5},
            {"label": "관망", "value": 0.0},
        ],
    },
    "q_rumor": {
        "id": "q_rumor",
        "text": "출처 불명 루머에 얼마나 흔들리나요?",
        "options": [
            {"label": "많이 흔들린다", "value": 1.0},
            {"label": "확인부터 한다", "value": 0.0},
        ],
    },
    "q_check": {
        "id": "q_check",
        "text": "시세창을 얼마나 자주 보나요?",
        "options": [
            {"label": "수시로", "value": 1.0},
            {"label": "가끔", "value": 0.5},
            {"label": "거의 안 봄", "value": 0.0},
        ],
    },
}

# 경험자/무경험자별 문항 진행 순서 (상한 7).
_FLOW_EXP = ["q_experience", "q_panic", "q_fomo", "q_rumor", "q_check"]
_FLOW_NONE = ["q_experience", "q_time_pref", "q_panic", "q_fomo", "q_rumor", "q_check"]


def _flow(answers: dict) -> list[str]:
    return _FLOW_NONE if answers.get("q_experience") == "none" else _FLOW_EXP


def next_question(answers: dict) -> dict | None:
    """다음 문항(아직 안 물은 것). 흐름을 다 채우면 None. 무경험 분기 반영."""
    for qid in _flow(answers):
        if qid not in answers:
            return _QUESTIONS[qid]
    return None


def question_by_id(qid: str) -> dict | None:
    """qid로 문항 정의 조회(옵션 라벨·값 포함). 없으면 None."""
    return _QUESTIONS.get(qid)


def _num(answers: dict, key: str, default: float = 0.0) -> float:
    v = answers.get(key)
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _initial_axis(answer: float) -> float:
    """0~1 답변 → 중립 50 중심 초기 감정치([30,70]). build_player_persona의
    default_fear/greed 산식(50+(x-0.5)*40)과 동일 idiom을 4축에 확장."""
    return round(50.0 + (answer - 0.5) * 40.0, 2)


def build_initial_emotion(answers: dict) -> PlayerEmotionState:
    """답변 → 플레이어 초기 감정 4축(결정론). 빈/누락 답은 중립 0.5→50.

    q_panic→fear, q_fomo→greed, q_rumor→anxiety, q_check→restlessness.
    무경험자는 시점선호(q_time_pref)로 충동성을 fear/greed에 보정
    (build_player_persona와 동일 규칙). player_emotion 게이지(0~100)로 clamp.
    """
    panic = _num(answers, "q_panic", 0.5)
    fomo = _num(answers, "q_fomo", 0.5)
    rumor = _num(answers, "q_rumor", 0.5)
    check = _num(answers, "q_check", 0.5)
    if answers.get("q_experience") == "none":
        tp = _num(answers, "q_time_pref", 0.5)
        panic = (panic + tp) / 2
        fomo = (fomo + tp) / 2

    return clamp(
        PlayerEmotionState(
            fear=_initial_axis(panic),
            greed=_initial_axis(fomo),
            anxiety=_initial_axis(rumor),
            restlessness=_initial_axis(check),
        )
    )


def build_player_persona(answers: dict) -> Persona:
    """답변 → 플레이어 거울 클론 Persona (결정론). 빈 답은 중립 폴백."""
    panic = _num(answers, "q_panic", 0.5)
    fomo = _num(answers, "q_fomo", 0.5)
    rumor = _num(answers, "q_rumor", 0.5)
    check = _num(answers, "q_check", 0.5)
    # 무경험자는 시점선호로 충동성 보정.
    if answers.get("q_experience") == "none":
        tp = _num(answers, "q_time_pref", 0.5)
        panic = (panic + tp) / 2
        fomo = (fomo + tp) / 2

    has_answers = bool(answers)
    # 빈 답이면 정확히 중립(50/50).
    default_fear = 50.0 + (panic - 0.5) * 40.0 if has_answers else 50.0
    default_greed = 50.0 + (fomo - 0.5) * 40.0 if has_answers else 50.0

    # 성향에 따른 타입 추정.
    if panic >= 0.66:
        ptype = AgentType.PANIC_SELLER
    elif fomo >= 0.66:
        ptype = AgentType.FOMO_TRADER
    else:
        ptype = AgentType.VALUE_INVESTOR

    return Persona(
        persona_id="player_clone",
        alias="내 거울 클론",
        type=ptype,
        sprite="characters/Isabella_Rodriguez.png",
        color="#6C8EBF",
        innate="플레이어의 투자 성향을 비추는 거울",
        learned="온보딩 인터뷰로 추정된 성향",
        currently="시장을 막 배우기 시작함",
        lifestyle="플레이어와 같은 하루 리듬",
        daily_req="시세 확인, 커뮤니티 눈팅, 매매 결정",
        cash_pool=[1_000_000.0, 2_000_000.0],
        portfolio_symbol_pool=["BTC", "ETH"],
        default_fear=round(default_fear, 2),
        default_greed=round(default_greed, 2),
        herd_sensitivity=round(0.3 + 0.4 * check, 3),
        rumor_sensitivity=round(rumor, 3),
        fear_threshold=round(80.0 - panic * 30.0, 2) if has_answers else None,
    )
