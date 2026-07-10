"""v3 §B/§E — coins.py + GET /emo/catalog + _state()의 ticker.

카탈로그·티커 페이로드에 날짜가 전혀 없음(시기 블라인드 유지) / ticker
결정론(같은 seed+day → 같은 값) / 미래 누출 없음(정산 전 날짜는 index=100·
day_pct=0, 정산된 날짜만 반영) / catalog 멱등.
"""

from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sim import coins as C
from sim import emo_store
from sim.emo_api import router
from sim.emo_game import EmoGameRun
from sim.fate_line import CATEGORIES

ANSWERS = {"Q1": 2, "Q2": 2, "Q3": 2, "Q4": 2, "Q5": 2, "Q6": 2, "Q7": 2}


def _client():
    emo_store._clear()
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _cat(returns):
    return {c: list(returns) for c in CATEGORIES}


# --- coins.py 순수 함수 ----------------------------------------------------- #
def test_category_coin_map_has_all_categories_symbol_name_color():
    m = C.category_coin_map()
    assert set(m) == set(CATEGORIES)
    for cat in CATEGORIES:
        entry = m[cat]
        assert entry["category"] == cat
        assert entry["symbol"]
        assert entry["name"]
        assert entry["color"].startswith("#")


def test_category_coin_map_meme_is_doge():
    # market_seed.json의 meme _meta_origin이 DOGE로 고정(fate_line.reveal과 동일 소스).
    m = C.category_coin_map()
    assert m["meme"]["symbol"] == "DOGE"
    assert m["meme"]["name"] == "도지코인"


def test_catalog_no_dates_anywhere():
    payload = C.catalog()
    dumped = json.dumps(payload, ensure_ascii=False)
    # 날짜 절대 금지(엔딩 전까지 시기 블라인드) — 연도(2020년대) 패턴 부재 확인.
    for year in range(2015, 2027):
        assert str(year) not in dumped
    for entry in payload:
        assert set(entry) == {"category", "symbol", "name", "color"}


def test_coin_for_category_unknown_falls_back():
    entry = C.coin_for_category("does_not_exist")
    assert entry["category"] == "does_not_exist"
    assert entry["symbol"] == ""


# --- GET /emo/catalog -------------------------------------------------------- #
def test_catalog_endpoint_returns_coins_list():
    c = _client()
    body = c.get("/emo/catalog?seed=7").json()
    assert set(body) == {"coins"}
    assert {co["category"] for co in body["coins"]} == set(CATEGORIES)


def test_catalog_endpoint_idempotent_across_seeds():
    # 카탈로그는 market_seed.json 고정 데이터 파생 — seed와 무관(결정론 자명).
    c = _client()
    a = c.get("/emo/catalog?seed=1").json()
    b = c.get("/emo/catalog?seed=999").json()
    assert a == b


def test_catalog_endpoint_no_dates_in_response_body():
    c = _client()
    body = c.get("/emo/catalog?seed=1").json()
    dumped = json.dumps(body, ensure_ascii=False)
    for year in range(2015, 2027):
        assert str(year) not in dumped


# --- ticker (_state()) ------------------------------------------------------ #
def test_ticker_present_in_start_and_state_response():
    c = _client()
    gid = c.post("/emo/start", json={"answers": ANSWERS, "seed": 3, "days": 5}).json()["game_id"]
    body = c.get(f"/emo/{gid}/state").json()
    assert "ticker" in body
    assert {t["category"] for t in body["ticker"]} == set(CATEGORIES)
    for t in body["ticker"]:
        assert set(t) == {"category", "symbol", "name", "day_pct", "index"}


def test_ticker_no_dates_in_payload():
    c = _client()
    gid = c.post("/emo/start", json={"answers": ANSWERS, "seed": 3, "days": 5}).json()["game_id"]
    body = c.get(f"/emo/{gid}/state").json()
    dumped = json.dumps(body["ticker"], ensure_ascii=False)
    for year in range(2015, 2027):
        assert str(year) not in dumped


def test_ticker_day0_before_any_settlement_is_flat_index_100():
    run = EmoGameRun.new(ANSWERS, ["market_crash"] * 5, _cat([-0.1, 0.05, 0.02, 0.01, -0.02]), seed=1)
    for t in run.ticker():
        assert t["index"] == 100.0
        assert t["day_pct"] == 0.0


def test_ticker_reflects_only_settled_days_no_future_leak():
    returns = _cat([0.1, 0.2, 0.3, 0.4, 0.5])   # 카테고리 모두 동일 시리즈(단순화)
    run = EmoGameRun.new(ANSWERS, ["market_crash"] * 5, returns, seed=1)
    run.choose("sell", coin_target="meme")   # day0 정산 → day1 진입
    for t in run.ticker():
        assert abs(t["index"] - 110.0) < 1e-6   # 100 * 1.1 (day0만 반영)
        assert abs(t["day_pct"] - 10.0) < 1e-6
        # day1(0.2)·day2(0.3) 등 미래 수익률은 절대 반영되지 않는다.
        assert t["index"] < 100 * 1.1 * 1.2


def test_ticker_index_is_cumulative_product_matching_cat_returns():
    returns = {
        "large_stable": [0.1, -0.1, 0.05],
        "mid_alt": [0.0, 0.0, 0.0],
        "meme": [0.2, 0.2, 0.2],
        "stable": [0.0, 0.0, 0.0],
    }
    run = EmoGameRun.new(ANSWERS, ["market_crash"] * 3, returns, seed=1)
    run.choose("sell", coin_target="meme")   # day0 정산
    run.choose("sell", coin_target="meme")   # day1 정산
    expected_large = 100 * 1.1 * 0.9
    expected_meme = 100 * 1.2 * 1.2
    by_cat = {t["category"]: t for t in run.ticker()}
    assert abs(by_cat["large_stable"]["index"] - expected_large) < 1e-6
    assert abs(by_cat["meme"]["index"] - expected_meme) < 1e-6


def test_ticker_deterministic_same_seed_same_day():
    returns = _cat([0.05, -0.03, 0.02])
    run_a = EmoGameRun.new(ANSWERS, ["market_crash"] * 3, returns, seed=42)
    run_b = EmoGameRun.new(ANSWERS, ["market_crash"] * 3, returns, seed=42)
    run_a.choose("sell", coin_target="meme")
    run_b.choose("sell", coin_target="meme")
    assert run_a.ticker() == run_b.ticker()


def test_ticker_is_pure_get_does_not_mutate_state():
    c = _client()
    gid = c.post("/emo/start", json={"answers": ANSWERS, "seed": 3, "days": 5}).json()["game_id"]
    before = c.get(f"/emo/{gid}/state").json()
    c.get(f"/emo/{gid}/state")
    after = c.get(f"/emo/{gid}/state").json()
    assert before["ticker"] == after["ticker"]
