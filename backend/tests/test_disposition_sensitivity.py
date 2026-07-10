"""T-61 (1안): 성향별 감정 민감도 배율 — sensitivity_scale 순수함수.

노출 감정 델타를 declared_type별로 증폭/감쇠. 🔒 expected_bias(편향축)를 재사용하지 않고
게임플레이 감정축 전용 별도 테이블 — 리포트 actual_bias와 소스를 분리해 self_awareness가
자기충족으로 허수화되는 순환(T-47/council 확정 불변식)을 원천 차단.
"""
from sim.disposition import DECLARED_TYPES, _EXPOSURE_SENSITIVITY, sensitivity_scale


def test_neutral_type_is_identity():
    assert sensitivity_scale("위험중립형", {"fear": 10, "greed": 6}) == {"fear": 10.0, "greed": 6.0}


def test_stable_amplifies_fear_more_than_aggressive():
    # 안정형은 하락(fear)에 더 크게, 공격형은 덜 흔들린다.
    d = {"fear": 10}
    assert sensitivity_scale("안정형", d)["fear"] > sensitivity_scale("공격투자형", d)["fear"]


def test_aggressive_amplifies_greed_more_than_stable():
    # 공격형은 상승(greed)에 더 크게 반응한다.
    d = {"greed": 10}
    assert sensitivity_scale("공격투자형", d)["greed"] > sensitivity_scale("안정형", d)["greed"]


def test_unknown_type_and_missing_axis_pass_through():
    # 미지 유형 → ×1.0. 테이블에 없는 축(composure) → ×1.0(그대로 통과).
    assert sensitivity_scale("없는유형", {"fear": 5}) == {"fear": 5.0}
    assert sensitivity_scale("안정형", {"composure": 8}) == {"composure": 8.0}


def test_does_not_mutate_input():
    d = {"fear": 10}
    sensitivity_scale("안정형", d)
    assert d == {"fear": 10}


def test_every_declared_type_covers_four_exposure_axes():
    # 5유형 모두 4개 노출축 배율 보유(누락 시 조용히 ×1.0 되는 것 방지).
    for dt in DECLARED_TYPES:
        assert set(_EXPOSURE_SENSITIVITY[dt]) == {"fear", "anxiety", "greed", "restlessness"}, dt


def test_sensitivity_table_uses_emotion_axes_not_bias_axes():
    # 회귀가드: 민감도 축은 감정축(fear/greed...)이지 편향축(loss/fomo/disp...)이 아니다.
    for dt in DECLARED_TYPES:
        keys = set(_EXPOSURE_SENSITIVITY[dt])
        assert keys.isdisjoint({"loss", "fomo", "disp", "over", "panic"}), dt
