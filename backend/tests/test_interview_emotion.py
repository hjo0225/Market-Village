"""T-2: 진단문항 → 초기 감정 4축(fear/greed/anxiety/restlessness) 매핑.

interview 답변을 player_emotion.PlayerEmotionState 초기값으로 변환하는
결정론 함수 build_initial_emotion 을 검증한다. build_player_persona(클론용)
와는 별개의 산출물(플레이어 자기감정 게이지)이다.
"""

from sim.interview import build_initial_emotion
from sim.player_emotion.state import PlayerEmotionState


def test_returns_player_emotion_state():
    st = build_initial_emotion({})
    assert isinstance(st, PlayerEmotionState)


def test_empty_answers_are_neutral_50():
    # 빈 답 = 중립. build_player_persona의 50/50 폴백과 동일 idiom.
    st = build_initial_emotion({})
    assert st.fear == 50
    assert st.greed == 50
    assert st.anxiety == 50
    assert st.restlessness == 50


def test_deterministic():
    answers = {"q_panic": 1.0, "q_fomo": 0.0, "q_rumor": 1.0, "q_check": 0.5}
    assert build_initial_emotion(answers) == build_initial_emotion(answers)


def test_each_question_maps_to_its_axis():
    # 각 문항이 자기 축을 끌어올린다(다른 축은 중립).
    hi_fear = build_initial_emotion({"q_panic": 1.0})
    assert hi_fear.fear > 50 and hi_fear.greed == 50

    hi_greed = build_initial_emotion({"q_fomo": 1.0})
    assert hi_greed.greed > 50 and hi_greed.fear == 50

    hi_anx = build_initial_emotion({"q_rumor": 1.0})
    assert hi_anx.anxiety > 50 and hi_anx.fear == 50

    hi_rest = build_initial_emotion({"q_check": 1.0})
    assert hi_rest.restlessness > 50 and hi_rest.fear == 50


def test_low_answer_lowers_axis():
    st = build_initial_emotion({"q_panic": 0.0, "q_fomo": 0.0, "q_rumor": 0.0, "q_check": 0.0})
    assert st.fear < 50 and st.greed < 50 and st.anxiety < 50 and st.restlessness < 50


def test_values_within_range():
    st = build_initial_emotion({"q_panic": 1.0, "q_fomo": 1.0, "q_rumor": 1.0, "q_check": 1.0})
    for v in (st.fear, st.greed, st.anxiety, st.restlessness):
        assert 0 <= v <= 100


def test_inexperienced_time_pref_blends_into_fear_greed():
    # 무경험자는 시점선호(충동성)가 panic/fomo에 섞인다(build_player_persona와 동일 규칙).
    base = build_initial_emotion({"q_experience": "none", "q_panic": 0.0, "q_fomo": 0.0})
    impulsive = build_initial_emotion(
        {"q_experience": "none", "q_panic": 0.0, "q_fomo": 0.0, "q_time_pref": 1.0}
    )
    assert impulsive.fear > base.fear
    assert impulsive.greed > base.greed
