"""T-14: EmoGameRun 영속화 — 인메모리 1차 소스 + Mongo 보조.

db.py 철학 그대로: `_RUNS`(인메모리)가 항상 진실 소스이고, Mongo(db.save_game)는
서버 재시작 후 재개용 보조 저장소. Mongo가 없어도(로컬) 인메모리로 완전 동작한다.
실제 프로덕션 Mongo 쓰기는 하드게이트(env MONGO_URI) — 로컬은 db가 조용히 False.
"""

from __future__ import annotations

from . import db
from .emo_game import EmoGameRun

_RUNS: dict[str, EmoGameRun] = {}


def save_run(game_id: str, run: EmoGameRun) -> None:
    """인메모리에 저장하고 Mongo에 백업(best-effort — 실패해도 예외 없음)."""
    _RUNS[game_id] = run
    db.save_game(game_id, run.to_doc())


def load_run(game_id: str) -> EmoGameRun | None:
    """인메모리 우선, 없으면 Mongo에서 복원(재시작 후 재개). 없으면 None."""
    if game_id in _RUNS:
        return _RUNS[game_id]
    doc = db.load_game(game_id)
    if doc is None:
        return None
    run = EmoGameRun.from_doc(doc)
    _RUNS[game_id] = run
    return run


def _clear() -> None:
    """테스트/재시작 시뮬레이션 전용 — 인메모리 캐시를 비운다."""
    _RUNS.clear()
