"""신 게임 API 라우터 — EmoGameRun(감정 4축 미연시)을 HTTP로 노출.

프론트(/play)가 연결할 계약. 기존 market_live_server 라우터는 건드리지 않는
신규 APIRouter(컷오버 시 구 라우터 대체). market_live_server에 include_router로
마운트한다.

GET은 전부 상태 무변이·멱등(리로드/리마운트 안전, PLAN-READY 4d). 상태 변이는
POST(choose/chain_choose/designate/avoid)로만.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import disposition_report, emo_store
from .emo_game import EmoGameRun
from .fate_line import CATEGORIES, load_fate_line
from .player_emotion.verdict import compute_verdict

router = APIRouter(prefix="/emo", tags=["emo"])

# 감정 이벤트를 파생시키는 시장 벨웨더. meme=고변동(급락/급등 드라마의 원천) —
# 커뮤니티 게시판 여론이 패닉/열광하는 신호. large_stable은 저변동이라 전부 '루머'로
# 단조로워져 감정 코어가 죽는다(30일 실데이터 검증: large=급락/급등 0, meme=급락4·급등11).
_BELLWETHER = "meme"

# 드라마 윈도 오프셋(T-21). 실 시드 30일 중 앞부분은 잔잔(급락/급등 0)하고 드라마가
# fate 11~20일에 몰려 있어, 기본 10일 게임을 그 구간으로 당겨온다(급등4·급락2·변동3
# ·루머1 — 공포·탐욕 균형 아크). 블라인드 실데이터를 유지하며 '어느 10일을 사는가'만
# 고정 이동(통제변인 보존). 창이 시드를 넘지 않게 클램프.
_MARKET_OFFSET = 11


def _build_market(seed: int, days: int) -> tuple[list[str], dict[str, list[float]]]:
    """시장 시퀀스 — **실 FateLine(블라인드 과거 업비트 OHLC)**에서 카테고리별
    일별 수익률 + 그와 일관된 감정 이벤트. 운명선은 회차 무관 고정(통제변인).

    이벤트는 벨웨더(meme, 고변동) 수익률에서 파생한다(급락=하락일, 급등=상승일) —
    "급락인데 +수익" 비일관 제거. 완만한 날은 변동폭으로 변동/루머 구분.
    emo day d = fate day d+offset(드라마 구간으로 당김, 창이 시드 넘지 않게 클램프).
    """
    fate = load_fate_line()
    offset = min(_MARKET_OFFSET, max(1, fate.days - days))
    cat_returns: dict[str, list[float]] = {
        cat: [fate.change_rate(cat, d + offset) / 100.0 for d in range(days)]
        for cat in CATEGORIES
    }
    events: list[str] = []
    for r in cat_returns[_BELLWETHER]:
        if r <= -0.05:
            events.append("market_crash")
        elif r >= 0.05:
            events.append("market_surge")
        else:
            events.append("market_volatile" if abs(r) >= 0.02 else "rumor_spread")
    return events, cat_returns


def _emotion_dict(run: EmoGameRun) -> dict:
    e = run.emotion
    return {"fear": e.fear, "greed": e.greed, "anxiety": e.anxiety,
            "restlessness": e.restlessness, "composure": e.composure}


def _state(run: EmoGameRun, game_id: str) -> dict:
    return {
        "game_id": game_id,
        "day": run.day,
        "total_days": len(run.events),
        "clone_name": run.clone_name,   # T-28 — 게임 내내 표시할 클론 이름
        "is_over": run.is_over,
        "emotion": _emotion_dict(run),
        "verdict": compute_verdict(run.emotion),
        "portfolio_value": run.portfolio_value,
        "holdings": run.holdings,   # {카테고리: 보유액} — 포트폴리오 배분 패널(T-11)
        "companion": run.companion(),
        "special_event_count": run.special_event_count,
        "has_pending_chain": run.pending_chain is not None,
        "has_cashout_dilemma": run.cashout_available(),   # T-30c
        "last_market": run.last_market,   # T-35 — 마지막 정산일 카테고리별 수익률(%)

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
    allocations: dict[str, float] | None = None   # {카테고리: 0~100 비중} — 합 정규화
    name: str | None = None   # T-28 — 클론 이름(미입력 시 백엔드 기본값)


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
    events, cat_returns = _build_market(body.seed, max(1, body.days))
    run = EmoGameRun.new(
        body.answers, events, cat_returns, seed=body.seed,
        allocation=body.allocations, name=body.name,
    )
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


@router.get("/{game_id}/dilemma")
def dilemma(game_id: str) -> dict | None:
    """T-30c — 캐시아웃 딜레마(발동 조건 충족 시). 순수 GET."""
    return _get(game_id).cashout_event()


@router.post("/{game_id}/dilemma/choose")
def dilemma_choose(game_id: str, body: ChoiceBody) -> dict:
    run = _get(game_id)
    try:
        run.cashout(body.choice_id)
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


@router.get("/{game_id}/report")
def report(game_id: str) -> dict:
    """T-47d — 진단 리포트(1층 선언 vs 2층 실제 편향). 엔딩 후에만 공개
    (플레이 중 숨김 = 관찰 오염 방지). 순수 GET·멱등."""
    run = _get(game_id)
    if not run.is_over:
        raise HTTPException(status_code=409, detail="game not over yet")
    return disposition_report.compute_report(run.disposition, run.actual_bias())
