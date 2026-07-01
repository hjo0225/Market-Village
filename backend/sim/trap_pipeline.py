"""§8.5 함정 파이프라인 — 하루 [위기] 구간 엔진의 심장 (순수/결정론).

트리거 발동 ≠ 함정에 빠짐. 두 단계로 분리된다(§8.5):
  STEP1 감지 → STEP2 정렬 → STEP3 충동직전(격앙도) → [입력 대기]
  STEP4 개입 → STEP5 저항판정 → STEP6 실패 시 이유 표시.

저항 = f(1층 기질 × 2층 상태 × 3층 개입)(§11.2). 실패 시: 충동매매(§6.5)+자금
행선지(§8.3)+감정악화+(손실 포지션)확증편향 잠금(§8.4). 격화는 양날(§8.4b):
대체로 독(참기형, 충동을 더함)이나 드물게 약(끊기형, 잘못된 상태를 뺌) — 끊기형은
'결과'가 아니라 '그 시점 상황 구조'로만 판정(결과론 금지).

표현(대사·독백)은 입히지 않는다 — 결정만(§8.6.3). LLM 표현 계층의 몫.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import tuning as T
from . import traps as TR
from . import resistance as RES
from .resistance import CloneProfile
from .trade import fund_destination

# 함정 그룹 → 충동매매 자금 행선지(§8.3)
_TRAP_FUND_FLOW = {
    "F1": "to_cash", "F2": "to_cash",
    "M1": "to_hotter", "M2": "to_hotter",
    "G2": "concentrate", "G1": "hold_winner",
}

# 격화가 약이 되는 끊기형 신호(§8.4b). 신호1은 손실 집착일 때만 성립.
_MEDICINE_SIGNALS = {"signal1_attachment", "signal2_external"}


@dataclass
class Intervention:
    strategy: str
    rapport: float = 50.0


@dataclass
class CrisisInput:
    ctx: TR.CrisisContext
    clone: CloneProfile
    vulnerability: dict = field(default_factory=dict)
    related_resilience: float = 50.0       # 선정 함정 관련 내성(2층 상태)
    escalation_stimulus: float = 0.0       # 당일 자극
    intervention: Intervention | None = None
    roll: float = 100.0                    # 결정론 판정용 [0,100] (roll < 성공률 → 저항)
    holding_loss: bool = False             # 손실 포지션 보유 중인가
    ignore_streak: int = 0                 # 비관 정보 연속 무시 횟수
    escalation_kind: str | None = None     # 상황 구조상 끊기형 신호(있으면)


@dataclass
class CrisisResult:
    triggered: list[str]
    trap: str | None
    escalation: float
    intervened: bool
    success_prob: float
    resisted: bool
    impulse_trade: bool
    fund_signal: tuple | None
    stat_outcome: str            # "calm" / "resist" / "trap"
    confirmation_locked: bool
    escalation_effect: str       # "독" / "약" / "중립"
    reason: str


def _escalation(related_resilience: float, stimulus: float) -> float:
    # §11.4.3 ③: (100−관련내성)×0.6 + 당일자극×0.4
    raw = (100.0 - related_resilience) * T.ESCALATION_RESILIENCE_W + stimulus * T.ESCALATION_STIMULUS_W
    return T.clamp(raw, 0.0, 100.0)


def _medicine(kind: str | None, holding_loss: bool) -> bool:
    """끊기형(약) 성립 여부 — 상황 구조로만 판정(결과론 금지 §8.4b)."""
    if kind == "signal2_external":
        return True                       # 외부 선동 차단은 항상 성립
    if kind == "signal1_attachment":
        return holding_loss               # 비합리적 집착 탈출은 손실 포지션일 때만
    return False


def run_crisis(inp: CrisisInput) -> CrisisResult:
    # STEP1 감지
    triggered = TR.detect_triggers(inp.ctx)
    if not triggered:
        # 평온한 날 — 위기 페이즈 SKIP (§8.5 STEP2)
        return CrisisResult(
            triggered=[], trap=None, escalation=0.0, intervened=False,
            success_prob=0.0, resisted=True, impulse_trade=False, fund_signal=None,
            stat_outcome="calm", confirmation_locked=False,
            escalation_effect="중립", reason="평온한 날",
        )

    # STEP2 정렬 — 오늘의 위기 1개
    trap_id = TR.prioritize(triggered, inp.vulnerability)
    trap = TR.get_trap(trap_id)

    # STEP3 충동 직전 — 격앙도 산출
    escalation = _escalation(inp.related_resilience, inp.escalation_stimulus)

    # STEP4 개입 → 저항 판정용 성공률
    if inp.intervention is not None:
        success_prob = RES.intervention_success(
            inp.intervention.rapport, inp.intervention.strategy,
            inp.clone, trap, escalation,
        )
        intervened = True
    else:
        # 개입 없음 — 자력 저항 베이스라인(래포 중립·전략 무관)
        success_prob = RES.intervention_success(
            T.RAPPORT_MID, RES.STRATEGY_B, inp.clone, trap, escalation,
        )
        intervened = False

    # STEP5 저항 판정 + §8.4b 격화 양날
    is_medicine = _medicine(inp.escalation_kind, inp.holding_loss)
    escalation_effect = "약" if is_medicine else ("독" if inp.escalation_kind or escalation > 0 else "중립")
    if is_medicine:
        resisted = True                   # 끊기형 격화가 잘못된 상태를 제거 → 저항
    else:
        resisted = inp.roll < success_prob

    # STEP6 결과 + 이유
    if resisted:
        return CrisisResult(
            triggered=sorted(triggered), trap=trap_id, escalation=escalation,
            intervened=intervened, success_prob=success_prob, resisted=True,
            impulse_trade=False, fund_signal=None, stat_outcome="resist",
            confirmation_locked=_locked(inp), escalation_effect=escalation_effect,
            reason="저항 성공",
        )

    # 넘어감 — 충동매매 + 자금 행선지(§8.3) + 확증편향 잠금(§8.4)
    flow = _TRAP_FUND_FLOW.get(trap_id, "")
    fund_signal = fund_destination(flow)
    reason = RES.failure_reason(
        inp.intervention.rapport if inp.intervention else T.RAPPORT_MID,
        inp.intervention.strategy if inp.intervention else RES.STRATEGY_B,
        inp.clone, trap, escalation,
    )
    return CrisisResult(
        triggered=sorted(triggered), trap=trap_id, escalation=escalation,
        intervened=intervened, success_prob=success_prob, resisted=False,
        impulse_trade=True, fund_signal=fund_signal, stat_outcome="trap",
        confirmation_locked=_locked(inp), escalation_effect=escalation_effect,
        reason=reason,
    )


def _locked(inp: CrisisInput) -> bool:
    """§8.4 — 손실 포지션 보유 중 비관 정보 N회 연속 무시 → 확증편향 잠금."""
    return inp.holding_loss and inp.ignore_streak >= T.CONFIRMATION_BIAS_IGNORE_STREAK
