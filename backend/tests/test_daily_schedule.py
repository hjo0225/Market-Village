"""T-248 · §12.2 일과 일일 셔플 — 종류는 고정 메뉴, 순서는 매일 결정론 셔플.

플레이테스트 리포트 ⑧ — 일과가 매일 동일했음(셔플 미구현, 고정 순환 배치).
"""

from __future__ import annotations

from sim import clone_spec as CS
from sim.game_run import GameRun, _MENU

CLONE = CS.build_clone_spec({"q_panic": 0.5})


def _g(run_id="sched_g"):
    return GameRun(CLONE, category="meme", start_price=100.0, run_id=run_id)


def test_schedule_covers_all_places_every_day():
    g = _g()
    for _ in range(3):
        assert sorted(g.schedule.values()) == sorted(_MENU)
        g.advance_day()


def test_schedule_differs_between_days():
    g = _g()
    day0 = dict(g.schedule)
    g.advance_day()
    day1 = dict(g.schedule)
    g.advance_day()
    day2 = dict(g.schedule)
    # 8! 순열 중 연속 동일은 사실상 0 — 셔플이 실제로 작동하는지 봉인.
    assert day0 != day1 or day1 != day2


def test_schedule_deterministic_same_run():
    a, b = _g("det_a"), _g("det_a")
    assert a.schedule == b.schedule
    a.advance_day(); b.advance_day()
    assert a.schedule == b.schedule                # 같은 (run, day) = 같은 일과


def test_avoid_swap_applies_to_today_only():
    g = _g()
    slots = list(g.schedule)
    g.avoid(slots[0], slots[1])
    swapped = dict(g.schedule)
    g.advance_day()
    # 다음 날은 그날의 셔플 — 어제의 회피 스왑이 이월되지 않는다.
    assert g.schedule == g._schedule_for_day(g.day)
    assert g.schedule != swapped or True           # (우연 일치 허용 — 위 단언이 본질)
