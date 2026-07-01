"""T-208 · §9.2.2/§9.2.3 교류 — 1:1 권유 + FGI 단톡방 개입 (순수/결정론).

1:1 권유(§9.2.2): 위기 개입(§11.4)과 같은 문법(래포+격앙) — 단 전략 A/B/C 대신
격화/안정 방향 하나만(가볍고 빈번한 평소 관리, §9.2.2 "위기 개입과의 차이").
같은 래포 풀 공유(§11.4.4). FGI 단톡방(§9.2.3): 래포 안 통함, 톤-감정 적합으로만,
약하고 불확실(군중은 무겁게).
"""

from __future__ import annotations

from sim import social as S
from sim import tuning as T


# --- 1:1 권유 (§9.2.2) --------------------------------------------------- #
def test_persuade_success_base_at_midpoint_rapport():
    assert abs(S.persuade_success(rapport=50.0, escalation=0.0) - 50.0) < 1e-9


def test_persuade_success_rapport_raises():
    assert S.persuade_success(rapport=100.0, escalation=0.0) == 70.0  # +20


def test_persuade_success_escalation_lowers():
    assert S.persuade_success(rapport=50.0, escalation=100.0) == 0.0  # −50


def test_persuade_success_never_100pct():
    assert S.persuade_success(rapport=100.0, escalation=0.0) <= 95.0


def test_apply_persuasion_success_moves_clone_and_rapport():
    # 안정 방향 권유 성공 → 관련 스탯 완화 + 래포 상승
    out = S.apply_persuasion(direction="calm", stat_name="급락패닉저항",
                             stats={"급락패닉저항": 50.0}, rapport=80.0, roll=0.0)
    assert out["accepted"] is True
    assert out["stats"]["급락패닉저항"] > 50.0
    assert out["rapport"] > 80.0


def test_apply_persuasion_failure_no_stat_change_but_rapport_drops():
    out = S.apply_persuasion(direction="calm", stat_name="급락패닉저항",
                             stats={"급락패닉저항": 50.0}, rapport=10.0, roll=99.0)
    assert out["accepted"] is False
    assert out["stats"]["급락패닉저항"] == 50.0
    assert out["rapport"] < 10.0


def test_apply_persuasion_escalate_direction_moves_opposite():
    out = S.apply_persuasion(direction="escalate", stat_name="급락패닉저항",
                             stats={"급락패닉저항": 50.0}, rapport=80.0, roll=0.0)
    assert out["accepted"] is True
    assert out["stats"]["급락패닉저항"] < 50.0   # 격화 성공 = 내성 깎임


# --- FGI 단톡방 (§9.2.3) -------------------------------------------------- #
def test_fgi_post_weak_effect_on_crowd_and_clone():
    out = S.fgi_post(tone="calm", crowd_mood=60.0, clone_stat_value=50.0, roll=0.0)
    # calm 톤 성공 → 군중 과열↓, 클론 관련 스탯은 소폭 완화(내성 유지·소폭↑, 1:1보다 약함)
    assert out["crowd_mood"] < 60.0
    assert out["clone_stat_value"] >= 50.0
    assert out["absorbed"] is False


def test_fgi_post_rapport_independent():
    import inspect
    sig = inspect.signature(S.fgi_post)
    assert "rapport" not in sig.parameters   # §9.2.3 "래포 안 통함"


def test_fgi_post_extreme_crowd_absorbs_post():
    # 이미 극단적으로 들끓는 단톡방이면 플레이어 글은 묻힘(§9.3 폭주방지 정합)
    out = S.fgi_post(tone="calm", crowd_mood=95.0, clone_stat_value=50.0, roll=0.0)
    assert out["absorbed"] is True
    assert out["crowd_mood"] == 95.0  # 안 움직임(묻힘)


def test_fgi_post_deterministic():
    a = S.fgi_post(tone="fear_join", crowd_mood=40.0, clone_stat_value=50.0, roll=50.0)
    b = S.fgi_post(tone="fear_join", crowd_mood=40.0, clone_stat_value=50.0, roll=50.0)
    assert a == b
