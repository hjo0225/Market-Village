"""T-273 · 마을 분위기 프리셋 — 보수/공격/균형이 NPC 노출 빈도만 기울인다.

🤖 council(2026-07-05): 인원 구성 변경(횡단 파괴적) 대신 **노출 빈도 가중** —
8종 전원 잔류 + 함정 자극 4종(F1/M1/M2/G2) 전부 만날 수 있어 6함정 커버리지
구조 보존. 프리셋은 favored 그룹에 고정 슬롯 +1씩만(순수 파생, RNG 없음).
"""

from __future__ import annotations

import market_live_server as mls
from sim import clone_spec as CS
from sim import personas
from sim.day_loop import overlap_meetings
from sim.game_run import GameRun

CLONE = CS.build_clone_spec({"q_panic": 0.5})
STIM4 = {"panic_ant", "fomo_scalper", "conspiracy_influencer", "jackpot_gambler"}
HELP4 = {"value_investor", "quant_trader", "macro_whale", "contrarian"}


def test_default_preset_identical_to_legacy():
    # 회귀 봉인 — 기본(균형)은 기존 npc_scheds()와 바이트 동일.
    assert personas.npc_scheds() == {p["id"]: p["sched"] for p in personas.TRADER_PERSONAS}
    assert personas.npc_scheds("balanced") == personas.npc_scheds()


def test_aggressive_adds_one_slot_to_stim_only():
    base, agg = personas.npc_scheds(), personas.npc_scheds("aggressive")
    assert set(agg) == set(base)                              # 8종 전원 잔류
    for nid in STIM4:
        assert len(agg[nid]) == len(base[nid]) + 1            # 함정 4종만 +1
        assert set(base[nid].items()) <= set(agg[nid].items())  # 기존 슬롯 보존
    for nid in HELP4:
        assert agg[nid] == base[nid]                          # 도움형 무변
    assert personas.npc_stim_traps() == {p["id"]: p["stim_trap"]
                                         for p in personas.TRADER_PERSONAS}


def test_conservative_adds_one_slot_to_helpers_only():
    base, con = personas.npc_scheds(), personas.npc_scheds("conservative")
    for nid in HELP4:
        assert len(con[nid]) == len(base[nid]) + 1
    for nid in STIM4:
        assert con[nid] == base[nid]


def test_unknown_preset_falls_back_to_balanced():
    assert personas.npc_scheds("nonsense") == personas.npc_scheds()


def _meeting_bias(village: str, run_id: str = "vp") -> int:
    """30일 결정론 일과 대비 함정 NPC 후보 등장 수(순수 계산 — 상태 무변이)."""
    g = GameRun(CLONE, category="meme", start_price=100.0, run_id=run_id,
                village=village)
    count = 0
    for day in range(30):
        meetings = overlap_meetings(g._schedule_for_day(day), g.npc_scheds)
        count += sum(1 for cands in meetings.values() for c in cands if c in STIM4)
    return count


def test_gamerun_village_biases_meetings_deterministically():
    agg1, agg2 = _meeting_bias("aggressive"), _meeting_bias("aggressive")
    bal, con = _meeting_bias("balanced"), _meeting_bias("conservative")
    assert agg1 == agg2                                       # 결정론
    assert agg1 > bal > 0                                     # 공격 마을=함정 노출↑
    assert con <= bal                                         # 신중 마을=함정 노출≤


def test_village_serialization_roundtrip_and_backcompat():
    g = GameRun(CLONE, category="meme", start_price=100.0, run_id="vp_ser",
                village="aggressive")
    doc = g.to_doc()
    assert doc["village"] == "aggressive"
    g2 = GameRun.from_doc(doc, fate_line=g.fl)
    assert g2.npc_scheds == g.npc_scheds
    doc.pop("village")                                        # 구 문서 시뮬레이션
    g3 = GameRun.from_doc(doc, fate_line=g.fl)
    assert g3.npc_scheds == personas.npc_scheds("balanced")


def test_start_endpoint_accepts_village():
    r = mls.control_game_start(mls.GameStartBody(
        game_id="vp_ep", answers={}, symbol="DOGE", start_price=100.0,
        village="aggressive"))
    assert r["status"] == "ok"
    g = mls._get_game("vp_ep")
    assert g.npc_scheds == personas.npc_scheds("aggressive")
