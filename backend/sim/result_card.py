"""§14 엔딩 — 회차 결과 카드 (우마무스메식 박제).

Day30 종료 시 그 회차 클론을 한 장의 카드로 박제한다. 수익률과 감정 4스탯을
**나란히** 박는 게 핵심(§14.1) — "+32%인데 FOMO저항 12네?"로 돈만 보던 시선을
감정으로 끌어온다.

등급은 수익률이 아니라 수익률×감정통제 2축으로 매긴다(§14.2). 수익만으로 등급을
매기면 운으로 번 회차가 S급이 되어 기둥4(과정>결과)가 붕괴한다.
"""

from __future__ import annotations

from .runs import RunStore, RunSummary

# 경계(고정) — §14.2. 수치는 튜닝 출발점.
RETURN_HIGH = 0.0       # 수익률 ≥ 0 = 높음
CONTROL_GOOD = 50.0     # 감정통제 ≥ 50 = 좋음

_EVALUATION_TEXT = {
    "고수": "실력 — 과정과 결과 모두 좋다.",
    "벼락부자형": "운빨 — 돈은 벌었지만 감정에 휘둘렸다. 다음엔 과정을 보라.",
    "강철멘탈형": "과정 승리 — 좋은 판단, 나쁜 운.",
    "호구": "개선 필요 — 결과도 과정도 흔들렸다.",
}


def evaluate(return_pct: float, emotion_control: float) -> str:
    """§14.2 2×2 매트릭스 → 등급. 등급 기준은 수익이 아니라 감정통제."""
    high_return = return_pct >= RETURN_HIGH
    good_control = emotion_control >= CONTROL_GOOD
    if high_return and good_control:
        return "고수"
    if high_return and not good_control:
        return "벼락부자형"
    if not high_return and good_control:
        return "강철멘탈형"
    return "호구"


def _emotion_control(emotion_overall: dict) -> float:
    """4스탯 평균 = 감정통제 종합(빈 값은 중립 50)."""
    if not emotion_overall:
        return 50.0
    vals = list(emotion_overall.values())
    return sum(vals) / len(vals)


def result_card(summary: RunSummary) -> dict:
    """회차 요약 → 카드(수익률 + 감정오버롤 + 함정기록 + 등급 + 평가)."""
    control = _emotion_control(summary.emotion_overall)
    grade = evaluate(summary.return_pct, control)
    return {
        "run_id": summary.run_id,
        "return_pct": summary.return_pct,
        "emotion_overall": summary.emotion_overall,
        "emotion_control": round(control, 2),
        "trap_record": summary.trap_counts,
        "grade": grade,
        "evaluation": _EVALUATION_TEXT.get(grade, ""),
    }


def card_collection(store: RunStore) -> list[dict]:
    """누적 카드 = 성장 연대기(§14.3). 등록 순서대로."""
    return [result_card(s) for s in store.summaries()]
