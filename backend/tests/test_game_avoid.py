"""T-202 · 전날밤 일과 미리보기 + 회피 (§9.2.1).

내일 일과(8슬롯)와 변경 안 하면 마주칠 NPC를 보여주고, 일과 항목 하나의 순서만
바꿔(회피) 마주칠 NPC를 달라지게 한다. GameRun 메서드 + 엔드포인트.
"""

from __future__ import annotations

import market_live_server as mls
from sim.game_run import GameRun
from sim import clone_spec as CS

CLONE = CS.build_clone_spec({"q_panic": 0.5})


def _g():
    return GameRun(CLONE, category="meme", start_price=100.0, run_id="av")


def _align(g, place, slot):
    """T-248(일일 셔플) — 만남을 결정론으로 구성하기 위한 회피 정렬 헬퍼."""
    cur = next(s for s, pl in g.schedule.items() if pl == place)
    if cur != slot:
        g.avoid(cur, slot)


def test_preview_returns_schedule_and_meetings():
    g = _g()
    _align(g, "광장", 3)               # 만식(음모론)의 {3: 광장}과 겹치게 정렬
    p = g.preview_day()
    assert len(p["slots"]) == 8
    assert len(p["schedule"]) == 8
    assert 3 in p["meetings"]


def test_avoid_changes_meetings():
    g = _g()
    _align(g, "광장", 3)
    assert 3 in g.preview_day()["meetings"]    # 회피 전: 슬롯3 광장 만남 존재
    other = next(s for s in g.schedule if s != 3 and g.schedule[s] != "광장")
    after = g.avoid(3, other)                    # 동선 틀기
    assert 3 not in after                        # 회피 성공: 슬롯3 만남 사라짐
    # 활동 집합은 불변(통제변인 §12.2)
    assert sorted(g.schedule.values()) == sorted(_g().schedule.values())


# --- 엔드포인트 (핸들러 직접호출) --------------------------------------- #
def test_preview_and_avoid_endpoints():
    mls.control_game_start(mls.GameStartBody(game_id="av_ep", answers={}, symbol="DOGE"))
    g = mls._get_game("av_ep")
    _align(g, "광장", 3)               # 결정론 정렬 후 엔드포인트 계약 검증
    p = mls.control_game_preview(game_id="av_ep")
    assert p["status"] == "ok" and len(p["slots"]) == 8 and 3 in p["meetings"]
    other = next(s for s in g.schedule if s != 3 and g.schedule[s] != "광장")
    r = mls.control_game_avoid(mls.GameAvoidBody(game_id="av_ep", slot_a=3, slot_b=other))
    assert r["status"] == "ok" and 3 not in r["meetings"]


def test_avoid_missing_game():
    assert mls.control_game_preview(game_id="nope")["status"] == "error"
