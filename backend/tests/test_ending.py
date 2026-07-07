"""T-13: 엔딩 5종 분기 (문서 §4).

감정(과열/위축/중립 → 2단계)×재산(고/저) 4분기 + 특수이벤트 N회 이상 히든(E5).
verdict 3단계를 감정축 2단계로 접는다: 중립=감정+(통제됨), 과열·위축=감정−.
2×2 등급(고수/벼락부자형/강철멘탈형/호구)은 병기 유지.
"""

from sim.ending import (
    SPECIAL_EVENT_ENDING_N,
    decide_ending,
    emotion_controlled,
    grade_2x2,
)


def test_emotion_controlled_only_neutral():
    assert emotion_controlled("중립") is True
    assert emotion_controlled("과열") is False
    assert emotion_controlled("위축") is False


def test_four_quadrants():
    assert decide_ending("중립", "high", 0)["id"] == "E1"   # 감정+ 재산+
    assert decide_ending("과열", "high", 0)["id"] == "E2"   # 감정- 재산+
    assert decide_ending("중립", "low", 0)["id"] == "E3"    # 감정+ 재산-
    assert decide_ending("위축", "low", 0)["id"] == "E4"    # 감정- 재산-


def test_special_event_hidden_ending_overrides():
    e = decide_ending("과열", "low", SPECIAL_EVENT_ENDING_N)
    assert e["id"] == "E5"
    # 임계 미만이면 일반 분기.
    assert decide_ending("과열", "low", SPECIAL_EVENT_ENDING_N - 1)["id"] == "E4"


def test_ending_has_title_and_three_cut_epilogue():
    for verdict in ("중립", "과열", "위축"):
        for wealth in ("high", "low"):
            e = decide_ending(verdict, wealth, 0)
            assert e["title"].strip()
            assert len(e["epilogue"]) == 3
            assert all(line.strip() for line in e["epilogue"])


def test_grade_2x2_preserved_even_on_e5():
    e = decide_ending("중립", "high", SPECIAL_EVENT_ENDING_N)
    assert e["id"] == "E5"
    assert e["grade"] == grade_2x2("중립", "high")   # 등급 병기 = 2x2로 계산


def test_grade_labels():
    assert grade_2x2("중립", "high") == "고수"
    assert grade_2x2("과열", "high") == "벼락부자형"
    assert grade_2x2("중립", "low") == "강철멘탈형"
    assert grade_2x2("위축", "low") == "호구"
