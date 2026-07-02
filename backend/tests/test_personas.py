"""T-220 · §9.5 페르소나 풀(매매 8종 + 관중 8종) 데이터 정합 검증.

데이터 원본: Market_Village_PRD_FINAL.md §9.5.3(매매, 수치 그대로) +
PRD_SOCIAL_NPC_BOARD.md §7(관중 수치·자산 배정·스케줄 초안).
부호 규칙(§9.5.2): 수치 높음 = 취약(코드 방식). 클론 표시용 "내성"과 반대.
"""

from __future__ import annotations

import os

import pytest

from sim import personas

_VALID_TRAPS = {"F1", "F2", "G1", "G2", "M1", "M2"}
# NPC 스케줄에 허용되는 장소 — 클론 홈 스폰(집_차트)은 제외(부속 PRD §7.1, T-241 확장).
_NPC_PLACES = {"카페", "일터", "광장", "운동", "펍", "마켓", "도서관"}

_ASSET_ROOT = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "environment", "frontend_server", "static_dirs", "assets", "characters",
)


def test_pool_sizes_and_unique_ids():
    assert len(personas.TRADER_PERSONAS) == 8   # §9.5.3 7종 + 한탕 도박꾼
    assert len(personas.SNS_PERSONAS) == 8      # §9.5.4
    ids = [p["id"] for p in personas.TRADER_PERSONAS + personas.SNS_PERSONAS]
    assert len(ids) == len(set(ids)) == 16


def test_trader_numbers_match_prd_9_5_3():
    # §9.5.3 표 그대로 (fear/greed/conf/exc/trust, herd, rumor)
    expected = {
        "panic_ant": (85, 15, 25, 72, 35, 0.9, 0.8),
        "fomo_scalper": (20, 90, 72, 85, 45, 0.85, 0.6),
        "conspiracy_influencer": (40, 65, 64, 82, 12, 0.5, 0.95),
        "value_investor": (30, 40, 72, 24, 72, 0.2, 0.2),
        "quant_trader": (45, 55, 75, 20, 66, 0.3, 0.3),
        "macro_whale": (10, 70, 86, 20, 70, 0.1, 0.2),
        "contrarian": (25, 60, 70, 46, 30, 0.05, 0.3),
        "jackpot_gambler": (15, 92, 85, 55, 30, 0.4, 0.5),
    }
    by_id = {p["id"]: p for p in personas.TRADER_PERSONAS}
    assert set(by_id) == set(expected)
    for pid, (f, g, c, e, t, herd, rumor) in expected.items():
        p = by_id[pid]
        assert (p["fear"], p["greed"], p["confidence"], p["excitement"],
                p["trust"]) == (f, g, c, e, t), pid
        assert (p["herd"], p["rumor"]) == (herd, rumor), pid


def test_all_numbers_in_range():
    for p in personas.TRADER_PERSONAS + personas.SNS_PERSONAS:
        for axis in ("fear", "greed", "confidence", "excitement", "trust"):
            assert 0 <= p[axis] <= 100, (p["id"], axis)
        assert 0.0 <= p["herd"] <= 1.0 and 0.0 <= p["rumor"] <= 1.0, p["id"]


def test_trader_stim_traps_and_roles():
    # 해침 4종은 유효 함정, 도움 4종은 None (§9.5.3 "주 자극 함정").
    stim = {p["id"]: p["stim_trap"] for p in personas.TRADER_PERSONAS}
    assert stim["panic_ant"] == "F1"
    assert stim["fomo_scalper"] == "M1"
    assert stim["conspiracy_influencer"] == "M2"
    assert stim["jackpot_gambler"] == "G2"
    for helper in ("value_investor", "quant_trader", "macro_whale", "contrarian"):
        assert stim[helper] is None, helper
    for v in stim.values():
        assert v is None or v in _VALID_TRAPS


def test_trader_schedules_valid():
    # 슬롯 1~8(§12.1b), 장소는 실제 어휘만, NPC당 최소 1칸.
    for p in personas.TRADER_PERSONAS:
        assert p["sched"], p["id"]
        for slot, place in p["sched"].items():
            assert isinstance(slot, int) and 1 <= slot <= 8, (p["id"], slot)
            assert place in _NPC_PLACES, (p["id"], place)


def test_npc_scheds_helper_matches_game_run_contract():
    # game_run._NPC_SCHEDS / _NPC_STIM_TRAP 대체용 헬퍼 형태 검증.
    scheds = personas.npc_scheds()
    stims = personas.npc_stim_traps()
    assert set(scheds) == set(stims) == {p["id"] for p in personas.TRADER_PERSONAS}
    for sched in scheds.values():
        assert all(isinstance(s, int) for s in sched)


def test_sns_personas_have_portraits_and_no_sched():
    # 관중은 맵 미등장(§9.5.4) — 스케줄 없음, 게시판 아바타(초상)만.
    for p in personas.SNS_PERSONAS:
        assert "sched" not in p, p["id"]
        assert p["portrait"], p["id"]


@pytest.mark.skipif(
    not os.path.isdir(_ASSET_ROOT),
    reason="environment/ 자산은 gitignore — 로컬 전용 검증(CI엔 없음)",
)
def test_assigned_assets_exist_on_disk():
    for p in personas.TRADER_PERSONAS:
        path = os.path.join(_ASSET_ROOT, p["sprite"] + ".png")
        assert os.path.isfile(path), path
    for p in personas.TRADER_PERSONAS + personas.SNS_PERSONAS:
        path = os.path.join(_ASSET_ROOT, "profile", p["portrait"] + ".png")
        assert os.path.isfile(path), path


def test_asset_assignment_no_duplicates():
    # 매매 스프라이트 8종 서로 다름, 초상 16종(매매+관중) 서로 다름.
    sprites = [p["sprite"] for p in personas.TRADER_PERSONAS]
    assert len(sprites) == len(set(sprites))
    portraits = [p["portrait"] for p in personas.TRADER_PERSONAS + personas.SNS_PERSONAS]
    assert len(portraits) == len(set(portraits))
