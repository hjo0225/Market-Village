"""T-211 · 고유 이벤트 게임 주입 (§5.4 / §12.3 외란).

인터뷰 답변이 만든 클론 고유 이벤트(커피 쏟음 등)를 일과 중 확률 외란으로 주입한다.
효과는 작게(§12.3) — 멘탈회복만 ±2~4 건드린다(트리거가 아니라 '마지막 한 방울').
멘탈회복은 어떤 함정의 저항에도 안 쓰이므로 수익률(거울)엔 영향 없음(측정 보호).
"""

from __future__ import annotations

import random

from sim import day_loop as DL
from sim import clone_spec as CS
from sim.game_run import GameRun

SPEC = CS.build_clone_spec({"q_panic": 1.0, "q_fomo": 1.0, "q_check": 1.0, "q_rumor": 1.0})


def test_clone_disturbance_pulls_unique_event():
    ids = {e["id"] for e in SPEC.unique_events}
    fired = [DL.clone_disturbance(SPEC, random.Random(s)) for s in range(300)]
    hits = [e for e in fired if e is not None]
    assert hits, "외란이 가끔은 발생해야 함"
    for e in hits:
        assert e["id"] in ids                       # 클론 고유 이벤트에서 나옴
        assert {"id", "trigger", "effect", "delta"} <= set(e)
        assert 2.0 <= abs(e["delta"]) <= 4.0         # 작게(§12.3)


def test_no_unique_events_safe():
    spec = CS.build_clone_spec({})   # 폴백 이벤트 1개는 있음
    # 발생해도 크래시 없음
    for s in range(50):
        DL.clone_disturbance(spec, random.Random(s))


def test_game_surfaces_event_and_nudges_mental():
    g = GameRun(SPEC, category="meme", start_price=100.0, run_id="ue")
    saw_event = False
    for _ in range(30):
        g.advance_day()
        if g.last_event is not None:
            saw_event = True
    assert saw_event                                  # 30일 중 외란이 떴다
    assert "last_event" in g.state()


def test_disturbance_does_not_break_return_equivalence():
    # 외란이 멘탈회복만 건드리므로 수익률은 run_loop과 여전히 동치
    from sim import run_loop as RL
    from sim.runs import RunStore
    g = GameRun(SPEC, category="meme", start_price=100.0, run_id="ue2",
                start_stats={"급락패닉저항": 25, "멘탈마모저항": 50, "익절거부제어": 50,
                            "과대베팅제어": 50, "추격매수저항": 50, "막차불안저항": 50,
                            "멘탈회복": 50})
    for _ in range(30):
        g.advance_day()
    batch = RL.simulate_run(RunStore(), "b", SPEC, category="meme", start_price=100.0,
                            start_stats={"급락패닉저항": 25, "멘탈마모저항": 50, "익절거부제어": 50,
                            "과대베팅제어": 50, "추격매수저항": 50, "막차불안저항": 50,
                            "멘탈회복": 50})
    assert g.summary.return_pct == batch.return_pct   # 수익률 불변(측정 보호)
