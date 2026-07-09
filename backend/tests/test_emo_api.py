"""T-7(프론트 브릿지): 신 게임 API 라우터 — EmoGameRun을 HTTP로 노출.

진단→시작→매일(게시판·동행·체인·선택)→엔딩 전체 흐름을 TestClient로 구동한다.
기존 market_live_server 라우터는 건드리지 않는 신규 APIRouter.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sim import emo_store
from sim.emo_api import _build_market, router


def _client():
    emo_store._clear()
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


ANSWERS = {"q_panic": 0.5, "q_fomo": 0.5, "q_rumor": 0.5, "q_check": 0.5}


def test_start_returns_game_id_and_initial_state():
    c = _client()
    r = c.post("/emo/start", json={"answers": ANSWERS, "seed": 42, "days": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["game_id"]
    assert body["day"] == 0
    assert not body["is_over"]
    assert set(body["emotion"]) == {"fear", "greed", "anxiety", "restlessness", "composure"}


# --- v3 §A: days 기본값 20 → 10 ------------------------------------------- #
def test_start_default_days_is_10_when_omitted():
    c = _client()
    r = c.post("/emo/start", json={"answers": ANSWERS, "seed": 42})
    assert r.status_code == 200
    body = r.json()
    assert body["total_days"] == 10


def test_board_and_choose_advances():
    c = _client()
    gid = c.post("/emo/start", json={"answers": ANSWERS, "seed": 42, "days": 3}).json()["game_id"]
    board = c.get(f"/emo/{gid}/board").json()
    assert board["scenario"]["choices"]
    choice = board["scenario"]["choices"][0]["id"]
    r = c.post(f"/emo/{gid}/choose", json={"choice_id": choice})
    assert r.status_code == 200
    assert r.json()["day"] == 1


def test_board_get_is_idempotent():
    c = _client()
    gid = c.post("/emo/start", json={"answers": ANSWERS, "seed": 42, "days": 3}).json()["game_id"]
    b1 = c.get(f"/emo/{gid}/board").json()
    st1 = c.get(f"/emo/{gid}/state").json()["emotion"]
    b2 = c.get(f"/emo/{gid}/board").json()
    st2 = c.get(f"/emo/{gid}/state").json()["emotion"]
    assert b1 == b2 and st1 == st2   # GET이 상태를 변이하지 않음(4d)


def test_designate_and_companion_in_state():
    c = _client()
    gid = c.post("/emo/start", json={"answers": ANSWERS, "seed": 42, "days": 3}).json()["game_id"]
    st = c.get(f"/emo/{gid}/state").json()
    assert "companion" in st


def test_full_playthrough_to_ending():
    c = _client()
    gid = c.post("/emo/start", json={"answers": ANSWERS, "seed": 42, "days": 3}).json()["game_id"]
    for _ in range(3):
        # 미해결 체인이 있으면 먼저 해결.
        ch = c.get(f"/emo/{gid}/chain").json()
        if ch:
            c.post(f"/emo/{gid}/chain/choose", json={"choice_id": ch["choices"][0]["id"]})
        board = c.get(f"/emo/{gid}/board").json()
        c.post(f"/emo/{gid}/choose", json={"choice_id": board["scenario"]["choices"][0]["id"]})
    state = c.get(f"/emo/{gid}/state").json()
    assert state["is_over"]
    ending = c.get(f"/emo/{gid}/ending").json()
    assert ending["id"] in ("E1", "E2", "E3", "E4", "E5")
    assert len(ending["epilogue"]) == 3


def test_unknown_game_404():
    c = _client()
    assert c.get("/emo/nope/state").status_code == 404


def test_default_market_window_has_drama():
    # T-21: 기본 10일 게임에 급락·급등이 최소 1회씩 — 감정 코어(공포/FOMO) 자극 보장.
    # 실 FateLine 시드 앞 10일이 잔잔해 드라마 구간(offset)으로 당겨온다.
    events, cat_returns = _build_market(seed=0, days=10)
    assert "market_crash" in events, events
    assert "market_surge" in events, events
    assert all(len(v) == 10 for v in cat_returns.values())


# --- T-28: 클론 이름 노출 -------------------------------------------------- #
def test_start_exposes_clone_name():
    c = _client()
    r = c.post("/emo/start", json={"answers": ANSWERS, "seed": 42, "days": 3, "name": "철수"})
    assert r.status_code == 200
    body = r.json()
    assert body["clone_name"] == "철수"
    # state GET도 같은 이름을 준다(멱등).
    gid = body["game_id"]
    assert c.get(f"/emo/{gid}/state").json()["clone_name"] == "철수"


def test_start_clone_name_defaults_when_omitted():
    c = _client()
    body = c.post("/emo/start", json={"answers": ANSWERS, "seed": 42, "days": 3}).json()
    assert body["clone_name"] == "내 클론"
