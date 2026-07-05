"""T-208 · 교류 엔드포인트 — 1:1 권유 + FGI 단톡방.

핸들러 직접 호출(RETRO 규칙5).
"""

from __future__ import annotations

import market_live_server as mls


def _start(gid="soc_ep"):
    return mls.control_game_start(mls.GameStartBody(
        game_id=gid, answers={"q_panic": 1.0}, symbol="DOGE", start_price=100.0))


def test_persuade_endpoint():
    _start("soc_a")
    r = mls.control_game_persuade(mls.GamePersuadeBody(
        game_id="soc_a", npc_id="value_investor", direction="calm", roll=0.0))
    assert r["status"] == "ok" and r["accepted"] is True
    assert r["rapport"] > 50.0


def test_persuade_endpoint_missing_game():
    r = mls.control_game_persuade(mls.GamePersuadeBody(
        game_id="nope", npc_id="value_investor", direction="calm"))
    assert r["status"] == "error"


def test_fgi_endpoint():
    # T-230 — calm은 중립(50) 복원 의미론: 중립에선 무이동, 공포 쪽(40)에선 +방향.
    _start("soc_b")
    r = mls.control_game_fgi(mls.GameFgiBody(game_id="soc_b", tone="calm", roll=0.0))
    assert r["status"] == "ok"
    assert r["crowd_mood"] == 50.0
    mls._get_game("soc_b").crowd_mood = 40.0
    r2 = mls.control_game_fgi(mls.GameFgiBody(game_id="soc_b", tone="calm", roll=0.0))
    assert r2["crowd_mood"] > 40.0


def test_state_exposes_rapport_and_crowd_mood():
    _start("soc_c")
    r = mls.control_game_state(game_id="soc_c")
    assert "rapport" in r["state"] and "crowd_mood" in r["state"]
