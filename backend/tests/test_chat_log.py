"""T-288 · NPC별 대화 로그(메신저 대화방) — GET /control/game/chat_log.

스냅샷(met·emotion_stats)과 소셜 로그에서 npc별 일자별 대화를 조립한다.
만남 대사는 meeting_talk 결정론 재생성(그날 밤 스탯 스냅샷 사용), 권유는
방향·성패 요약. 순수 조회(변이 없음).
"""

from __future__ import annotations

import market_live_server as mls
from sim import clone_spec as CS
from sim import meeting_talk


def _start(gid: str):
    return mls.control_game_start(mls.GameStartBody(
        game_id=gid, answers={}, symbol="DOGE", start_price=100.0))


def _advance(gid: str):
    return mls.control_game_advance(mls.GameAdvanceBody(game_id=gid))


def test_chat_log_contains_meeting_lines_for_met_npc():
    _start("chat_a")
    g = mls._get_game("chat_a")
    # 만남이 기록될 때까지 진행(픽은 매일 있지만 met 기록은 advance 시점)
    npc = None
    for _ in range(6):
        _advance("chat_a")
        snaps = g.store.snapshots(g.run_id)
        for day, s in sorted(snaps.items()):
            if s.met:
                npc = s.met[0]
                met_day = day
                break
        if npc:
            break
    assert npc, "6일 내 만남 기록 없음"
    r = mls.control_game_chat_log(game_id="chat_a", npc_id=npc)
    assert r["status"] == "ok"
    day_entry = next(d for d in r["days"] if d["day"] == met_day)
    meeting = next(e for e in day_entry["entries"] if e["kind"] == "meeting")
    # 결정론 재생성 — 같은 (game, day, npc, 그날 스탯)이면 같은 대사
    snap = g.store.snapshots(g.run_id)[met_day]
    expect = meeting_talk.dialogue("chat_a", met_day, npc,
                                   dict(snap.emotion_stats or {}))
    assert meeting["lines"] == expect


def test_chat_log_includes_persuade_summary():
    _start("chat_b")
    g = mls._get_game("chat_b")
    g.persuade("value_investor", "calm", roll=1.0)   # 성공 확정(낮은 roll=성공)
    r = mls.control_game_chat_log(game_id="chat_b", npc_id="value_investor")
    assert r["status"] == "ok"
    entries = [e for d in r["days"] for e in d["entries"] if e["kind"] == "persuade"]
    assert len(entries) == 1
    assert entries[0]["direction"] == "calm"
    assert isinstance(entries[0]["accepted"], bool)


def test_chat_log_empty_for_stranger_and_missing_game():
    _start("chat_c")
    r = mls.control_game_chat_log(game_id="chat_c", npc_id="macro_whale")
    assert r["status"] == "ok" and r["days"] == []
    assert mls.control_game_chat_log(game_id="nope", npc_id="x")["status"] == "error"
