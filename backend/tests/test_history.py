"""T-269 · 진행 이력(발자취) — 뉴스 선택·만남·소셜 액션·일과를 일별로 남기고 조회.

사용자 피드백 ④(좌측 이력 패널)의 데이터 계층. 조사 결과(CHECKLIST 2026-07-05):
companion만 스냅샷에 있고 뉴스 선택·전체 만남·소셜 액션은 휘발이었다 —
전부 기본값 있는 순수 추가라 하위호환 안전.
"""

from __future__ import annotations

import market_live_server as mls
from sim import clone_spec as CS
from sim.game_run import GameRun

CLONE = CS.build_clone_spec({"q_panic": 0.5})
NEWS = {"id": "n1", "tone": "fear", "headline": "테스트 속보"}


def _g(run_id="hist"):
    return GameRun(CLONE, category="meme", start_price=100.0, run_id=run_id)


def test_snapshot_records_news_met_schedule():
    g = _g()
    sched_before = dict(g.schedule)
    snap = g.advance_day(news=NEWS)
    assert snap.news_id == "n1"
    assert snap.news_tone == "fear"
    # 진행 시점(회피 반영)의 일과 — 키는 str(BSON은 int 키 거부: DB-off 테스트가
    # 못 잡는 저장 실패를 여기서 구조적으로 봉인).
    assert snap.schedule == {str(k): v for k, v in sched_before.items()}
    assert all(isinstance(k, str) for k in snap.schedule)
    assert isinstance(snap.met, list)
    if snap.met:                                   # 만남이 있던 날이면 주 교류=첫 만남
        assert snap.companion == snap.met[0]


def test_social_actions_logged_with_day():
    g = _g()
    g.persuade("panic_ant", "calm", roll=0.0)
    g.fgi_post("fear", roll=0.0)
    kinds = [e["kind"] for e in g._social_log]
    assert kinds == ["persuade", "fgi"]
    assert g._social_log[0]["npc_id"] == "panic_ant"
    assert g._social_log[0]["day"] == 0


def test_invalid_persuade_not_logged():
    g = _g()
    g.persuade("nobody", "calm")
    assert g._social_log == []


def test_history_projection_per_day():
    g = _g()
    g.persuade("panic_ant", "calm")
    g.advance_day(news=NEWS)
    g.advance_day()
    h = g.history()
    assert [d["day"] for d in h] == [0, 1]
    assert h[0]["news_tone"] == "fear"
    assert h[1]["news_tone"] == ""                 # 뉴스 안 고른 날
    assert h[0]["social"] and h[0]["social"][0]["kind"] == "persuade"
    assert h[1]["social"] == []
    assert h[0]["schedule"]                        # 일과 8슬롯


def test_social_log_survives_serialization():
    g = _g()
    g.persuade("panic_ant", "calm")
    g2 = GameRun.from_doc(g.to_doc(), fate_line=g.fl)
    assert g2._social_log == g._social_log


def test_history_endpoint():
    mls.control_game_start(mls.GameStartBody(
        game_id="hist_ep", answers={}, symbol="DOGE", start_price=100.0))
    g = mls._get_game("hist_ep")
    g.advance_day(news=NEWS)
    r = mls.control_game_history(game_id="hist_ep")
    assert r["status"] == "ok"
    assert r["days"][0]["news_tone"] == "fear"
    assert mls.control_game_history(game_id="no_such")["status"] == "error"


# --- T-306 · 포트폴리오 한눈 보기 — 종목별 시세·보유가치 --------------------- #
def test_history_trade_carries_per_asset_breakdown():
    g = _g("hist_assets")
    g.advance_day()
    t = g.history()[-1]["trade"]
    assert "assets" in t and "cash" in t
    assert isinstance(t["cash"], float)
    for a in t["assets"]:
        assert a["category"]
        assert isinstance(a["price_pct"], float)
        assert a["value"] > 0            # 보유 수량이 있는 종목만 나열


# --- T-300 · 매매 서사 — 감정 원인→매매→시세→수익률 ------------------------ #
def test_history_carries_trade_narrative_fields():
    g = _g("hist_trade")
    for _ in range(5):
        g.advance_day()
    h = g.history()
    for d in h:
        t = d["trade"]
        # 항상 존재: fund_flow(""=거래 없음), 시세 변화율, 자산 변화율.
        assert set(t) >= {"fund_flow", "price_pct", "ret_pct",
                          "trap_name", "swayed", "realized_pnl"}
        assert isinstance(t["price_pct"], float)
        assert isinstance(t["ret_pct"], float)
    # 휘둘려 매매한 날은 원인(trap_name)이 함께 남는다.
    swayed_days = [d for d in h if d["trade"]["swayed"] and d["trade"]["fund_flow"]]
    for d in swayed_days:
        assert d["trade"]["trap_name"]


def test_advance_day_result_carries_trade_narrative():
    # T-301(사용자 "하루가 끝나면 모달로 떠야") — 정산 응답에 서사가 실려야
    # 프론트가 refresh를 기다리지 않고 모달에 바로 띄운다. history()와 동일 산식.
    mls.control_game_start(mls.GameStartBody(
        game_id="hist_modal", answers={}, symbol="DOGE", start_price=100.0))
    r = mls.control_game_advance(mls.GameAdvanceBody(game_id="hist_modal"))
    dr = r["day_result"]
    assert set(dr["trade"]) >= {"fund_flow", "price_pct", "ret_pct",
                                "trap_name", "swayed", "realized_pnl"}
    assert isinstance(dr["npc_trades"], list)
    g = mls._get_game("hist_modal")
    assert dr["trade"] == g.history()[-1]["trade"]


def test_history_endpoint_carries_npc_trades():
    mls.control_game_start(mls.GameStartBody(
        game_id="hist_npc", answers={}, symbol="DOGE", start_price=100.0))
    g = mls._get_game("hist_npc")
    for _ in range(3):
        g.advance_day()
    r = mls.control_game_history(game_id="hist_npc")
    assert r["status"] == "ok"
    for d in r["days"]:
        assert "npc_trades" in d
        for tr in d["npc_trades"]:
            assert tr["id"] and tr["name"] and tr["action"] in ("buy", "sell")
