"""T-230 · crowd_mood 방향축 의미론 마감 — fgi_post 수동 경로 + LLM 부호 가드.

🤖 council(2026-07-05) 실측: 자동(게시판) 경로는 T-250이 이미 방향화(0=극공포↔
100=극탐욕, 감쇠 0.20, 평형 74<M2 75). 잔존 문제는 ①fgi_post의 fear_join이
+(탐욕 방향)로 남아 "공포 동참이 M2(막차불안)를 역점화" ②calm이 공포 구간(40)에서
더 공포(38)로 밀림 ③LLM crowd_delta 부호 미대조 ④공포 극단 흡수 비대칭 — 전부 여기서 봉인.
"""

from __future__ import annotations

from sim import board_v2
from sim import clone_spec as CS
from sim import social as S
from sim.game_run import GameRun

CLONE = CS.build_clone_spec({"q_panic": 0.5})


def test_fear_join_moves_crowd_toward_fear():
    out = S.fgi_post(tone="fear_join", crowd_mood=60.0, clone_stat_value=50.0, roll=0.0)
    assert out["crowd_mood"] < 60.0                     # 공포 동참 = 공포 방향(−)
    assert out["clone_delta_applied"] < 0               # 클론 내성도 깎임(톤 기준)


def test_calm_restores_toward_neutral_from_fear_side():
    out = S.fgi_post(tone="calm", crowd_mood=40.0, clone_stat_value=50.0, roll=0.0)
    assert out["crowd_mood"] > 40.0                     # 진정 = 중립 복원(공포 완화)
    assert out["clone_delta_applied"] > 0


def test_absorb_is_symmetric_at_both_extremes():
    hi = S.fgi_post(tone="calm", crowd_mood=95.0, clone_stat_value=50.0, roll=0.0)
    lo = S.fgi_post(tone="calm", crowd_mood=8.0, clone_stat_value=50.0, roll=0.0)
    assert hi["absorbed"] is True and lo["absorbed"] is True
    assert lo["crowd_mood"] == 8.0                      # 공포 극단도 묻힘(대칭)


def test_fear_join_cannot_reignite_m2_at_equilibrium():
    # 밸런스 렌즈의 핵심 시나리오 — 탐욕 이벤트 연속일 평형(74) 부근에서
    # 공포 글 1번이 M2 임계(75)를 점화하던 역전 경로가 소멸했는지.
    g = GameRun(CLONE, category="meme", start_price=100.0, run_id="m2guard")
    g.crowd_mood = 74.0
    g.fgi_post(tone="fear_join", roll=0.0)
    assert g.crowd_mood < 75.0                          # 구코드: 76 → M2 점화 가능


def test_validate_sign_guard_by_context():
    conv = {"threads": [
        {"author_id": "doomposter", "stance": "down", "text": "폭락이다",
         "comments": []},
        {"author_id": "newbie", "stance": "down", "text": "무서워요", "comments": []},
    ], "crowd_delta": 6.0}
    out = board_v2.validate(conv, context="fear")
    assert out is not None
    assert out["crowd_delta"] <= 0.0                    # 공포 게시판에 +6 → 0으로
    out2 = board_v2.validate({**conv, "crowd_delta": -6.0}, context="fomo")
    assert out2["crowd_delta"] >= 0.0                   # 탐욕 게시판에 −6 → 0으로
    out3 = board_v2.validate({**conv, "crowd_delta": 6.0})   # context 없음=기존 동작
    assert out3["crowd_delta"] == 6.0


def test_m2_never_fires_in_pure_fear_run():
    # RETRO 규칙 — 파생 지표는 소비 지점 실발생률로 검증: 공포 뉴스만 30일 흘려도
    # M2(막차불안=탐욕+군중매수)는 crowd 경로로 발동하지 않아야 한다.
    g = GameRun(CLONE, category="meme", start_price=100.0, run_id="fear30")
    fear_news = {"id": "f", "tone": "fear", "headline": "공포 헤드라인"}
    m2_days = 0
    for _ in range(30):
        g.fgi_post(tone="fear_join", roll=0.0)          # 매일 공포 동참까지 얹고
        snap = g.advance_day(news=fear_news)
        if snap is None:
            break
        if snap.trap == "M2" or any(b.get("trap") == "M2" for b in snap.bundle):
            m2_days += 1
    assert m2_days == 0
