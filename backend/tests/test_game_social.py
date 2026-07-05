"""T-208 · GameRun 교류 배선 — 1:1 권유·FGI가 진짜 공유 래포 풀을 움직이는지.

핵심 DoD: 권유 → 감정 빚기(2층) → **위기 개입 성공률에 실제 영향**(§9.2.2 "같은
래포 풀"). GameRun이 래포를 세션 상태로 지속 보유해야만 성립 — 매 호출마다
외부에서 주입되고 버려지면 "공유 풀"이 거짓이 된다.
"""

from __future__ import annotations

from sim.game_run import GameRun
from sim import clone_spec as CS
from sim.resistance import STRATEGY_B

CLONE = CS.build_clone_spec({"q_panic": 1.0, "q_fomo": 0.0})


def _g():
    return GameRun(CLONE, category="meme", start_price=100.0, run_id="soc",
                   initial_rapport=50.0)


def test_rapport_persists_on_gamerun():
    g = _g()
    assert g.rapport == 50.0


def test_persuade_with_stable_npc_raises_rapport_on_success():
    g = _g()
    before = g.rapport
    out = g.persuade("value_investor", direction="calm", roll=0.0)
    assert out["accepted"] is True
    assert g.rapport > before   # 래포가 세션에 실제로 누적됨


def test_persuasion_raises_crisis_intervention_success_next_day(monkeypatch):
    # T-249 만남 효과 중립화 — 이 테스트는 권유→개입 연동만 본다(만남이 27일간
    # 저항을 깎으면 래포 98로도 못 버티는 날이 생겨 검증 대상이 흐려짐).
    from sim import tuning as _T
    monkeypatch.setattr(_T, "MEETING_STIM_DELTA", 0.0)
    monkeypatch.setattr(_T, "MEETING_CALM_DELTA", 0.0)
    # DoD 핵심 증명: day27(F1 급락, 실 업비트 DOGE −21.6%) 전에 1:1 권유로 래포를
    # 올려두면, 같은 roll·같은 전략의 위기 개입이 실제로 더 잘 먹힌다(공유 래포 풀 §11.4.4).
    def make(persuade_n):
        g = _g()
        for _ in range(persuade_n):
            g.persuade("value_investor", direction="calm", roll=0.0)
        for _ in range(27):
            g.advance_day()
        return g

    baseline = make(0)                 # 래포 50 그대로
    persuaded = make(6)                # 6회 권유 성공 → 래포 98
    assert persuaded.rapport > baseline.rapport

    snap_base = baseline.advance_day(strategy=STRATEGY_B, roll=50.0)
    snap_high = persuaded.advance_day(strategy=STRATEGY_B, roll=50.0)  # 같은 roll
    assert snap_base.swayed is True    # 래포 50 → 못 버팀
    assert snap_high.swayed is False   # 권유로 빚은 래포 98 → 버팀


def test_fgi_post_moves_crowd_mood_and_stat():
    # T-230 — calm은 '들끓음 낮추기'가 아니라 **중립(50) 복원**: 중립에선 무이동,
    # 클론 멘탈은 톤 기준(진정=+)으로 여전히 오른다.
    g = _g()
    before_mental = g.stats["멘탈회복"]
    out = g.fgi_post(tone="calm", roll=0.0)
    assert out["crowd_mood"] == 50.0          # 중립에서 calm = 무이동
    assert g.crowd_mood == out["crowd_mood"]
    assert g.stats["멘탈회복"] > before_mental
    g.crowd_mood = 60.0
    assert g.fgi_post(tone="calm", roll=0.0)["crowd_mood"] < 60.0   # 탐욕→중립
    g.crowd_mood = 40.0
    assert g.fgi_post(tone="calm", roll=0.0)["crowd_mood"] > 40.0   # 공포→중립


def test_new_run_resets_rapport_and_crowd_mood():
    g = _g()
    g.persuade("value_investor", direction="calm", roll=0.0)
    assert g.rapport != 50.0
    g.new_run(run_id="soc2")
    assert g.rapport == 50.0
    assert g.crowd_mood == 50.0


def test_persuade_unknown_npc_rejected():
    g = _g()
    out = g.persuade("nope", direction="calm", roll=0.0)
    assert out["accepted"] is False
