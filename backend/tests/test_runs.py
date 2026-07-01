"""T-108 · §13 회차(NG+) 스토어 + 회차 비교.

거울은 한 판 안이 아니라 "1회차의 나 vs 2회차의 나"를 겹쳐 보는 자리에서 나온다
(기둥2). §13.8 3계층 영속: 회차요약(영구) / 위기로그(최근 N=5) / 개입로그(현재+직전).
회차마다 래포·확증편향은 리셋되지만(클론은 "처음 만남") 요약은 누적 → 나는 성장.
인메모리(Mongo 영속화는 D-D 하드게이트, 별도).
"""

from __future__ import annotations

from sim import runs
from sim.runs import RunStore, RunSummary, DailySnapshot


def _summary(run_id, ret=10.0, grade="강철멘탈형"):
    return RunSummary(
        run_id=run_id, return_pct=ret,
        emotion_overall={"공포내성": 40}, grade=grade,
        trap_counts={"F1": {"triggered": 2, "resisted": 1}},
        clone_spec_snapshot={"F1": 80},
    )


def _snap(day, swayed=False, fund_flow="hold_winner", companion="거북이", ret=5.0):
    return DailySnapshot(
        day=day, holdings={"A": {"quantity": 1, "avg_cost": 100}}, cash=1000.0,
        total_asset=1100.0, realized_pnl=ret, trades=[], emotion_stats={"공포내성": 40},
        swayed=swayed, fund_flow=fund_flow, companion=companion,
    )


def test_summary_is_permanent():
    st = RunStore()
    for i in range(8):                       # 8회차
        st.start_run(f"r{i}")
        st.record_summary(_summary(f"r{i}", ret=float(i)))
    # 요약은 영구 — 모든 회차가 컬렉션에 남음(성장 연대기 §14.3)
    assert len(st.summaries()) == 8
    assert st.get_summary("r0").return_pct == 0.0


def test_crisis_log_keeps_recent_n():
    st = RunStore(keep_crisis=5)
    for i in range(8):
        st.start_run(f"r{i}")
        st.record_crisis(f"r{i}", day=14, log={"action": "panic_sell"})
    # 위기로그는 최근 5회차만 (§13.8)
    assert st.get_crisis("r7", 14) is not None
    assert st.get_crisis("r0", 14) is None     # 오래된 건 드롭
    assert st.get_summary  # 요약 접근자는 여전히 존재


def test_impulse_log_current_and_prev_only():
    st = RunStore()
    for i in range(4):
        st.start_run(f"r{i}")
        st.record_impulse(f"r{i}", {"day": 5, "trap": "M1"})
    # 개입(충동)로그는 현재+직전만 (§13.8 과거찌르기 A전략용)
    assert st.get_impulses("r3")              # 현재
    assert st.get_impulses("r2")              # 직전
    assert st.get_impulses("r1") == []        # 그 이전은 드롭


def test_start_run_resets_rapport_and_bias():
    st = RunStore()
    state = st.start_run("r0", initial_rapport=35.0)
    assert state["rapport"] == 35.0
    assert state["confirmation_locked"] is False


def test_compare_runs():
    st = RunStore()
    st.start_run("r0")
    st.record_snapshot("r0", _snap(14, swayed=True, fund_flow="to_cash",
                                   companion="개구리", ret=-22.0))
    st.start_run("r1")
    st.record_snapshot("r1", _snap(14, swayed=False, fund_flow="hold_winner",
                                   companion="거북이", ret=8.0))
    cmp = runs.compare_runs(st, "r0", "r1", day=14)
    assert cmp["day"] == 14
    assert cmp["a"]["swayed"] is True and cmp["b"]["swayed"] is False
    assert cmp["a"]["fund_flow"] == "to_cash"
    assert cmp["a"]["companion"] == "개구리" and cmp["b"]["companion"] == "거북이"
    assert cmp["a"]["realized_pnl"] == -22.0 and cmp["b"]["realized_pnl"] == 8.0


def test_compare_missing_day_safe():
    st = RunStore()
    st.start_run("r0")
    st.start_run("r1")
    cmp = runs.compare_runs(st, "r0", "r1", day=99)
    assert cmp["a"] is None and cmp["b"] is None
