"""T-200 · step-able GameRun — 신 엔진 정본의 하루씩 플레이 세션(§12.4).

run_loop은 30일을 batch로 돈다. 플레이는 하루씩 advance 해야 하므로 GameRun이
상태(클론·포트폴리오·day)를 들고 하루치 코어(step_day)를 1일씩 굴린다. batch
run_loop과 **동치**(같은 입력=같은 최종 수익률)여야 한다(DRY).
"""

from __future__ import annotations

from sim import run_loop as RL
from sim.game_run import GameRun
from sim import clone_spec as CS
from sim.runs import RunStore
from sim.trap_pipeline import Intervention
from sim.resistance import STRATEGY_B

PANICKY = CS.build_clone_spec({"q_panic": 1.0, "q_fomo": 0.0})


def _stats():
    return {"급락패닉저항": 25.0, "멘탈마모저항": 50.0, "익절거부제어": 50.0,
            "과대베팅제어": 50.0, "추격매수저항": 50.0, "막차불안저항": 50.0,
            "멘탈회복": 50.0}


def _game(**kw):
    base = dict(category="meme", start_price=100.0, start_stats=_stats(),
                start_quantity=1.0, start_cash=0.0, run_id="g")
    base.update(kw)
    return GameRun(PANICKY, **base)


def test_initial_positions_seed_diversified_start():
    # T-215 D1 — 분산 시작: 주력(meme) + 2차 포지션(large_stable)을 day0부터.
    g = _game(initial_positions={"large_stable": {"avg_cost": 100.0, "quantity": 0.3}})
    st = g.state()
    holdings = {h["category"]: h for h in st["portfolio"]["holdings"]}
    assert set(holdings) == {"meme", "large_stable"}
    assert holdings["large_stable"]["quantity"] == 0.3
    assert holdings["large_stable"]["avg_cost"] == 100.0
    # 이미 보유 중인 카테고리는 M1(추격매수) 감시 목록(other_categories)에서 빠져야 함.
    assert "large_stable" not in g.other_categories


def test_initial_positions_included_in_day0_total_asset():
    # 버그 재현: last_snap이 없는 day0의 total_asset 폴백이 2차 포지션을 빠뜨렸었음.
    g = _game(category="large_stable", start_quantity=0.4,
              initial_positions={
                  "mid_alt": {"avg_cost": 100.0, "quantity": 0.3},
                  "meme": {"avg_cost": 100.0, "quantity": 0.2},
                  "stable": {"avg_cost": 100.0, "quantity": 0.1},
              })
    assert g.state()["total_asset"] == 100.0


def test_initial_positions_survive_new_run_reset():
    # NG+에서도 같은 분산 배분으로 리셋(통제 변인 유지, 기둥3).
    g = _game(initial_positions={"large_stable": {"avg_cost": 100.0, "quantity": 0.3}})
    g.advance_day()
    g.new_run()
    holdings = {h["category"]: h for h in g.state()["portfolio"]["holdings"]}
    assert "large_stable" in holdings
    assert holdings["large_stable"]["quantity"] == 0.3


def test_advance_one_day_at_a_time():
    g = _game()
    assert g.state()["day"] == 0 and g.finished is False
    g.advance_day()
    assert g.state()["day"] == 1 and g.finished is False


def test_full_30_days_finishes_with_summary():
    g = _game()
    for _ in range(30):
        g.advance_day()
    st = g.state()
    assert st["day"] == 30 and st["finished"] is True
    assert g.store.get_snapshot("g", 29) is not None     # 30일 스냅샷
    assert g.summary is not None
    assert g.summary.grade in {"고수", "벼락부자형", "강철멘탈형", "호구"}


def test_state_exposes_day_stats_portfolio():
    g = _game()
    st = g.state()
    assert set(st) >= {"run_id", "day", "days", "finished", "stats", "portfolio", "total_asset"}
    assert set(st["stats"]) == {"급락패닉저항", "멘탈마모저항", "익절거부제어",
                                "과대베팅제어", "추격매수저항", "막차불안저항", "멘탈회복"}
    assert set(st["portfolio"]) >= {"avg_cost", "quantity", "cash", "holdings"}
    # T-214 — 화면 배선용 종목별 분해(주력 1개, 시작 시점 보유수량 1.0).
    holdings = st["portfolio"]["holdings"]
    assert len(holdings) == 1
    h = holdings[0]
    assert h["category"] == "meme"
    assert h["quantity"] == 1.0
    assert h["avg_cost"] == 100.0
    assert h["value"] == 100.0          # day0: 현재가==avg_cost
    assert h["unrealized_pnl"] == 0.0


