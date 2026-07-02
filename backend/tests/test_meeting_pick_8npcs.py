"""T-222 · §9.2.1b 만남 선택 판정 × 8종 실데이터 결합 검증.

clone_picks_npc(순수)와 GameRun 배선(T-208b)은 기존재 — 이 티켓은 2종 스텁
시절 로직이 personas 8종 실데이터에서도 스펙대로 작동함을 봉인한다:
가장 약한 함정을 자극하는 NPC에 끌리고(결정론), 도움형만 겹치면 그중 하나.
"""

from __future__ import annotations

from sim import personas
from sim.avoidance import clone_picks_npc
from sim import clone_spec as CS
from sim.game_run import GameRun

ALL_IDS = [p["id"] for p in personas.TRADER_PERSONAS]
STIM = personas.npc_stim_traps()


def test_pick_follows_weakest_trap_across_full_pool():
    # 후보가 8종 전원일 때, 클론의 최약 함정을 자극하는 NPC가 선택된다.
    cases = {
        "F1": "panic_ant",
        "M1": "fomo_scalper",
        "M2": "conspiracy_influencer",
        "G2": "jackpot_gambler",
    }
    for trap, expected in cases.items():
        scores = {t: 10.0 for t in ("F1", "F2", "G1", "G2", "M1", "M2")}
        scores[trap] = 95.0                      # 이 함정이 최약(취약점 최대)
        assert clone_picks_npc(ALL_IDS, scores, STIM) == expected, trap


def test_pick_deterministic_across_calls():
    scores = {"F1": 80.0, "G2": 80.0}            # 동점 → id 사전순 고정
    first = clone_picks_npc(ALL_IDS, scores, STIM)
    assert all(clone_picks_npc(ALL_IDS, scores, STIM) == first for _ in range(5))


def test_helpers_only_slot_picks_one_deterministically():
    # 슬롯2를 일터로 정렬(T-248 일일 셔플 대응)하면 도움형 2명(정호·미나)만 겹친다 —
    # 그중 하나가 결정론적으로 선택되어 picks에 노출된다.
    g = GameRun(CS.build_clone_spec({"q_panic": 0.5}),
                category="meme", start_price=100.0, run_id="t222")
    cur = next(s for s, pl in g.schedule.items() if pl == "일터")
    if cur != 2:
        g.avoid(cur, 2)
    p = g.preview_day()
    assert set(p["meetings"].get(2, [])) == {"value_investor", "contrarian"}
    pick = p["picks"][2]
    assert pick in ("value_investor", "contrarian")
    assert STIM[pick] is None                     # 도움형만 있던 슬롯이므로
    assert g.preview_day()["picks"][2] == pick    # 재호출 동일(결정론)
