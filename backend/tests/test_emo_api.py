"""T-7(프론트 브릿지): 신 게임 API 라우터 — EmoGameRun을 HTTP로 노출.

진단→시작→매일(게시판·동행·체인·선택)→엔딩 전체 흐름을 TestClient로 구동한다.
기존 market_live_server 라우터는 건드리지 않는 신규 APIRouter.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sim import emo_store
from sim.emo_api import _build_market, router
from sim.ending import decide_ending


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
    choice = board["scenario"]["choices"][0]["id"]   # 매도(방어) — coin_target 필요
    r = c.post(f"/emo/{gid}/choose", json={"choice_id": choice, "coin_target": "meme"})
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
        c.post(f"/emo/{gid}/choose",
               json={"choice_id": board["scenario"]["choices"][0]["id"], "coin_target": "meme"})
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


# --- 3일 압축 모드: 급등(유혹)→급락(시련)→반등(검증) 교육 아크 --------------- #
def test_compact_3day_market_window_is_surge_crash_surge():
    # emo_api._MARKET_OFFSET_COMPACT(16)의 검증된 결과 — meme 수익률
    # +6.4% / -11.4% / +5.2%. 급락날 패닉셀하면 반등을 놓치는 걸 정산이 보여준다.
    events, cat_returns = _build_market(seed=0, days=3)
    assert events == ["market_surge", "market_crash", "market_surge"], events
    assert all(len(v) == 3 for v in cat_returns.values())


def test_start_3days_reports_total_days_3():
    c = _client()
    body = c.post("/emo/start", json={"answers": ANSWERS, "seed": 42, "days": 3}).json()
    assert body["total_days"] == 3


def test_full_3day_playthrough_epilogue_has_no_hardcoded_yeoltteul():
    c = _client()
    gid = c.post("/emo/start", json={"answers": ANSWERS, "seed": 42, "days": 3}).json()["game_id"]
    for _ in range(3):
        # §2.2 — 오늘 플랜이 아직 없으면 유효한 plan을 제출(기존 test_plan_api.py
        # 패턴 재사용). 이미 잠겼거나(409) 게임이 끝났으면 건너뛴다.
        c.post(f"/emo/{gid}/plan",
               json={"plan": {"오전": "카페", "오후": "운동", "저녁": "집"}})
        # 미해결 체인이 있으면 먼저 해결(test_full_playthrough_to_ending 패턴).
        ch = c.get(f"/emo/{gid}/chain").json()
        if ch:
            c.post(f"/emo/{gid}/chain/choose", json={"choice_id": ch["choices"][0]["id"]})
        board = c.get(f"/emo/{gid}/board").json()
        c.post(f"/emo/{gid}/choose",
               json={"choice_id": board["scenario"]["choices"][0]["id"], "coin_target": "meme"})
    state = c.get(f"/emo/{gid}/state").json()
    assert state["is_over"]
    assert state["ending"] is not None
    ending = c.get(f"/emo/{gid}/ending").json()
    assert ending["id"] in ("E1", "E2", "E3", "E4", "E5")
    assert len(ending["epilogue"]) == 3
    assert all("열흘" not in line for line in ending["epilogue"])


# --- decide_ending 단위: 3일 압축 모드 E5 기준(SPECIAL_EVENT_ENDING_N_COMPACT) - #
def test_decide_ending_compact_e5_unreachable_in_3days():
    # 압축 모드 특수이벤트 최대 누적은 3(하루 1건) — 기준(4) 미달이라 E5 불가.
    # 체인 확률 0.95 상태에서 기준이 3 이하면 모든 압축 회차가 E5로 수렴해
    # 2×2 엔딩(제품 테제)이 가려지므로, 히든 엔딩은 10일 정식판의 보상으로 남긴다.
    ending = decide_ending("중립", "high", special_count=3, total_days=3)
    assert ending["id"] == "E1"
    ending = decide_ending("과열", "low", special_count=3, total_days=3, composure=0.0)
    assert ending["id"] == "E4"


def test_decide_ending_10day_default_needs_higher_special_count():
    # 같은 special_count=3인데 total_days=10(또는 생략)이면 기존 기준(6) 미달 → E5 아님.
    # 기준(6) 충족 시에만 E5.
    ending_10 = decide_ending("중립", "high", special_count=3, total_days=10)
    ending_none = decide_ending("중립", "high", special_count=3)
    assert ending_10["id"] != "E5"
    assert ending_none["id"] != "E5"
    assert decide_ending("중립", "high", special_count=6, total_days=10)["id"] == "E5"
