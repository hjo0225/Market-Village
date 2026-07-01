"""T-109 · §14 결과 카드 + 2축 평가 매트릭스.

Day30 종료 시 회차 클론을 한 장의 카드로 박제(우마무스메식). 핵심: 수익률과 감정
수치를 나란히 박아 "돈만 보던 시선을 감정으로" 끌어온다(§14.1). 등급은 수익률이
아니라 **수익률×감정통제 2축**으로 매긴다(§14.2) — 운으로 번 회차가 S급이 되면
기둥4(과정>결과) 붕괴.
"""

from __future__ import annotations

from sim import result_card as RC
from sim.runs import RunStore, RunSummary


# --- 2축 매트릭스 (§14.2) ------------------------------------------------ #
def test_evaluation_matrix_quadrants():
    assert RC.evaluate(return_pct=30.0, emotion_control=70.0) == "고수"
    assert RC.evaluate(return_pct=30.0, emotion_control=20.0) == "벼락부자형"
    assert RC.evaluate(return_pct=-10.0, emotion_control=70.0) == "강철멘탈형"
    assert RC.evaluate(return_pct=-10.0, emotion_control=20.0) == "호구"


def test_evaluation_boundaries_fixed():
    # 경계 고정: 수익 0 이상 = 높음, 감정통제 50 이상 = 좋음
    assert RC.evaluate(0.0, 50.0) == "고수"
    assert RC.evaluate(-0.01, 50.0) == "강철멘탈형"
    assert RC.evaluate(0.0, 49.99) == "벼락부자형"


def test_high_return_bad_control_is_not_top_grade():
    # §14.2 핵심 학습 장치: 수익 높아도 통제 나쁘면 최고 등급 아님
    assert RC.evaluate(50.0, 10.0) != "고수"


def _summary(run_id, ret, stats, grade=""):
    return RunSummary(
        run_id=run_id, return_pct=ret, emotion_overall=stats, grade=grade,
        trap_counts={"F1": {"triggered": 2, "resisted": 1},
                     "M1": {"triggered": 5, "resisted": 2}},
        clone_spec_snapshot={},
    )


def test_result_card_fields():
    s = _summary("r3", 32.0, {"공포내성": 31, "탐욕제어": 22, "FOMO저항": 12, "멘탈회복": 41})
    card = RC.result_card(s)
    assert card["return_pct"] == 32.0
    assert card["emotion_overall"] == s.emotion_overall   # 수익+감정 나란히 §14.1
    assert "F1" in card["trap_record"] and "M1" in card["trap_record"]
    # 평균 감정통제 = (31+22+12+41)/4 = 26.5 < 50 → 통제 나쁨 + 수익 높음 = 벼락부자형
    assert card["grade"] == "벼락부자형"
    assert isinstance(card["evaluation"], str) and card["evaluation"]


def test_strong_mental_low_return():
    # 손해 봤지만 통제 좋음 → 강철멘탈형(과정 승리)
    s = _summary("r4", -8.0, {"공포내성": 70, "탐욕제어": 65, "FOMO저항": 72, "멘탈회복": 60})
    assert RC.result_card(s)["grade"] == "강철멘탈형"


def test_card_collection_chronology():
    st = RunStore()
    grades_in = []
    for i, (ret, ctrl) in enumerate([(40, 20), (10, 55), (35, 80)]):
        st.start_run(f"r{i}")
        stats = {"공포내성": ctrl, "탐욕제어": ctrl, "FOMO저항": ctrl, "멘탈회복": ctrl}
        st.record_summary(_summary(f"r{i}", float(ret), stats))
    cards = RC.card_collection(st)
    assert len(cards) == 3
    # 성장 연대기: 벼락부자형 → ... → 고수 (§14.3)
    assert cards[0]["grade"] == "벼락부자형"
    assert cards[2]["grade"] == "고수"


def test_empty_emotion_safe():
    s = _summary("r0", 5.0, {})
    card = RC.result_card(s)
    assert "grade" in card  # 빈 감정도 크래시 없음