def test_portfolio_holdings_breakdown_includes_secondary_positions():
    # T-214 — T-210의 2차 포지션(추격매수)이 holdings 분해에도 나오는지.
    stats = _stats()
    stats["추격매수저항"] = 20.0
    g = _game(category="stable", start_stats=stats, start_quantity=0.0,
              start_cash=100.0, other_categories=("meme",))
    for _ in range(27):
        g.advance_day(roll=100.0)
    holdings = g.state()["portfolio"]["holdings"]
    cats = {h["category"] for h in holdings}
    assert "meme" in cats
    meme = next(h for h in holdings if h["category"] == "meme")
    assert meme["quantity"] > 0
    assert meme["value"] > 0            # 실제 급등 구간이라 평가액이 0보다 커야 함
    assert "unrealized_pnl" in meme


def test_equivalent_to_batch_run_loop():
    # 동치(DRY): GameRun 30일 == run_loop.simulate_run 같은 입력(감시 종목도 명시로 맞춤)
    g = _game(other_categories=())
    for _ in range(30):
        g.advance_day()
    batch = RL.simulate_run(RunStore(), "b", PANICKY, category="meme",
                            start_price=100.0, start_stats=_stats(),
                            start_quantity=1.0, start_cash=0.0, other_categories=())
    assert g.summary.return_pct == batch.return_pct


def test_equivalent_to_batch_run_loop_with_default_watch():
    # 기본 감시(전 카테고리)까지도 동치 — 두 경로 기본 정책이 정확히 같음을 보장.
    g = _game()
    for _ in range(30):
        g.advance_day()
    batch = RL.simulate_run(RunStore(), "b2", PANICKY, category="meme",
                            start_price=100.0, start_stats=_stats(),
                            start_quantity=1.0, start_cash=0.0)
    assert g.summary.return_pct == batch.return_pct


def test_advance_day_chases_watched_surge_and_grows_positions():
    # T-210 GameRun 경로 — stable 보유 + meme 감시. meme day26 실 업비트 DOGE +104.8%
    # (day23~26 연속 급등 — 2021년 실제 펌프 구간).
    stats = _stats()
    stats["추격매수저항"] = 20.0
    g = _game(category="stable", start_stats=stats, start_quantity=0.0,
              start_cash=100.0, other_categories=("meme",))
    for d in range(27):
        snap = g.advance_day(roll=100.0)
    assert snap.trap == "M1" and snap.fund_flow == "to_hotter"
    assert "meme" in g.holding.get("positions", {})
    assert g.state()["portfolio"]["positions"]["meme"]["quantity"] > 0


def test_advance_day_high_crowd_mood_triggers_m2_chase():
    # T-210b — crowd_mood(§9.2.3 FGI 단톡방)가 fgi/crowd_buying 프록시로 M2를 켠다.
    stats = _stats()
    stats["막차불안저항"] = 20.0
    g = _game(category="stable", start_stats=stats, start_quantity=0.0,
              start_cash=100.0, other_categories=())
    g.crowd_mood = 80.0   # M2_FGI=75 초과 → crowd_buying도 자동 True
    snap = g.advance_day(roll=100.0)   # day0(stable) — 다른 트리거 없음
    assert snap.trap == "M2" and snap.fund_flow == "to_hotter"


def test_intervention_on_crash_day_changes_outcome():
    # day27 급락(실 업비트 DOGE −21.6%)에 개입(B+래포100, roll0)하면 안 휘둘림 → 더 나은 수익률
    no_help = _game(run_id="g1")
    for _ in range(30):
        no_help.advance_day()
    saved = _game(run_id="g2")
    for d in range(30):
        if d == 27:
            saved.advance_day(intervention=Intervention(STRATEGY_B, 100.0), roll=0.0)
        else:
            saved.advance_day()
    assert saved.store.get_snapshot("g2", 27).swayed is False
    assert no_help.store.get_snapshot("g1", 27).swayed is True
    assert saved.summary.return_pct > no_help.summary.return_pct


def test_new_run_resets_and_accumulates():
    g = _game(run_id="run1")
    for _ in range(30):
        g.advance_day()
    g.new_run(run_id="run2")
    assert g.state()["day"] == 0 and g.finished is False
    assert g.state()["portfolio"]["quantity"] == 1.0   # 포트폴리오 리셋
    for _ in range(30):
        g.advance_day()
    # 요약은 누적(성장 연대기 §14.3)
    assert len(g.store.summaries()) == 2
