"""T-DB · RunStore 직렬화 왕복 — MongoDB 영속화의 순수함수 기반.

DB 연결 없이 dict 왕복(to_dict → from_dict)만 검증한다(실제 DB I/O는
별도 통합 테스트, 이 모듈은 순수 데이터 변환만).
"""

from __future__ import annotations

from sim.runs import DailySnapshot, RunStore, RunSummary


def test_round_trip_preserves_summaries():
    store = RunStore()
    store.start_run("run1")
    store.record_summary(RunSummary(run_id="run1", return_pct=12.5, grade="고수",
                                    emotion_overall={"멘탈회복": 60.0}))
    doc = store.to_dict()
    restored = RunStore.from_dict(doc)
    assert restored.summaries() == store.summaries()


def test_round_trip_preserves_snapshots():
    store = RunStore()
    store.start_run("run1")
    snap = DailySnapshot(day=5, holdings={"meme": {"quantity": 1.0, "avg_cost": 100.0}},
                         cash=20.0, total_asset=120.0, realized_pnl=5.0,
                         emotion_stats={"급락패닉저항": 42.0}, swayed=True,
                         fund_flow="to_cash", trap="F1")
    store.record_snapshot("run1", snap)
    doc = store.to_dict()
    restored = RunStore.from_dict(doc)
    assert restored.get_snapshot("run1", 5) == snap


def test_round_trip_preserves_run_order_across_multiple_runs():
    store = RunStore()
    store.start_run("run1")
    store.record_summary(RunSummary(run_id="run1", return_pct=1.0))
    store.start_run("run2")
    store.record_summary(RunSummary(run_id="run2", return_pct=2.0))
    doc = store.to_dict()
    restored = RunStore.from_dict(doc)
    assert [s.run_id for s in restored.summaries()] == ["run1", "run2"]


def test_empty_store_round_trips():
    store = RunStore()
    doc = store.to_dict()
    restored = RunStore.from_dict(doc)
    assert restored.summaries() == []
