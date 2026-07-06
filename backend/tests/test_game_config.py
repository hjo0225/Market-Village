# -*- coding: utf-8 -*-
"""T-302·T-303 — 시뮬레이션 10일 + 에이전트 이름 설정.

T-302: 서비스 계층(start)이 GAME_DAYS=10을 넘긴다 — 엔진 기본값(30)은 기존
테스트·run_loop 동치성을 위해 불변.
T-303: clone_name이 state·리더보드·매매·맵 이름표로 흐른다(미지정=기존 문구).
"""

from __future__ import annotations

import market_live_server as mls


def _start(gid, **kw):
    return mls.control_game_start(mls.GameStartBody(
        game_id=gid, answers={}, symbol="DOGE", start_price=100.0, **kw))


def test_new_game_is_10_days():
    r = _start("cfg_days")
    assert r["state"]["days"] == 10
    assert mls.GAME_DAYS == 10


def test_clone_name_flows_to_state_and_leaderboard():
    r = _start("cfg_name", clone_name="불사조")
    assert r["state"]["clone_name"] == "불사조"
    lb = mls.control_game_leaderboard(game_id="cfg_name")
    clone_row = next(e for e in lb["board"] if e["id"] == "clone")
    assert clone_row["name"] == "불사조"


def test_clone_name_defaults_when_missing():
    r = _start("cfg_noname")
    assert r["state"]["clone_name"] == "내 클론"
    lb = mls.control_game_leaderboard(game_id="cfg_noname")
    assert next(e for e in lb["board"] if e["id"] == "clone")["name"] == "내 클론"


def test_clone_name_survives_serialization():
    _start("cfg_ser", clone_name="불사조")
    g = mls._get_game("cfg_ser")
    from sim.game_run import GameRun
    g2 = GameRun.from_doc(g.to_doc(), fate_line=g.fl)
    assert g2.clone_name == "불사조"
    assert g2.days == 10
