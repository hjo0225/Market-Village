"""T-117 · §9.2.1 회피(일과 순서 변경) + §9.2.1b 클론의 NPC 선택(약점).

교류에 대한 플레이어 개입 = 회피. 전날 밤 일과 항목 하나의 순서만 변경(트레이드오프).
동선이 바뀌면 마주치는 NPC가 달라진다. 같은 슬롯·장소에 여럿이면 클론이 한 명을
고르는데, 누구를 고르냐는 플레이어가 아니라 클론 성격 — *가장 약한 함정을 자극하는
NPC*에게 끌린다(거울: "하필 나쁜 상대를 고름").
"""

from __future__ import annotations

from sim import avoidance as AV
from sim.day_loop import overlap_meetings


def test_avoid_swaps_one_item():
    sched = {1: "카페", 3: "광장", 5: "일터", 7: "집"}
    out = AV.avoid(sched, 3, 7)
    assert out[3] == "집" and out[7] == "광장"   # 두 슬롯 내용 스왑
    assert out[1] == "카페" and out[5] == "일터"  # 나머지 불변
    assert sorted(out.values()) == sorted(sched.values())  # 활동 집합 불변
    assert sched[3] == "광장"  # 원본 불변(순수)


def test_clone_drawn_to_weakest_trap_npc():
    # 클론이 FOMO(M1)에 가장 약함. 후보 중 M1 자극 NPC에게 끌림.
    candidates = ["turtle", "frog", "gambler"]
    clone_trap_scores = {"F1": 30.0, "M1": 90.0, "G2": 40.0}
    npc_stim = {"turtle": None, "frog": "M1", "gambler": "G2"}
    assert AV.clone_picks_npc(candidates, clone_trap_scores, npc_stim) == "frog"


def test_stable_npc_is_least_attractive():
    # 자극 안 하는 안정형만 있으면 그래도 한 명(결정론) 고르되, 자극형이 있으면 그쪽
    candidates = ["turtle", "quant"]
    picked = AV.clone_picks_npc(candidates, {"M1": 90.0}, {"turtle": None, "quant": None})
    assert picked in candidates           # 안정형뿐이어도 한 명은 고름
    # 자극형이 추가되면 그쪽으로
    picked2 = AV.clone_picks_npc(
        ["turtle", "frog"], {"M1": 90.0}, {"turtle": None, "frog": "M1"})
    assert picked2 == "frog"


def test_pick_tiebreak_deterministic():
    # 같은 취약점 자극이 둘이면 id 사전순 tie-break(결정론)
    candidates = ["zeta", "alpha"]
    scores = {"M1": 90.0}
    stim = {"zeta": "M1", "alpha": "M1"}
    assert AV.clone_picks_npc(candidates, scores, stim) == "alpha"


def test_empty_candidates_none():
    assert AV.clone_picks_npc([], {"M1": 90.0}, {}) is None


def test_avoidance_changes_who_we_meet():
    # 회피로 클론 동선을 틀면 마주칠 NPC가 달라진다(§9.2.1)
    clone = {3: "광장", 7: "집"}
    npcs = {"frog": {3: "광장"}}        # 슬롯3 광장에서 frog와 마주침
    before = overlap_meetings(clone, npcs)
    assert before.get(3) == ["frog"]
    # 광장을 슬롯7로 옮기면(집은 슬롯3으로) frog와 안 마주침
    moved = AV.avoid(clone, 3, 7)
    after = overlap_meetings(moved, npcs)
    assert 3 not in after  # frog 회피 성공
