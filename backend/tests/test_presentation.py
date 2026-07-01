"""T-206 · 표현 계층 — 엔진 결정 → 연출명령 + 대사 (§12.0/§8.6.3).

결정(수치)은 이미 끝났다. 표현은 그 결정을 *서술*만 한다(결정 역전 없음 §8.6.3).
연출명령(emote/trade)은 맵이 연기하고, 대사는 클론 합리화 언어(§5.1 3층)에서 나와
거울 모먼트가 된다. 속마음(독백)은 결정적 순간에만 열린다(§12.0b). 기본은 오프라인
결정론 템플릿, LLM은 키 있을 때 표현만 교체(opt-in, 수치 무관).
"""

from __future__ import annotations

import market_live_server as mls
from sim import presentation as P
from sim import clone_spec as CS
from sim.runs import DailySnapshot

SPEC = CS.build_clone_spec({"q_panic": 1.0})


def _snap(trap=None, swayed=False, fund_flow=""):
    return DailySnapshot(day=20, swayed=swayed, fund_flow=fund_flow, trap=trap,
                         emotion_stats={"공포내성": 12.0})


def test_trap_day_uses_rationalization():
    sc = P.narrate(_snap(trap="F1", swayed=True, fund_flow="to_cash"), SPEC)
    assert sc["dialogue"] in SPEC.rationalization["F1"]   # 합리화 언어 = 거울
    assert sc["monologue_open"] is True                   # 위기 = 속마음 열림
    assert any("trade" in c for c in sc["commands"])       # 충동 매매 연출


def test_resisted_day_line():
    sc = P.narrate(_snap(trap="F1", swayed=False), SPEC)
    assert sc["monologue_open"] is True
    assert "버텼" in sc["dialogue"] or sc["dialogue"]


def test_calm_day_closed_monologue():
    sc = P.narrate(_snap(), SPEC)
    assert sc["monologue_open"] is False                  # 평소 = 속마음 숨김
    assert any("emote" in c for c in sc["commands"])


def test_bundle_of_two_emits_trade_command_per_swayed_category():
    # T-216 — 번들 2개 이상이면 snap.fund_flow는 비지만, 번들 안 각 swayed
    # 항목마다 개별 trade 연출 명령이 나와야 한다(회귀: 예전엔 아예 안 나왔음).
    snap = DailySnapshot(
        day=5, swayed=True, fund_flow="", trap="F1",
        emotion_stats={"급락패닉저항": 12.0},
        bundle=[
            {"category": "large_stable", "trap": "F1", "trap_name": "급락 패닉",
             "resisted": False, "reason": "", "fund_flow": "to_cash", "realized_pnl": -5.0},
            {"category": "meme", "trap": "F1", "trap_name": "급락 패닉",
             "resisted": True, "reason": "", "fund_flow": "", "realized_pnl": 0.0},
        ],
    )
    sc = P.narrate(snap, SPEC)
    trade_cmds = [c for c in sc["commands"] if "trade" in c]
    assert len(trade_cmds) == 1                     # meme은 resisted라 연출 없음
    assert trade_cmds[0]["category"] == "large_stable"


def test_deterministic():
    s = _snap(trap="F1", swayed=True, fund_flow="to_cash")
    assert P.narrate(s, SPEC) == P.narrate(s, SPEC)


def test_scene_endpoint_after_advance():
    mls.control_game_start(mls.GameStartBody(game_id="sc", answers={"q_panic": 1.0}, symbol="DOGE"))
    mls.control_game_advance(mls.GameAdvanceBody(game_id="sc"))
    r = mls.control_game_scene(game_id="sc")
    assert r["status"] == "ok"
    assert "dialogue" in r["scene"] and "commands" in r["scene"]


def test_scene_no_game():
    assert mls.control_game_scene(game_id="nope")["status"] == "error"
