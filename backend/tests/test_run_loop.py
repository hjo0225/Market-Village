"""T-118 · §13 30일 전체 회차 루프 — 거울의 산출물 + D-B 가격 적용 지점.

crisis_day를 30일 threading해 한 회차를 완주한다. 매 라운드 가격은 D-B 하이브리드
(운명선 90% 고정 + 출렁임 10%). 같은 시험지(고정 운명선)를 두 회차가 다른 개입으로
살면 결과가 갈린다 — "1회차 패닉 −x% vs 2회차 버팀 +y%"(§13.6 회차 비교).
순수/결정론(인메모리 RunStore).
"""

from __future__ import annotations

from sim import run_loop as RL
from sim import clone_spec as CS
from sim import result_card as RC
from sim.runs import RunStore, compare_runs
from sim.trap_pipeline import Intervention
from sim.resistance import STRATEGY_B

PANICKY = CS.build_clone_spec({"q_panic": 1.0, "q_fomo": 0.0})  # F1 취약(=100)


def _stats():
    return {"급락패닉저항": 25.0, "멘탈마모저항": 50.0, "익절거부제어": 50.0,
            "과대베팅제어": 50.0, "추격매수저항": 50.0, "막차불안저항": 50.0,
            "멘탈회복": 50.0}


def test_run_completes_30_days():
    store = RunStore()
    summary = RL.simulate_run(
        store, "r0", PANICKY, category="meme", start_price=100.0,
        start_stats=_stats(), start_quantity=1.0, start_cash=0.0,
    )
    assert summary.run_id == "r0"
    # 30일 스냅샷이 쌓였다(거울 비교의 데이터 소스)
    assert store.get_snapshot("r0", 29) is not None
    assert store.get_summary("r0") is summary


def test_deterministic():
    a = RL.simulate_run(RunStore(), "r", PANICKY, category="meme",
                        start_price=100.0, start_stats=_stats())
    b = RL.simulate_run(RunStore(), "r", PANICKY, category="meme",
                        start_price=100.0, start_stats=_stats())
    assert a.return_pct == b.return_pct
    assert a.emotion_overall == b.emotion_overall


def test_two_runs_diverge_intervention_saves_return():
    store = RunStore()
    # 1회차: 개입 없음 → day27 급락(실 업비트 DOGE −21.6%)에 패닉 매도(손실 확정)
    run_a = RL.simulate_run(
        store, "run_a", PANICKY, category="meme", start_price=100.0,
        start_stats=_stats(), start_quantity=1.0, start_cash=0.0,
    )
    # 2회차: day27에 좋은 개입(B+래포100, roll 0) → 버팀
    run_b = RL.simulate_run(
        store, "run_b", PANICKY, category="meme", start_price=100.0,
        start_stats=_stats(), start_quantity=1.0, start_cash=0.0,
        day_plan={27: {"intervention": Intervention(strategy=STRATEGY_B, rapport=100.0),
                       "roll": 0.0}},
    )
    # 1회차는 day27에 휘둘려 팔았고, 2회차는 버텼다
    assert store.get_snapshot("run_a", 27).swayed is True
    assert store.get_snapshot("run_b", 27).swayed is False
    # 버틴 회차가 더 나은 수익률(같은 운명선, 다른 선택, 다른 결과 §13.6)
    assert run_b.return_pct > run_a.return_pct


def test_m1_chase_diverges_fund_flow_and_return():
    # T-210 DoD — 다자산 감시(other_categories)가 있어야만 M1이 발동해 자금이
    # 실제로 움직인다. meme day23 = 실 업비트 DOGE +31.2% 급등(M1_SURGE_PCT=20 초과,
    # 2021년 실제 펌프 초입 — day23이 그 구간의 첫날). 보유는 stable(그날 사실상
    # 횡보 — 다른 트리거 없음, M1만 단독으로 켜짐).
    stats = _stats()
    stats["추격매수저항"] = 20.0   # 취약
    store = RunStore()

    run_no_watch = RL.simulate_run(
        store, "no_watch", PANICKY, category="stable", start_price=100.0,
        start_stats=dict(stats), start_quantity=0.0, start_cash=100.0,
        day_plan={23: {"roll": 100.0}}, other_categories=(),
    )
    run_watch = RL.simulate_run(
        store, "watch", PANICKY, category="stable", start_price=100.0,
        start_stats=dict(stats), start_quantity=0.0, start_cash=100.0,
        day_plan={23: {"roll": 100.0}}, other_categories=("meme",),
    )

    day_no_watch = store.get_snapshot("no_watch", 23)
    day_watch = store.get_snapshot("watch", 23)
    assert day_no_watch.trap is None                        # 감시 없음 → 평온
    assert day_watch.trap == "M1" and day_watch.fund_flow == "to_hotter"
    assert "meme" in day_watch.holdings                     # 실제로 meme 포지션이 생김
    assert "meme" not in day_no_watch.holdings
    # 자금흐름이 갈렸으니 최종 수익률도 갈린다(같은 운명선, 다른 결과 §13.6)
    assert run_watch.return_pct != run_no_watch.return_pct


def test_compare_runs_shows_divergence():
    store = RunStore()
    RL.simulate_run(store, "run_a", PANICKY, category="meme", start_price=100.0,
                    start_stats=_stats())
    RL.simulate_run(store, "run_b", PANICKY, category="meme", start_price=100.0,
                    start_stats=_stats(),
                    day_plan={27: {"intervention": Intervention(STRATEGY_B, 100.0), "roll": 0.0}})
    cmp = compare_runs(store, "run_a", "run_b", day=27)
    assert cmp["a"]["swayed"] is True and cmp["b"]["swayed"] is False
    assert cmp["a"]["fund_flow"] == "to_cash"   # 패닉 → 현금 도피


def test_summary_feeds_result_card():
    store = RunStore()
    s = RL.simulate_run(store, "r0", PANICKY, category="meme", start_price=100.0,
                        start_stats=_stats())
    card = RC.result_card(s)
    assert card["return_pct"] == s.return_pct
    assert card["grade"] in {"고수", "벼락부자형", "강철멘탈형", "호구"}
