"""T-106 · §5.5 클론 스펙 — 6함정 취약점 + 뉴스톤 계수 + 합리화풀 + 고유이벤트.

복제가 캐내는 것: "이 사람이 투자에서 언제·왜·어떻게 무너지는가"(§5.1). 인터뷰
답변 → 결정론으로 6함정 취약점(0~100) + 뉴스톤 반응계수(0.5~1.5) + 함정별 합리화
대사풀 + 고유 이벤트(§5.4). 같은 답=같은 스펙(거울 정확도).
"""

from __future__ import annotations

from sim import clone_spec as CS

TRAP_IDS = {"F1", "F2", "G1", "G2", "M1", "M2"}


def test_trap_scores_shape():
    spec = CS.build_clone_spec({"q_panic": 0.5, "q_fomo": 0.5})
    assert set(spec.trap_scores) == TRAP_IDS
    for v in spec.trap_scores.values():
        assert 0.0 <= v <= 100.0


def test_deterministic():
    ans = {"q_panic": 1.0, "q_fomo": 0.0, "q_rumor": 1.0, "q_check": 0.5}
    assert CS.build_clone_spec(ans) == CS.build_clone_spec(ans)


def test_panic_answer_raises_F1():
    panicky = CS.build_clone_spec({"q_panic": 1.0, "q_fomo": 0.0})
    calm = CS.build_clone_spec({"q_panic": 0.0, "q_fomo": 0.0})
    assert panicky.trap_scores["F1"] > calm.trap_scores["F1"]
    assert panicky.trap_scores["F1"] >= 90.0


def test_fomo_answer_raises_M1():
    chaser = CS.build_clone_spec({"q_panic": 0.0, "q_fomo": 1.0})
    assert chaser.trap_scores["M1"] >= 90.0
    assert chaser.trap_scores["M1"] > chaser.trap_scores["F1"]


def test_news_tone_coefficients_in_range():
    spec = CS.build_clone_spec({"q_panic": 1.0, "q_fomo": 0.0, "q_check": 0.5})
    assert set(spec.news_tone_coef) == {"fear", "optimism", "uncertain"}
    for v in spec.news_tone_coef.values():
        assert 0.5 <= v <= 1.5
    # 패닉형은 공포 톤에 더 민감
    assert spec.news_tone_coef["fear"] > 1.0


def test_rationalization_pool_per_trap():
    spec = CS.build_clone_spec({"q_panic": 1.0, "q_fomo": 1.0})
    for tid in ("F1", "G1", "M1"):
        assert tid in spec.rationalization
        assert len(spec.rationalization[tid]) >= 1
        assert all(isinstance(s, str) and s for s in spec.rationalization[tid])


def test_unique_events_generated_and_deterministic():
    ans = {"q_panic": 1.0, "q_fomo": 1.0, "q_check": 1.0, "q_rumor": 1.0}
    a = CS.build_clone_spec(ans)
    b = CS.build_clone_spec(ans)
    assert len(a.unique_events) >= 1
    assert [e["id"] for e in a.unique_events] == [e["id"] for e in b.unique_events]
    # 고유 이벤트는 트리거·효과를 가진다 (§5.4)
    for e in a.unique_events:
        assert "id" in e and "trigger" in e and "effect" in e


def test_empty_answers_neutral_fallback():
    spec = CS.build_clone_spec({})
    # 빈 답이면 뉴스톤 계수 중립(1.0), 취약점은 범위 안
    assert all(abs(v - 1.0) < 1e-9 for v in spec.news_tone_coef.values())
    assert all(0.0 <= v <= 100.0 for v in spec.trap_scores.values())
    assert len(spec.unique_events) >= 1   # 비어있지 않음(폴백 이벤트)


def test_confirmation_bias_from_rumor():
    suspicious = CS.build_clone_spec({"q_rumor": 1.0})
    skeptic = CS.build_clone_spec({"q_rumor": 0.0})
    assert suspicious.confirmation_bias > skeptic.confirmation_bias
