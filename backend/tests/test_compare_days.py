"""T-227 · §13.6 회차 비교 — 분기일 자동 추출 (PRD_MIRROR_COMPARE C2).

30일 나열 대신, 두 회차의 스냅샷이 실제로 갈린 날(swayed/fund_flow/companion
중 하나라도 다름)만 골라 보여준다("결과 아는 날은 빨리감기" §13.3).
"""

from __future__ import annotations

import market_live_server as mls
from sim.runs import DailySnapshot, RunStore, diverging_days


def _store_with(a_days: dict, b_days: dict) -> RunStore:
    st = RunStore()
    st.start_run("r1")
    st.start_run("r2")
    for day, kw in a_days.items():
        st.record_snapshot("r1", DailySnapshot(day=day, **kw))
    for day, kw in b_days.items():
        st.record_snapshot("r2", DailySnapshot(day=day, **kw))
    return st


def test_diverging_days_finds_behavior_differences():
    st = _store_with(
        {1: {"swayed": False}, 2: {"swayed": True, "fund_flow": "to_cash"},
         3: {"companion": "panic_ant"}},
        {1: {"swayed": False}, 2: {"swayed": False},
         3: {"companion": "value_investor"}},
    )
    assert diverging_days(st, "r1", "r2") == [2, 3]   # 1일차는 동일 → 제외


def test_diverging_days_empty_when_identical():
    st = _store_with({1: {"swayed": True}}, {1: {"swayed": True}})
    assert diverging_days(st, "r1", "r2") == []


def test_diverging_days_ignores_days_missing_in_either_run():
    st = _store_with({1: {"swayed": True}, 5: {"swayed": True}},
                     {1: {"swayed": False}})
    assert diverging_days(st, "r1", "r2") == [1]      # 5일차는 r2에 없음 → 제외


def test_compare_days_endpoint():
    mls.control_game_start(mls.GameStartBody(
        game_id="cmp_days", answers={}, symbol="DOGE", start_price=100.0))
    g = mls._get_game("cmp_days")
    g.store.start_run("runA")
    g.store.start_run("runB")
    g.store.record_snapshot("runA", DailySnapshot(day=3, swayed=True, fund_flow="to_cash"))
    g.store.record_snapshot("runB", DailySnapshot(day=3, swayed=False))
    r = mls.control_game_compare_days(game_id="cmp_days", run_a="runA", run_b="runB")
    assert r["status"] == "ok" and r["days"] == [3]


def test_compare_days_endpoint_missing_game():
    assert mls.control_game_compare_days(
        game_id="nope", run_a="a", run_b="b")["status"] == "error"


def test_compare_days_endpoint_rejects_unknown_or_same_runs():
    # /review 지적 — 존재하지 않는 run/자기 자신 비교는 빈 목록("같은 선택")이
    # 아니라 에러여야 한다(프론트가 틀린 결론을 그리지 않게).
    mls.control_game_start(mls.GameStartBody(
        game_id="cmp_bad", answers={}, symbol="DOGE", start_price=100.0))
    g = mls._get_game("cmp_bad")
    g.store.record_snapshot("run1", DailySnapshot(day=1))
    assert mls.control_game_compare_days(
        game_id="cmp_bad", run_a="run1", run_b="ghost")["status"] == "error"
    assert mls.control_game_compare_days(
        game_id="cmp_bad", run_a="run1", run_b="run1")["status"] == "error"
