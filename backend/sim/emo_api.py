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

from . import coins as _coins
from . import diagnosis_report as _diagnosis_report
from . import disposition_report, emo_store
from . import llm as _llm
from . import tier as _tier
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
        "band_places": run.band_places(),   # T-50d — 밴드별 장소(장소 딜레마 발동 판정용)
        "last_market": run.last_market,   # T-35 — 마지막 정산일 카테고리별 수익률(%)
        "settlement": run.last_settlement,   # §5.1 — 마지막 choose() 정산 캐스케이드(없으면 None)
        "ticker": run.ticker(),   # §B — 카테고리별 실명 코인 시세 현황판(오늘까지, 미래 누출 없음)
        "tier": _tier.compute_tier(run.emotion, run.special_event_count),   # §C2 — 통제 티어(파생, 저장 안 함)

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
    days: int = 10   # T-48f — 편향 표본 견고화(panic/loss n=3 턱걸이→6) 시도 후,
                      # v3 §A 제품 결정으로 10일 복귀. 표본 부족은 리포트의
                      # low_sample 표시(disposition_report._LOW_SAMPLE)로 흡수.
                      # 운명선 max 30.
    allocations: dict[str, float] | None = None   # {카테고리: 0~100 비중} — 합 정규화
    name: str | None = None   # T-28 — 클론 이름(미입력 시 백엔드 기본값)


class ChoiceBody(BaseModel):
    choice_id: str
    coin_target: str | None = None   # T-53 (F4) — 매수/매도 대상 코인(카테고리). 유지는 무시.


class DesignateBody(BaseModel):
    npc_id: str


class AvoidBody(BaseModel):
    day_a: int
    day_b: int


class PlanBody(BaseModel):
    plan: dict[str, str]


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
    return {
        **_state(run, game_id),
        # v3 §D1 — 설문 직후 진단 근거 화면(신설). diagnose()가 이미 계산한
        # 값의 노출 + 문항별 기여 분해(점수 역추적)만 신규.
        "diagnosis": _diagnosis_report.build_diagnosis(body.answers),
    }


@router.get("/catalog")
def catalog(seed: int = 0) -> dict:
    """§B — 실명 코인 카탈로그(배분 화면용, 신설·멱등). market_seed.json의
    블라인드 자산 매핑에서 카테고리→{symbol,name,color}만 뽑는다(날짜 없음,
    시기는 계속 블라인드). `seed`는 계약 대칭용 파라미터 — 카탈로그 자체는
    운명선 고정 데이터라 seed에 따라 달라지지 않는다(I2 결정론 자명하게 성립)."""
    return {"coins": _coins.catalog()}


@router.get("/{game_id}/state")
def state(game_id: str) -> dict:
    return _state(_get(game_id), game_id)


@router.get("/{game_id}/board")
def board(game_id: str) -> dict:
    run = _get(game_id)
    if run.is_over:
        raise HTTPException(status_code=409, detail="game is over")
    return run.board()


@router.get("/{game_id}/plan")
def plan(game_id: str) -> dict:
    """§2.2 — 오늘의 일과 편성 미리보기(순수 GET, 멱등, I4)."""
    run = _get(game_id)
    if run.is_over:
        raise HTTPException(status_code=409, detail="game is over")
    return run.plan_preview()


@router.post("/{game_id}/plan")
def plan_submit(game_id: str, body: PlanBody) -> dict:
    """§2.2 — 오늘의 일과 편성 제출. 예산 초과/잘못된 장소=400, 이미 제출·게임
    종료=409."""
    run = _get(game_id)
    try:
        run.submit_plan(body.plan)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    emo_store.save_run(game_id, run)
    return _state(run, game_id)


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


@router.get("/{game_id}/place_dilemma/{place}")
def place_dilemma(game_id: str, place: str) -> dict | None:
    """T-50d — 장소 딜레마(도서관 익절복기·마켓 현실소비 = disp 결정점). 순수 GET."""
    return _get(game_id).place_dilemma(place)


@router.post("/{game_id}/place_dilemma/{place}/choose")
def place_dilemma_choose(game_id: str, place: str, body: ChoiceBody) -> dict:
    run = _get(game_id)
    try:
        run.resolve_place_dilemma(place, body.choice_id)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    emo_store.save_run(game_id, run)
    return _state(run, game_id)


@router.post("/{game_id}/choose")
def choose(game_id: str, body: ChoiceBody) -> dict:
    run = _get(game_id)
    if not run.is_over:
        # §4.2 — 오늘 게시판에 노출된 3개 밖의 선택지 id는 거부(6개 풀 전체가
        # 아니라 오늘의 추첨된 3개만 유효). board()는 순수·멱등이라 여기서 다시
        # 불러도 상태를 바꾸지 않는다.
        exposed_ids = {c["id"] for c in run.board()["scenario"]["choices"]}
        if body.choice_id not in exposed_ids:
            raise HTTPException(
                status_code=400,
                detail=f"choice {body.choice_id!r} not exposed today",
            )
    try:
        run.choose(body.choice_id, body.coin_target)
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
    rep = disposition_report.compute_report(
        run.disposition, run.actual_bias(),
        run.bias_tally, run.choice_history,   # T-48c 표본수 · T-48d 타임라인
    )
    if rep.get("available"):
        # T-49c/v3 §B — 엔딩 후 블라인드 해제(실제 종목·시기). 게임 종료라
        # 관찰오염 없음. v3 설계 전환: 종목명은 플레이 중 이미 공개돼 있었으므로
        # (coins.py 카탈로그), 리빌의 센터피스는 "시기"다 — 게임의 드라마를
        # 이끈 벨웨더 카테고리(meme)의 period로 정적 헤드라인 문구를 만든다.
        reveal = load_fate_line().reveal()
        rep["blind_reveal"] = reveal
        bellwether = next((r for r in reveal if r["category"] == _BELLWETHER), None)
        rep["blind_reveal_headline"] = (
            f"당신의 열흘은 사실 {bellwether['period']}이었다."
            if bellwether and bellwether.get("period") else None
        )
        # T-47f — 서술은 게임당 1회만 생성(LLM 게이트·일일한도·캐시=llm.py, 실패 시
        # 결정론 폴백). 첫 응답을 박제해 재요청에 재생(4d 멱등·과금 상한).
        if run.report_narrative is None:
            run.report_narrative = disposition_report.generate_narrative(
                rep, run.ending(), _llm.default_client()
            )
            emo_store.save_run(game_id, run)
        rep["narrative"] = run.report_narrative
    return rep
