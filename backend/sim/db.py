"""§13.8 T-DB — MongoDB 영속화(게임 세션). 로컬 전용, 하드게이트 승인됨(2026-07-01).

연결 실패해도 앱이 안 죽는다 — `_GAMES`(인메모리)가 항상 1차 소스이고, Mongo는
서버 재시작 후 재개용 보조 저장소일 뿐이다. 연결은 지연(lazy) + 짧은
타임아웃(800ms)이라 DB가 없어도 매 요청이 블로킹되지 않는다.
"""

from __future__ import annotations

import os
from pathlib import Path

if not os.getenv("MARKET_DISABLE_DB"):
    try:
        from dotenv import load_dotenv
        _root = Path(__file__).resolve().parents[2]
        load_dotenv(_root / ".env")
        load_dotenv(_root / "backend" / ".env")
    except Exception:
        pass

_client = None
_available: bool | None = None


def _get_client():
    """연결을 1회만 시도하고 결과를 캐싱(매 요청마다 재시도해 지연시키지 않음).

    URI는 매 호출 시 환경변수에서 읽는다(테스트가 동적으로 바꿀 수 있게).
    """
    global _client, _available
    if _available is False:
        return None
    if _client is None:
        uri = "" if os.getenv("MARKET_DISABLE_DB") else os.getenv("MONGO_URI", "")
        if not uri:
            _available = False
            return None
        try:
            from pymongo import MongoClient
            _client = MongoClient(uri, serverSelectionTimeoutMS=800)
            _client.admin.command("ping")
            _available = True
        except Exception:
            _client = None
            _available = False
            return None
    return _client


def reset_connection_cache() -> None:
    """테스트 전용 — 연결 캐시를 지워 다음 호출에서 재시도하게 한다."""
    global _client, _available
    _client = None
    _available = None


def games_collection():
    client = _get_client()
    if client is None:
        return None
    db_name = os.getenv("MONGO_DB", "market_village")
    return client[db_name]["games"]


def save_game(game_id: str, doc: dict) -> bool:
    """저장 성공 여부만 반환 — 실패해도 예외를 올리지 않는다(인메모리가 진실 소스)."""
    col = games_collection()
    if col is None:
        return False
    try:
        col.replace_one({"_id": game_id}, {**doc, "_id": game_id}, upsert=True)
        return True
    except Exception:
        return False


def load_game(game_id: str) -> dict | None:
    col = games_collection()
    if col is None:
        return None
    try:
        return col.find_one({"_id": game_id})
    except Exception:
        return None
