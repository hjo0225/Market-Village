"""§8.6.2 하루치 결정 파이프라인 — 새 시스템들을 한 클론의 하루로 조립.

결정/표현 분리(§8.6.3): 여기 [1]~[4]는 전부 규칙 엔진(결정적·회차 재현 가능).
[5] LLM 표현(대사·독백)은 범위 밖 — 이 오케스트레이터는 수치 결정만 낸다.

  [1] 자극 반영   : 뉴스 톤 → 감정 자극(§7.1 가격 무관)
  [2] 컨텍스트    : 운명선 change_rate + 보유 평가익 → CrisisContext
  [3] 함정 판정   : trap_pipeline.run_crisis (감지→정렬→개입→저항)
  [4] 회계+스탯   : 실현손익(§6.5) + 4스탯 자동증감(§11.5) → DailySnapshot
"""

from __future__ import annotations

from . import clone_stats as CSt
from . import news as NEWS
from . import traps as TR
from .clone_spec import CloneSpec
from .fate_line import FateLine
from .resistance import CloneProfile
from .runs import DailySnapshot
from .trap_pipeline import CrisisInput, Intervention, run_crisis


def _profile(spec: CloneSpec) -> CloneProfile:
    """클론 스펙(§5.5) → 저항 판정용 프로필. 성향 플래그는 인터뷰 확장 시 채움."""
    return CloneProfile(trap_scores=dict(spec.trap_scores), weakness_threshold=50.0)


def simulate_clone_day(
    *,
    clone_spec: CloneSpec,
    stats: dict[str, float],
    fate_line: FateLine,
    category: str,
    day: int,
    holding: dict,
    news: dict | None = None,
    news_reverse: bool = False,
    intervention: Intervention | None = None,
    roll: float = 100.0,
    unheld_surge_pct: float = 0.0,
    confidence: float = 0.0,
    just_realized_profit: bool = False,
    fgi: float = 0.0,
    crowd_buying: bool = False,
    ignore_streak: int = 0,
    escalation_kind: str | None = None,
    companion: str = "",
) -> DailySnapshot:
    """한 클론의 하루 결정을 §8.6.2 순서로 굴려 DailySnapshot 반환(결정론)."""
    stats = dict(stats)
    avg_cost = float(holding.get("avg_cost", 0.0))
    qty = float(holding.get("quantity", 0.0))

    # [1] 자극 반영 — 뉴스 톤 → 감정 자극(가격 무관 §7.1). 격앙 자극으로 환산.
    escalation_stimulus = 0.0
    if news is not None:
        tone = news.get("tone", "fear")
        coef = clone_spec.news_tone_coef.get(tone, 1.0)
        delta = NEWS.apply_news_to_clone(news, coef=coef, reverse=news_reverse)
        escalation_stimulus = abs(delta.fear_delta) + abs(delta.greed_delta)

    # [2] 컨텍스트 — 운명선(고정) + 보유 평가익
    ohlc = fate_line.day_ohlc(category, day)
    close = ohlc[3] if ohlc else avg_cost
    change_pct = fate_line.change_rate(category, day)
    profit_pct = ((close - avg_cost) / avg_cost * 100.0) if (avg_cost and qty > 0) else 0.0
    holding_loss = profit_pct < 0.0

    ctx = TR.CrisisContext(
        change_pct=change_pct,
        holding_profit_pct=profit_pct,
        unheld_surge_pct=unheld_surge_pct,
        confidence=confidence,
        just_realized_profit=just_realized_profit,
        fgi=fgi,
        crowd_buying=crowd_buying,
    )

    # 선정될 함정의 '관련 내성'을 2층 상태로 미리 집어 격앙도에 반영
    triggered = TR.detect_triggers(ctx)
    related_resilience = 50.0
    if triggered:
        pre_trap = TR.prioritize(triggered, clone_spec.trap_scores)
        stat_name = CSt.stat_for_trap(pre_trap)
        if stat_name in stats:
            related_resilience = stats[stat_name]

    # [3] 함정 판정
    res = run_crisis(CrisisInput(
        ctx=ctx, clone=_profile(clone_spec), vulnerability=clone_spec.trap_scores,
        related_resilience=related_resilience, escalation_stimulus=escalation_stimulus,
        intervention=intervention, roll=roll, holding_loss=holding_loss,
        ignore_streak=ignore_streak, escalation_kind=escalation_kind,
    ))

    # [4] 회계 + 스탯 자동증감. 진짜 평온한 날(트리거 자체 없음)엔 아무 것도 안
    # 움직인다 — "관련" 내성이 특정 함정에 묶여 있으므로(§11.5.1), 관련 함정이
    # 없는 날 전체를 건드리면 8:3:1 비대칭(무너지는 게임 §10)이 희석된다.
    if res.trap is not None:
        CSt.apply_outcome(stats, res.trap, res.stat_outcome)

    # 충동 매도(공포 도피)면 실현손익 확정(§6.5.4). 그 외엔 0(이동 없음/매수).
    realized_pnl = 0.0
    fund_flow = ""
    if res.impulse_trade and res.fund_signal is not None:
        fund_flow = next(
            (k for k, v in _FLOW_FROM_SIGNAL.items() if v == res.fund_signal[1]), ""
        )
        if fund_flow in ("to_cash", "to_stable") and qty > 0:
            realized_pnl = (close - avg_cost) * qty

    total_asset = (holding.get("cash", 0.0) if isinstance(holding, dict) else 0.0) + close * qty

    return DailySnapshot(
        day=day,
        holdings={category: {"quantity": qty, "avg_cost": avg_cost}},
        cash=float(holding.get("cash", 0.0)),
        total_asset=total_asset,
        realized_pnl=realized_pnl,
        trades=[],
        emotion_stats=stats,
        swayed=res.impulse_trade,
        fund_flow=fund_flow,
        companion=companion,
        trap=res.trap,
    )


# fund_destination 신호(함정 ids) → flow 키 역매핑
_FLOW_FROM_SIGNAL = {
    "to_cash": ["F1", "F2"],
    "to_hotter": ["M1", "M2"],
    "concentrate": ["G2"],
    "hold_winner": ["G1"],
}
