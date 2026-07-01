"""T-110 · §8.5 함정 파이프라인 통합 + §8.4 확증편향 잠금 + §8.4b 격화 양날.

하루 [위기] 구간 엔진(§8.5 STEP1~6): 감지 → 정렬 → 충동직전(격앙도) → 개입 →
저항판정 → 결과/이유. 저항 실패 시 충동매매(§6.5 회계)+자금행선지(§8.3)+감정악화
+(손실 포지션)확증편향 잠금(§8.4). 격화는 대체로 독(참기형)이나 드물게 약
(끊기형: 비합리적 집착 탈출/외부 선동 차단) — 결과가 아니라 상황 구조로만 판정.
"""

from __future__ import annotations

from sim import trap_pipeline as TP
from sim.trap_pipeline import CrisisInput, Intervention
from sim.traps import CrisisContext
from sim.resistance import CloneProfile, STRATEGY_B


def _clone(**kw):
    base = dict(trap_scores={"F1": 80.0, "M1": 80.0}, self_aware=True)
    base.update(kw)
    return CloneProfile(**base)


def test_calm_day_skips():
    inp = CrisisInput(ctx=CrisisContext(), clone=_clone(), vulnerability={})
    res = TP.run_crisis(inp)
    assert res.trap is None
    assert res.stat_outcome == "calm"
    assert res.impulse_trade is False


def test_crash_with_no_help_falls():
    # F1 급락 + 낮은 내성(높은 격앙) + 개입 없음 + 나쁜 roll → 넘어감
    inp = CrisisInput(
        ctx=CrisisContext(change_pct=-18.0), clone=_clone(),
        vulnerability={"F1": 80.0}, related_resilience=10.0, roll=100.0,
    )
    res = TP.run_crisis(inp)
    assert res.trap == "F1"
    assert res.resisted is False
    assert res.impulse_trade is True
    assert res.stat_outcome == "trap"
    assert res.fund_signal[1] == ["F1", "F2"]   # 공포 → 현금 도피
    assert "→ 무시됨" in res.reason


def test_crash_with_good_intervention_resists():
    inp = CrisisInput(
        ctx=CrisisContext(change_pct=-18.0),
        clone=_clone(trap_scores={"F1": 10.0}),     # 비약점
        vulnerability={"F1": 10.0}, related_resilience=90.0,  # 낮은 격앙
        intervention=Intervention(strategy=STRATEGY_B, rapport=100.0),
        roll=0.0,
    )
    res = TP.run_crisis(inp)
    assert res.trap == "F1"
    assert res.resisted is True
    assert res.impulse_trade is False
    assert res.stat_outcome == "resist"


def test_escalation_formula():
    # 격앙도 = (100−내성)×0.6 + 자극×0.4
    inp = CrisisInput(
        ctx=CrisisContext(change_pct=-18.0), clone=_clone(),
        vulnerability={"F1": 80.0}, related_resilience=20.0, escalation_stimulus=50.0,
    )
    res = TP.run_crisis(inp)
    assert abs(res.escalation - ((100 - 20) * 0.6 + 50 * 0.4)) < 1e-9  # 48+20=68


def test_prioritize_single_shock_in_pipeline():
    # F1(단발) + G1(상태의존) 동시 → 단발 F1 선정
    inp = CrisisInput(
        ctx=CrisisContext(change_pct=-18.0, holding_profit_pct=35.0),
        clone=_clone(), vulnerability={"F1": 50.0, "G1": 99.0},
    )
    assert TP.run_crisis(inp).trap == "F1"


def test_escalation_double_edge_external_signal_is_medicine():
    # §8.4b 신호2: 외부 선동 차단 격화 → 약(끊기형). 나쁜 roll에도 저항 성공.
    inp = CrisisInput(
        ctx=CrisisContext(change_pct=-18.0), clone=_clone(),
        vulnerability={"F1": 80.0}, related_resilience=10.0, roll=100.0,
        escalation_kind="signal2_external",
    )
    res = TP.run_crisis(inp)
    assert res.escalation_effect == "약"
    assert res.resisted is True
    assert res.impulse_trade is False


def test_escalation_default_is_poison():
    inp = CrisisInput(
        ctx=CrisisContext(change_pct=-18.0), clone=_clone(),
        vulnerability={"F1": 80.0}, related_resilience=10.0, roll=100.0,
    )
    assert TP.run_crisis(inp).escalation_effect == "독"


def test_attachment_signal_needs_loss_position():
    # 신호1(비합리적 집착 탈출)은 손실 포지션일 때만 약
    held = CrisisInput(
        ctx=CrisisContext(change_pct=-18.0), clone=_clone(),
        vulnerability={"F1": 80.0}, related_resilience=10.0, roll=100.0,
        escalation_kind="signal1_attachment", holding_loss=True,
    )
    assert TP.run_crisis(held).escalation_effect == "약"
    not_held = CrisisInput(
        ctx=CrisisContext(change_pct=-18.0), clone=_clone(),
        vulnerability={"F1": 80.0}, related_resilience=10.0, roll=100.0,
        escalation_kind="signal1_attachment", holding_loss=False,
    )
    # 손실 포지션 아니면 집착 탈출이 성립 안 함 → 독
    assert TP.run_crisis(not_held).escalation_effect == "독"


def test_confirmation_bias_lock():
    # 손실 포지션 + 비관 정보 3회 연속 무시 → 확증편향 잠금 (§8.4)
    inp = CrisisInput(
        ctx=CrisisContext(change_pct=-18.0), clone=_clone(),
        vulnerability={"F1": 80.0}, related_resilience=10.0, roll=100.0,
        holding_loss=True, ignore_streak=3,
    )
    assert TP.run_crisis(inp).confirmation_locked is True
    inp2 = CrisisInput(
        ctx=CrisisContext(change_pct=-18.0), clone=_clone(),
        vulnerability={"F1": 80.0}, related_resilience=10.0, roll=100.0,
        holding_loss=True, ignore_streak=1,
    )
    assert TP.run_crisis(inp2).confirmation_locked is False


def test_fomo_trap_fund_flow():
    inp = CrisisInput(
        ctx=CrisisContext(unheld_surge_pct=25.0), clone=_clone(),
        vulnerability={"M1": 80.0}, related_resilience=10.0, roll=100.0,
    )
    res = TP.run_crisis(inp)
    assert res.trap == "M1"
    assert res.fund_signal[1] == ["M1", "M2"]   # FOMO → 더 뜨거운 종목
