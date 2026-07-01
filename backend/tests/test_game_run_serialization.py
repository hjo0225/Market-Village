"""T-DB · GameRun 직렬화 왕복 — 서버 재시작 후 game_id로 재개하기 위한 기반.

DB 연결 없이 dict 왕복만 검증(실제 MongoDB I/O는 별도 통합 테스트).
"""

from __future__ import annotations

from sim.game_run import GameRun
from sim import clone_spec as CS
from sim.trap_pipeline import Intervention
from sim.resistance import STRATEGY_B

CLONE = CS.build_clone_spec({"q_panic": 1.0, "q_fomo": 0.0})


def _g(**kw):
    base = dict(category="meme", start_price=100.0, run_id="run1")
    base.update(kw)
    return GameRun(CLONE, **base)


def test_round_trip_preserves_fresh_state():
    g = _g()
    doc = g.to_doc()
    restored = GameRun.from_doc(doc)
    assert restored.state() == g.state()


def test_round_trip_preserves_state_after_days_and_social():
    g = _g()
    g.persuade("turtle", direction="calm", roll=0.0)   # 래포 변화
    g.fgi_post("fear_join", roll=0.0)                   # crowd_mood 변화
    for _ in range(5):
        g.advance_day()
    doc = g.to_doc()
    restored = GameRun.from_doc(doc)
    assert restored.state() == g.state()
    assert restored.holding == g.holding
    assert restored.schedule == g.schedule


def test_round_trip_preserves_avoided_schedule():
    g = _g()
    g.avoid(3, 1)
    doc = g.to_doc()
    restored = GameRun.from_doc(doc)
    assert restored.schedule == g.schedule


def test_round_trip_after_finished_run_preserves_summary_and_store():
    g = _g()
    for _ in range(30):
        g.advance_day()
    assert g.finished is True
    doc = g.to_doc()
    restored = GameRun.from_doc(doc)
    assert restored.finished is True
    assert restored.summary == g.summary
    assert restored.store.summaries() == g.store.summaries()


def test_restored_game_can_continue_playing_identically_to_original():
    # 결정론(기둥3) — 복원된 세션에서 이어 진행해도 원본과 동일한 결과.
    g_a = _g(run_id="a")
    for _ in range(10):
        g_a.advance_day()
    doc = g_a.to_doc()
    g_b = GameRun.from_doc(doc)
    for _ in range(20):
        g_a.advance_day(intervention=Intervention(STRATEGY_B, 60.0), roll=40.0)
        g_b.advance_day(intervention=Intervention(STRATEGY_B, 60.0), roll=40.0)
    assert g_a.state() == g_b.state()
    assert g_a.summary == g_b.summary
