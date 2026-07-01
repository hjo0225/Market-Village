"""T-DB · sim/db.py — MongoDB 영속화 계층.

conftest.py가 기본적으로 MARKET_DISABLE_DB=1로 격리(hermetic) — 이 파일의
"실제 연결" 테스트만 명시적으로 env를 세팅해 로컬 컨테이너(127.0.0.1:27019,
사람 승인 하 이번 세션에 구축)에 진짜로 접속해 검증한다(RETRO 규칙5: 실제
동작을 직접 본다). 컨테이너가 없는 환경에서 이 파일만 스킵되도록 각 테스트가
연결 가능 여부를 스스로 확인한다.
"""

from __future__ import annotations

import os

import pytest

from sim import db as DB


@pytest.fixture(autouse=True)
def _reset_db_state():
    DB.reset_connection_cache()
    yield
    DB.reset_connection_cache()


def test_disabled_by_default_returns_none_and_false():
    # conftest.py의 MARKET_DISABLE_DB=1이 살아있는 기본 상태.
    assert DB.games_collection() is None
    assert DB.save_game("g1", {"day": 1}) is False
    assert DB.load_game("g1") is None


def test_unreachable_uri_fails_gracefully(monkeypatch):
    monkeypatch.delenv("MARKET_DISABLE_DB", raising=False)
    monkeypatch.setenv("MONGO_URI", "mongodb://127.0.0.1:1/")  # 아무도 안 듣는 포트
    assert DB.games_collection() is None
    assert DB.save_game("g1", {"day": 1}) is False
    assert DB.load_game("g1") is None


def _real_uri_or_skip(monkeypatch):
    monkeypatch.delenv("MARKET_DISABLE_DB", raising=False)
    monkeypatch.setenv("MONGO_URI", "mongodb://127.0.0.1:27019")
    monkeypatch.setenv("MONGO_DB", "market_village_test")
    if DB.games_collection() is None:
        pytest.skip("로컬 MongoDB(127.0.0.1:27019) 없음 — 이 세션에서 띄운 전용 컨테이너 필요")


def test_save_and_load_round_trip_against_real_local_mongo(monkeypatch):
    _real_uri_or_skip(monkeypatch)
    doc = {"day": 7, "stats": {"멘탈회복": 55.0}, "finished": False}
    ok = DB.save_game("t-db-1", doc)
    assert ok is True
    loaded = DB.load_game("t-db-1")
    assert loaded is not None
    assert loaded["day"] == 7 and loaded["stats"]["멘탈회복"] == 55.0
    DB.games_collection().delete_one({"_id": "t-db-1"})  # 테스트 정리


def test_save_upserts_on_same_game_id(monkeypatch):
    _real_uri_or_skip(monkeypatch)
    DB.save_game("t-db-2", {"day": 1})
    DB.save_game("t-db-2", {"day": 2})
    loaded = DB.load_game("t-db-2")
    assert loaded["day"] == 2
    DB.games_collection().delete_one({"_id": "t-db-2"})


def test_load_missing_game_returns_none(monkeypatch):
    _real_uri_or_skip(monkeypatch)
    assert DB.load_game("nope-does-not-exist") is None
