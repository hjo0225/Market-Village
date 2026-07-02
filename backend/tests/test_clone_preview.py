"""T-231 · 설정 2단계 분리 — 인터뷰 확정 화면용 클론 성향 프리뷰.

인터뷰가 끝나면(확정 전) 답변이 만들 클론의 감정 성향(함정별 취약점)을 보여준다.
build_clone_spec 순수함수 재사용 — 게임 생성·상태 변이 없음(읽기 전용 프리뷰).
"""

from __future__ import annotations

import market_live_server as mls
from sim.clone_spec import build_clone_spec


def test_clone_preview_matches_build_clone_spec():
    answers = {"q_panic": 0.9, "q_fomo": 0.2, "q_rumor": 0.5, "q_check": 0.5}
    r = mls.control_clone_preview(mls.ClonePreviewBody(answers=answers))
    assert r["status"] == "ok"
    spec = build_clone_spec(answers)
    assert r["trap_scores"] == spec.trap_scores
    # 확정 카드 표시용 — 함정 id·이름·점수가 전부 채워진 목록.
    assert len(r["traits"]) == len(spec.trap_scores)
    for t in r["traits"]:
        assert t["id"] in spec.trap_scores
        assert t["name"] and isinstance(t["score"], float)


def test_clone_preview_empty_answers_neutral_fallback():
    r = mls.control_clone_preview(mls.ClonePreviewBody(answers={}))
    assert r["status"] == "ok"
    assert all(0.0 <= t["score"] <= 100.0 for t in r["traits"])


def test_clone_preview_is_pure_no_game_created():
    before = set(mls._GAMES)
    mls.control_clone_preview(mls.ClonePreviewBody(answers={"q_panic": 1.0}))
    assert set(mls._GAMES) == before
