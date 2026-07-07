"""신 게임 API 라우터 — EmoGameRun(감정 4축 미연시)을 HTTP로 노출.

프론트(/play)가 연결할 계약. 기존 market_live_server 라우터는 건드리지 않는
신규 APIRouter(컷오버 시 구 라우터 대체). market_live_server에 include_router로
마운트한다.

GET은 전부 상태 무변이·멱등(리로드/리마운트 안전, PLAN-READY 4d). 상태 변이는
POST(choose/chain_choose/designate/avoid)로만.
"""

from __future__ import annotations

import random
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import emo_store
from .emo_game import EmoGameRun
from .player_emotion.verdict import compute_verdict
from .scenario import EVENT_CATEGORIES

router = APIRouter(prefix="/emo", tags=["emo"])

_EVENT_POOL = list(EVENT_CATEGORIES)


def _build_market(seed: int, days: int) -> tuple[list[str], list[float]]:
    """결정론 시장 시퀀스(이벤트 카테고리 + 일별 수익률). 회차 재현.

    MVP: 시드 기반 합성. (fate_line OHLC 연동은 후속 — 지금은 오프라인 합성.)
    """
    rng = random.Random(seed)
    events = [rng.choice(_EVENT_POOL) for _ in range(days)]
    returns = [round(rng.uniform(-0.15, 0.15), 4) for _ in range(days)]
    return events, returns


def _emotion_dict(run: EmoGameRun) -> dict:
    e = run.emotion
    return {"fear": e.fear, "greed": e.greed, "anxiety": e.anxiety,
            "restlessness": e.restlessness}


def _state(run: EmoGameRun, game_id: str) -> dict:
    return {
        "game_id": game_id,
        "day": run.day,
        "total_days": len(run.events),
        "is_over": run.is_over,
        "emotion": _emotion_dict(run),
        "verdict": compute_verdict(run.emotion),
        "portfolio_value": run.portfolio_value,
        "companion": run.companion(),
        "special_event_count": run.special_event_count,
        "has_pending_chain": run.pending_chain is not None,
        "ending": run.ending() if run.is_over else None,
    }


def _get(game_id: str) -> EmoGameRun:
    run = emo_store.load_run(game_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"game {game_id!r} not found")
    return run


# --- 요청 모델 -------------------------------------------------------- #
class StartBody(BaseModel):
    answers: dict = {}
    seed: int = 0
    days: int = 10


class ChoiceBody(BaseModel):
    choice_id: str


class DesignateBody(BaseModel):
    npc_id: str


class AvoidBody(BaseModel):
    day_a: int
    day_b: int


# --- 엔드포인트 ------------------------------------------------------- #
@router.post("/start")
def start(body: StartBody) -> dict:
    events, returns = _build_market(body.seed, max(1, body.days))
    run = EmoGameRun.new(body.answers, events, returns, seed=body.seed)
    game_id = uuid.uuid4().hex
    emo_store.save_run(game_id, run)
    return _state(run, game_id)


@router.get("/{game_id}/state")
def state(game_id: str) -> dict:
    return _state(_get(game_id), game_id)


@router.get("/{game_id}/board")
def board(game_id: str) -> dict:
    run = _get(game_id)
    if run.is_over:
        raise HTTPException(status_code=409, detail="game is over")
    return run.board()


@router.get("/{game_id}/chain")
def chain_event(game_id: str) -> dict | None:
    return _get(game_id).chain_event()


@router.post("/{game_id}/chain/choose")
def chain_choose(game_id: str, body: ChoiceBody) -> dict:
    run = _get(game_id)
    try:
        run.chain_choose(body.choice_id)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    emo_store.save_run(game_id, run)
    return _state(run, game_id)


@router.post("/{game_id}/choose")
def choose(game_id: str, body: ChoiceBody) -> dict:
    run = _get(game_id)
    try:
        run.choose(body.choice_id)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    emo_store.save_run(game_id, run)
    return _state(run, game_id)


@router.post("/{game_id}/designate")
def designate(game_id: str, body: DesignateBody) -> dict:
    run = _get(game_id)
    try:
        run.designate(body.npc_id)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    emo_store.save_run(game_id, run)
    return _state(run, game_id)


@router.post("/{game_id}/avoid")
def avoid(game_id: str, body: AvoidBody) -> dict:
    run = _get(game_id)
    run.avoid(body.day_a, body.day_b)
    emo_store.save_run(game_id, run)
    return _state(run, game_id)


@router.get("/{game_id}/ending")
def ending(game_id: str) -> dict:
    run = _get(game_id)
    if not run.is_over:
        raise HTTPException(status_code=409, detail="game not over yet")
    return run.ending()
