"""T-DB · 서버 재시작 시나리오 — game_id로 진행 중이던 게임을 재개할 수 있는가.

실제 로컬 MongoDB(사람 승인, 127.0.0.1:27019)를 상대로 검증한다(RETRO 규칙5:
mock이 아니라 실제 동작을 본다). 컨테이너가 없으면 스킵.
"""

from __future__ import annotations

import pytest

import market_live_server as mls
# market_live_server.py는 `backend.sim.db`로 import한다(sys.path에 backend/와
# 루트 둘 다 있어 `sim.db`와 `backend.sim.db`가 서로 다른 모듈 인스턴스가 됨 —
# 캐시가 안 섞이게 반드시 mls가 실제로 쓰는 인스턴스를 참조). RETRO 참고.
DB = mls._db


@pytest.fixture(autouse=True)
def _real_db(monkeypatch):
    monkeypatch.delenv("MARKET_DISABLE_DB", raising=False)
    monkeypatch.setenv("MONGO_URI", "mongodb://127.0.0.1:27019")
    monkeypatch.setenv("MONGO_DB", "market_village_test")
    DB.reset_connection_cache()
    if DB.games_collection() is None:
        pytest.skip("로컬 MongoDB(127.0.0.1:27019) 없음")
    yield
    DB.games_collection().delete_many({"_id": {"$regex": "^persist-test-"}})
    DB.reset_connection_cache()


def _simulate_server_restart():
    """서버 재시작 흉내 — 인메모리 세션 캐시를 비운다(DB는 그대로)."""
    mls._GAMES.clear()


def test_game_resumes_from_db_after_restart():
    gid = "persist-test-1"
    mls.control_game_start(mls.GameStartBody(game_id=gid, answers={}, symbol="DOGE"))
    for _ in range(5):
        mls.control_game_advance(mls.GameAdvanceBody(game_id=gid))
    before = mls.control_game_state(game_id=gid)
    assert before["state"]["day"] == 5

    _simulate_server_restart()
    assert gid not in mls._GAMES   # 인메모리는 진짜로 비었다

    after = mls.control_game_state(game_id=gid)
    assert after["status"] == "ok"
    assert after["state"]["day"] == 5   # DB에서 재구성됨
    assert after["state"] == before["state"]


def test_resumed_game_can_continue_playing():
    gid = "persist-test-2"
    mls.control_game_start(mls.GameStartBody(game_id=gid, answers={}, symbol="DOGE"))
    for _ in range(3):
        mls.control_game_advance(mls.GameAdvanceBody(game_id=gid))
    _simulate_server_restart()

    r = mls.control_game_advance(mls.GameAdvanceBody(game_id=gid))
    assert r["status"] == "ok"
    assert r["state"]["day"] == 4   # 재개 후 하루 더 진행됨


def test_missing_game_id_not_found_even_with_db():
    assert mls.control_game_state(game_id="persist-test-does-not-exist")["status"] == "error"


def test_finished_run_summary_survives_restart():
    gid = "persist-test-3"
    mls.control_game_start(mls.GameStartBody(game_id=gid, answers={}, symbol="DOGE"))
    for _ in range(30):
        mls.control_game_advance(mls.GameAdvanceBody(game_id=gid))
    card_before = mls.control_game_card(game_id=gid)
    assert card_before["status"] == "ok"

    _simulate_server_restart()
    card_after = mls.control_game_card(game_id=gid)
    assert card_after["status"] == "ok"
    assert card_after["card"] == card_before["card"]
