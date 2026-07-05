"""T-281 · 만남 1:1 대화 생성 — 핸드폰 채팅 연출용(표현 전용, 결정론).

사용자 반복 피드백(2026-07-05): 만남 대화는 맵 말풍선이 아니라 핸드폰 채팅창.
대사는 (game_id, day, npc_id) 결정론이고 게임 수치에 영향 없음(감정 효과는
기존 밤 정산 그대로 — T-249).
"""

from __future__ import annotations

import market_live_server as mls
from sim import clone_spec as CS
from sim import meeting_talk, personas
from sim.game_run import GameRun

_SHAKEN = {"급락패닉저항": 30.0}
_STEADY = {"급락패닉저항": 80.0}


def test_dialogue_schema_and_determinism():
    a = meeting_talk.dialogue("g1", 3, "panic_ant", _SHAKEN)
    b = meeting_talk.dialogue("g1", 3, "panic_ant", _SHAKEN)
    assert a == b                                     # 같은 시드 = 같은 대화
    assert [m["who"] for m in a] == ["npc", "clone", "npc"]
    assert all(m["text"] for m in a)
    # 다른 날/다른 게임이면 대화가 달라질 수 있는 시드 구조(최소 한 케이스 상이)
    variants = {tuple(m["text"] for m in meeting_talk.dialogue(g, d, "panic_ant", _SHAKEN))
                for g in ("g1", "g2") for d in (1, 2, 3)}
    assert len(variants) >= 2


def test_dialogue_differs_by_persona():
    openers = {meeting_talk.dialogue("g1", 1, pid, _STEADY)[0]["text"]
               for pid in ("panic_ant", "value_investor", "jackpot_gambler")}
    assert len(openers) == 3                          # 페르소나별 화두가 다르다


def test_clone_reaction_follows_relevant_stat():
    # 자극형(panic_ant=F1→급락패닉저항): 스탯<50=동요, ≥50=버팀.
    shaken = meeting_talk.dialogue("g1", 1, "panic_ant", _SHAKEN)[1]["text"]
    steady = meeting_talk.dialogue("g1", 1, "panic_ant", _STEADY)[1]["text"]
    assert shaken in meeting_talk._CLONE_SHAKEN
    assert steady in meeting_talk._CLONE_STEADY


def test_helper_persona_gets_helped_reaction_and_closer():
    out = meeting_talk.dialogue("g1", 1, "value_investor", _SHAKEN)
    assert out[1]["text"] in meeting_talk._CLONE_HELPED
    assert out[2]["text"] in meeting_talk._CLOSERS_HELP


def test_meetings_by_band_carries_chat_payload():
    # 서버 헬퍼가 이름 외에 role·portrait·lines(채팅 대사)까지 동봉해야
    # 프론트 폰 채팅창이 그릴 수 있다. designate로 만남을 확정해 검증.
    g = GameRun(CS.build_clone_spec({"q_panic": 0.5}), category="meme",
                start_price=100.0, run_id="mt")
    picks = g.preview_day().get("picks") or {}
    assert picks, "이 시드에선 day 0에 픽이 있어야 함(결정론)"
    npc = next(iter(picks.values()))
    out = mls._meetings_by_band(g, "mt_game")
    entries = [m for band in out.values() for m in band]
    assert len(entries) == len(picks)
    m = next(e for e in entries if e["id"] == npc)
    p = personas.trader_by_id(npc)
    assert m["name"] == p["name"] and m["role"] == p["role"]
    assert m["portrait"] == p["portrait"]
    assert [x["who"] for x in m["lines"]] == ["npc", "clone", "npc"]
