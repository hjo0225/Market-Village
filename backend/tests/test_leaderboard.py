"""T-245 · §13.7 미니 리더보드 — NPC 가상 수익률(무상태 순수 파생).

council M4/R10: 페르소나 고정 규칙 × 운명선의 순수함수 — 상태 저장 없이 day0부터
재계산(재시작 안전·결정론), fate_line 읽기 전용이라 가격 영향 0이 구조로 보장.
감정 결합 없음(v2에서 R6/R8 통과 시).
"""

from __future__ import annotations

import market_live_server as mls
from sim import npc_traders, personas
from sim.fate_line import load_fate_line


def test_npc_return_deterministic_and_price_safe():
    fl = load_fate_line()
    p = personas.TRADER_PERSONAS[0]
    a = npc_traders.npc_return_pct(p, fl, "meme", 15)
    b = npc_traders.npc_return_pct(p, fl, "meme", 15)
    assert a == b                                   # 순수 재계산 = 결정론
    assert isinstance(a, float)


def test_npc_returns_differ_by_persona():
    # 성격이 다르면 같은 시장에서 다른 성적 — 전원 동일하면 규칙이 죽은 것.
    fl = load_fate_line()
    vals = {p["id"]: npc_traders.npc_return_pct(p, fl, "meme", 25)
            for p in personas.TRADER_PERSONAS}
    assert len(set(vals.values())) > 1


def test_day0_returns_are_zero():
    fl = load_fate_line()
    for p in personas.TRADER_PERSONAS:
        assert npc_traders.npc_return_pct(p, fl, "meme", 0) == 0.0


def test_leaderboard_endpoint_ranks_clone_among_npcs():
    mls.control_game_start(mls.GameStartBody(
        game_id="lb_game", answers={}, symbol="DOGE", start_price=100.0))
    r = mls.control_game_leaderboard(game_id="lb_game")
    assert r["status"] == "ok"
    assert r["total"] == 9                          # NPC 8 + 클론
    ids = [e["id"] for e in r["board"]]
    assert "clone" in ids
    pcts = [e["return_pct"] for e in r["board"]]
    assert pcts == sorted(pcts, reverse=True)       # 수익률 내림차순
    assert 1 <= r["clone_rank"] <= 9


def test_leaderboard_endpoint_missing_game():
    assert mls.control_game_leaderboard(game_id="nope")["status"] == "error"


def test_npc_action_single_source_with_returns():
    """T-256 — 매매 판정 헬퍼는 수익률 규칙과 단일 소스(연출↔순위 불일치 금지)."""
    from sim.fate_line import load_fate_line
    fl = load_fate_line()
    p = personas.trader_by_id("panic_ant")
    acts = [npc_traders.npc_action_on_day(p, fl, "meme", d) for d in range(1, 26)]
    assert any(a is not None for a in acts)          # 25일이면 매매가 나온다
    assert set(acts) <= {"buy", "sell", None}


def test_trades_endpoint_lists_that_days_actions():
    mls.control_game_start(mls.GameStartBody(
        game_id="tr_game", answers={}, symbol="DOGE", start_price=100.0))
    r = mls.control_game_trades(game_id="tr_game", day=5)
    assert r["status"] == "ok" and r["day"] == 5
    for tr in r["trades"]:
        assert tr["action"] in ("buy", "sell") and tr["id"] and tr["name"]
