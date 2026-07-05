"""T-272a · 만날 사람 지정 — 후보가 여럿인 슬롯에서 플레이어가 클론의 선택을 덮어쓴다.

§9.2.1b의 기본(클론이 스스로 고름)은 유지하되, 사용자 결정(2026-07-05)으로
플레이어가 전날밤 미리보기에서 특정 슬롯의 대화 상대를 *지정*할 수 있다.
지정은 그날 하루만 유효(밤 정산 후 소멸 — 일일 셔플 T-248과 같은 수명),
후보에 없는 NPC는 거부(클론의 동선 밖 인물과 억지로 만나게 할 수는 없다).
"""

from __future__ import annotations

import pytest

import market_live_server as mls
from sim import clone_spec as CS
from sim.game_run import GameRun

CLONE = CS.build_clone_spec({"q_panic": 0.5})

# 일터@슬롯2 = 도움형 2명(value_investor·contrarian)이 겹치는 유일하게 안정적인
# 다후보 슬롯(T-222 선례).
WORK_SLOT = 2
WORK_PAIR = {"value_investor", "contrarian"}


def _g(run_id="t272"):
    return GameRun(CLONE, category="meme", start_price=100.0, run_id=run_id)


def _align_work(g):
    cur = next(s for s, pl in g.schedule.items() if pl == "일터")
    if cur != WORK_SLOT:
        g.avoid(cur, WORK_SLOT)


def _clear_meetings_below(g, slot, max_iter=16):
    """companion은 최소 슬롯의 만남(met[0])이라, 그 앞 만남을 회피로 치운다."""
    for _ in range(max_iter):
        mts = g.preview_day()["meetings"]
        low = [s for s in sorted(mts) if s < slot]
        if not low:
            return
        free = next(t for t in g.schedule if t not in mts and t != slot)
        g.avoid(low[0], free)
    raise AssertionError("meetings below slot could not be cleared")


def test_designate_overrides_clone_pick_in_preview():
    g = _g()
    _align_work(g)
    default = g.preview_day()["picks"][WORK_SLOT]
    other = (WORK_PAIR - {default}).pop()
    g.designate(WORK_SLOT, other)
    p = g.preview_day()
    assert p["picks"][WORK_SLOT] == other
    assert p["designated"] == {WORK_SLOT: other}


def test_designate_rejects_non_candidate():
    g = _g()
    _align_work(g)
    with pytest.raises(ValueError):
        g.designate(WORK_SLOT, "jackpot_gambler")   # 그 슬롯 후보가 아님


def test_designate_none_returns_choice_to_clone():
    g = _g()
    _align_work(g)
    default = g.preview_day()["picks"][WORK_SLOT]
    other = (WORK_PAIR - {default}).pop()
    g.designate(WORK_SLOT, other)
    g.designate(WORK_SLOT, None)                    # 지정 해제 = 클론에게 맡김
    p = g.preview_day()
    assert p["picks"][WORK_SLOT] == default
    assert p["designated"] == {}


def test_advance_day_uses_designated_companion():
    g = _g()
    _align_work(g)
    _clear_meetings_below(g, WORK_SLOT)
    default = g.preview_day()["picks"][WORK_SLOT]
    other = (WORK_PAIR - {default}).pop()
    g.designate(WORK_SLOT, other)
    snap = g.advance_day()
    assert snap.companion == other


def test_designation_expires_after_day():
    g = _g()
    _align_work(g)
    default = g.preview_day()["picks"][WORK_SLOT]
    other = (WORK_PAIR - {default}).pop()
    g.designate(WORK_SLOT, other)
    g.advance_day()
    assert g.preview_day()["designated"] == {}      # 다음 날 일과엔 이월 안 됨


def test_designation_survives_serialization_roundtrip():
    g = _g()
    _align_work(g)
    default = g.preview_day()["picks"][WORK_SLOT]
    other = (WORK_PAIR - {default}).pop()
    g.designate(WORK_SLOT, other)
    g2 = GameRun.from_doc(g.to_doc(), fate_line=g.fl)
    assert g2.preview_day()["picks"][WORK_SLOT] == other


def test_designate_endpoint():
    mls.control_game_start(mls.GameStartBody(
        game_id="t272_ep", answers={}, symbol="DOGE", start_price=100.0))
    g = mls._get_game("t272_ep")
    _align_work(g)
    default = g.preview_day()["picks"][WORK_SLOT]
    other = (WORK_PAIR - {default}).pop()
    r = mls.control_game_designate(mls.GameDesignateBody(
        game_id="t272_ep", slot=WORK_SLOT, npc_id=other))
    assert r["status"] == "ok"
    assert r["picks"][WORK_SLOT] == other   # 직접 호출이라 int 키(HTTP에선 JSON이 str화)
    bad = mls.control_game_designate(mls.GameDesignateBody(
        game_id="t272_ep", slot=WORK_SLOT, npc_id="panic_ant"))
    assert bad["status"] == "error"
