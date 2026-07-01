"""프론트엔드 "결과 카드 모음"(회차별 결과카드 갤러리) — /control/game/summaries.

RunStore.summaries()는 기존재(전 회차 RunSummary 목록) — 엔드포인트만 새로 노출한다.
"""

from __future__ import annotations

import market_live_server as mls


def test_summaries_empty_before_any_run_finishes():
    mls.control_game_start(mls.GameStartBody(game_id="sum_a", answers={}, symbol="DOGE"))
    r = mls.control_game_summaries(game_id="sum_a")
    assert r["status"] == "ok"
    assert r["summaries"] == []


def test_summaries_lists_finished_runs():
    mls.control_game_start(mls.GameStartBody(game_id="sum_b", answers={}, symbol="DOGE"))
    for _ in range(30):
        mls.control_game_advance(mls.GameAdvanceBody(game_id="sum_b"))
    r = mls.control_game_summaries(game_id="sum_b")
    assert r["status"] == "ok"
    assert len(r["summaries"]) == 1
    assert r["summaries"][0]["run_id"] == "run1"
    assert "return_pct" in r["summaries"][0] and "grade" in r["summaries"][0]


def test_summaries_missing_game():
    assert mls.control_game_summaries(game_id="nope")["status"] == "error"
