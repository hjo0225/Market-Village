"""T-208b · §9.2.1b 클론의 NPC 선택 — GameRun 배선.

같은 슬롯에 NPC가 겹치면(overlap_meetings) *플레이어*가 아니라 *클론*이 누구와
대화할지 고른다(가장 약한 함정을 자극하는 NPC에 끌림, sim.avoidance.clone_picks_npc
는 기존재하는 순수함수). 지금까지는 GameRun.preview_day()가 후보 목록(meetings)만
보여주고 실제 클론의 선택은 노출하지 않았다 — 이 티켓은 그 배선만 잇는다(§9.2.2
1:1 권유의 능동적 npc_id 선택과는 별개 메커니즘, persuade()는 안 건드림).
"""

from __future__ import annotations

from sim.game_run import GameRun
from sim import clone_spec as CS

CLONE = CS.build_clone_spec({"q_panic": 0.5})


def _g():
    return GameRun(CLONE, category="meme", start_price=100.0, run_id="pick")


def test_preview_day_exposes_clone_pick_per_meeting_slot():
    g = _g()
    p = g.preview_day()
    assert 3 in p["meetings"]          # 슬롯3에서 개구리(F1 자극형)와 마주침(기존 계약)
    assert "picks" in p
    assert p["picks"][3] == "frog"     # 후보가 frog 하나뿐이어도 선택 결과가 노출돼야 함


def test_preview_day_pick_matches_clone_picks_npc_pure_function():
    from sim.avoidance import clone_picks_npc
    from sim.game_run import _NPC_STIM_TRAP

    g = _g()
    p = g.preview_day()
    for slot, candidates in p["meetings"].items():
        expected = clone_picks_npc(candidates, g.clone_spec.trap_scores, _NPC_STIM_TRAP)
        assert p["picks"][slot] == expected


def test_avoided_slot_has_no_pick():
    g = _g()
    g.avoid(3, 1)
    p = g.preview_day()
    assert 3 not in p["meetings"]
    assert 3 not in p["picks"]
