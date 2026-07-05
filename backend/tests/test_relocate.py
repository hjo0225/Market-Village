"""T-272b · 행선지(장소) 지정 — relocate(slot, place).

🤖 council(2026-07-05): 일과는 항상 8장소 순열(T-241)이라 "슬롯 s를 장소 p로"는
p가 있던 슬롯과의 스왑과 등가 — 기존 회피(avoid)와 동일 파워라 정체성 비용 0.
반대급부(원래 장소가 밀려남)가 구조적으로 보존된다. 같은 요청 재전송=자기 자신과
스왑=no-op(자연 멱등, 게이트 4c ①).
"""

from __future__ import annotations

import pytest

import market_live_server as mls
from sim import clone_spec as CS
from sim.game_run import GameRun

CLONE = CS.build_clone_spec({"q_panic": 0.5})


def _g(run_id="t272b"):
    return GameRun(CLONE, category="meme", start_price=100.0, run_id=run_id)


def test_relocate_swaps_and_keeps_permutation():
    g = _g()
    places_before = sorted(g.schedule.values())
    wanted = g.schedule[5]
    g.relocate(1, wanted)
    assert g.schedule[1] == wanted
    assert sorted(g.schedule.values()) == places_before   # 8장소 순열 불변(T-241)


def test_relocate_idempotent():
    g = _g()
    place = g.schedule[3]
    g.relocate(1, place)
    once = dict(g.schedule)
    g.relocate(1, place)                                   # 재전송 = no-op
    assert g.schedule == once


def test_relocate_rejects_unknown_place():
    g = _g()
    with pytest.raises(ValueError):
        g.relocate(1, "우주정거장")


def test_relocate_changes_meetings():
    g = _g()
    g.relocate(2, "일터")                                  # T-222 — 일터@2=정호·미나
    p = g.preview_day()
    assert set(p["meetings"].get(2, [])) == {"value_investor", "contrarian"}


def test_relocate_not_carried_to_next_day():
    g = _g()
    g.relocate(2, "일터")
    g.advance_day()
    assert g.schedule == g._schedule_for_day(g.day)        # 그날 셔플로 복귀(T-248)


def test_relocate_designated_outside_candidates_falls_back():
    g = _g()
    g.relocate(2, "일터")
    default = g.preview_day()["picks"][2]
    other = ({"value_investor", "contrarian"} - {default}).pop()
    g.designate(2, other)
    g.relocate(2, "광장")                                  # 슬롯2 후보가 바뀜
    p = g.preview_day()
    assert p["designated"].get(2) != other                 # 후보 밖 지정은 무효 필터


def test_relocate_endpoint_and_serialization():
    mls.control_game_start(mls.GameStartBody(
        game_id="t272b_ep", answers={}, symbol="DOGE", start_price=100.0))
    r = mls.control_game_relocate(mls.GameRelocateBody(
        game_id="t272b_ep", slot=2, place="일터"))
    assert r["status"] == "ok"
    g = mls._get_game("t272b_ep")
    assert g.schedule[2] == "일터"
    g2 = GameRun.from_doc(g.to_doc(), fate_line=g.fl)
    assert g2.schedule == g.schedule                       # 기존 schedule 필드로 왕복
    bad = mls.control_game_relocate(mls.GameRelocateBody(
        game_id="t272b_ep", slot=2, place="없는곳"))
    assert bad["status"] == "error"
