"""§13 30일 전체 회차 루프 — crisis_day를 한 회차로 threading (순수/결정론).

거울은 한 판 안이 아니라 회차 간 비교에서 나온다(기둥2). 이 오케스트레이터는 고정
운명선(같은 시험지) 위에서 30일을 굴려 한 회차를 완주하고, 매 라운드 가격을 D-B
하이브리드(운명선 90% 고정 + 출렁임 10%)로 매긴다. 포트폴리오(평단·현금·실현손익)를
일별로 threading해 회차 끝의 수익률을 낸다.

기존 엔진 라운드 루프(engine.py, reverie 모델)는 건드리지 않는다 — 이건 PRD 30일
거울 루프의 별도 경로다(수술하듯).
"""

from __future__ import annotations

from .crisis_day import simulate_clone_day
from .clone_spec import CloneSpec
from .clone_stats import MENTAL
from .fate_line import CATEGORIES, FateLine, category_for_symbol, hybrid_price, load_fate_line
from .result_card import evaluate
from .runs import RunStore, RunSummary
from . import tuning as T

_DEFAULT_STATS = {
    "급락패닉저항": 50.0, "멘탈마모저항": 50.0,
    "익절거부제어": 50.0, "과대베팅제어": 50.0,
    "추격매수저항": 50.0, "막차불안저항": 50.0,
    "멘탈회복": 50.0,
}


def apply_fund_flow(fund_flow, *, avg_cost, quantity, cash, positions,
                    price_today, surge_category=None, surge_price=None):
    """§8.3 충동매매 자금 행선지 → 포트폴리오 실제 이동(순수). 미정의 flow는 무변화.

    to_cash/to_stable(F1/F2 공포도피) = 전량 매도. to_hotter(M1/M2 추격) = 보유
    현금 일부를 급등 미보유 종목에 새로 태움. concentrate(G2 몰빵) = 보유 현금
    일부로 기존 포지션을 더 사(가중평균 평단 갱신). 비율은 tuning.py 상수.
    """
    positions = dict(positions)
    realized = 0.0
    if fund_flow in ("to_cash", "to_stable") and quantity > 0:
        realized = (price_today - avg_cost) * quantity
        cash += quantity * price_today
        quantity = 0.0
    elif fund_flow == "to_hotter" and surge_category and surge_price and cash > 0:
        chase_cash = cash * T.CHASE_FRACTION
        prev = positions.get(surge_category, {"avg_cost": surge_price, "quantity": 0.0})
        new_qty = prev["quantity"] + chase_cash / surge_price
        positions[surge_category] = {"avg_cost": surge_price, "quantity": new_qty}
        cash -= chase_cash
    elif fund_flow == "concentrate" and cash > 0 and price_today:
        add_cash = cash * T.CONCENTRATE_FRACTION
        add_qty = add_cash / price_today
        new_qty = quantity + add_qty
        if new_qty:
            avg_cost = ((avg_cost * quantity) + (price_today * add_qty)) / new_qty
        quantity = new_qty
        cash -= add_cash
    return {"avg_cost": avg_cost, "quantity": quantity, "cash": cash,
            "positions": positions, "realized": realized}


def step_day(clone_spec, stats, fate_line, category, day, start_price, holding, plan,
            *, other_categories=()):
    """하루치 코어(§12.4 한 칸) — 가격(D-B) → crisis_day 결정 → 포트폴리오 threading.

    holding = {avg_cost, quantity, cash}. 반환 (snap, new_holding, price_today) 또는
    운명선 미스 시 None. run_loop(batch)와 GameRun(step-able)이 **공유**한다(DRY).
    """
    fate_today = fate_line.day_ohlc(category, day)
    if fate_today is None:
        return None
    price_today = hybrid_price(start_price, fate_today[3], plan.get("agent_pressure", 0.0))
    avg_cost = holding["avg_cost"]
    quantity = holding["quantity"]
    cash = holding["cash"]
    positions = dict(holding.get("positions", {}))

    # §8.3 M1 — 미보유(다자산) 종목 중 오늘 가장 급등한 것. 없으면 0(하위호환).
    unheld_surge_pct, surge_category, surge_price = 0.0, None, None
    for oc in other_categories:
        cr = fate_line.change_rate(oc, day)
        if cr > unheld_surge_pct:
            oc_fate = fate_line.day_ohlc(oc, day)
            if oc_fate is not None:
                unheld_surge_pct, surge_category, surge_price = cr, oc, oc_fate[3]

    confidence = stats.get(MENTAL, 50.0)   # §8.3 G2 — 멘탈회복을 자신감 프록시로 재사용
    just_realized_profit = plan.get("prev_realized_pnl", 0.0) > 0.0
    # §8.3 M2 — FGI 단톡방 과열도(crowd_mood, §9.2.3)를 fgi/crowd_buying 프록시로
    # 재사용. 새 상태를 안 만든다(T-210b, 이미 있는 신호를 잇는다).
    crowd_mood = plan.get("crowd_mood", 50.0)
    fgi = crowd_mood
    crowd_buying = crowd_mood > 50.0

    snap = simulate_clone_day(
        clone_spec=clone_spec, stats=stats, fate_line=fate_line, category=category, day=day,
        holding={"avg_cost": avg_cost, "quantity": quantity, "cash": cash},
        news=plan.get("news"), intervention=plan.get("intervention"),
        roll=plan.get("roll", 100.0),
        unheld_surge_pct=unheld_surge_pct,
        confidence=confidence, just_realized_profit=just_realized_profit,
        fgi=fgi, crowd_buying=crowd_buying,
    )

    flow = apply_fund_flow(
        snap.fund_flow if snap.swayed else "", avg_cost=avg_cost, quantity=quantity,
        cash=cash, positions=positions, price_today=price_today,
        surge_category=surge_category, surge_price=surge_price,
    )
    avg_cost, quantity, cash, positions, realized = (
        flow["avg_cost"], flow["quantity"], flow["cash"], flow["positions"], flow["realized"])

    secondary_value = sum(
        p["quantity"] * (fate_line.day_ohlc(c, day) or (0, 0, 0, avg_cost))[3]
        for c, p in positions.items()
    )
    total = cash + quantity * price_today + secondary_value
    snap.realized_pnl = round(realized, 4)
    snap.total_asset = round(total, 4)
    snap.cash = round(cash, 4)
    snap.holdings = {category: {"quantity": quantity, "avg_cost": avg_cost},
                     **{c: dict(p) for c, p in positions.items()}}
    new_holding = {"avg_cost": avg_cost, "quantity": quantity, "cash": cash,
                   "positions": positions}
    return snap, new_holding, price_today


def simulate_run(
    store: RunStore,
    run_id: str,
    clone_spec: CloneSpec,
    *,
    category: str,
    start_price: float,
    days: int = 30,
    start_stats: dict | None = None,
    start_quantity: float = 1.0,
    start_cash: float = 0.0,
    day_plan: dict | None = None,
    fate_line: FateLine | None = None,
    initial_rapport: float = 50.0,
    other_categories: tuple[str, ...] | None = None,
) -> RunSummary:
    """한 회차(30일)를 굴려 RunSummary 반환 + 일별 스냅샷을 store에 기록.

    other_categories(§8.3 T-210) — 보유하지 않은 감시 종목들. 여기서 급등이 나면
    M1(추격매수)이, 직전 실현손익이 양수+높은 자신감(멘탈회복)이면 G2(몰빵)가
    실제로 발동해 포트폴리오를 움직인다. 기본값은 나머지 전 카테고리(GameRun과
    동일 정책 — 명시로 좁히면 배치·스텝 두 경로가 정확히 같은 입력이 된다).
    """
    fl = fate_line or load_fate_line()
    resolved_other = (other_categories if other_categories is not None
                      else tuple(c for c in CATEGORIES if c != category))
    store.start_run(run_id, initial_rapport)
    stats = dict(start_stats or _DEFAULT_STATS)
    plans = day_plan or {}

    holding = {"avg_cost": start_price, "quantity": start_quantity, "cash": start_cash}
    initial_total = start_cash + start_quantity * start_price

    last_price = start_price
    final_total = initial_total
    prev_realized_pnl = 0.0
    for day in range(days):
        plan = dict(plans.get(day, {}))
        plan.setdefault("prev_realized_pnl", prev_realized_pnl)
        res = step_day(clone_spec, stats, fl, category, day, start_price, holding, plan,
                       other_categories=resolved_other)
        if res is None:
            continue
        snap, holding, last_price = res
        stats = snap.emotion_stats
        prev_realized_pnl = snap.realized_pnl
        final_total = snap.total_asset
        store.record_snapshot(run_id, snap)

    return_pct = ((final_total - initial_total) / initial_total * 100.0) if initial_total else 0.0
    control = sum(stats.values()) / len(stats) if stats else 50.0

    summary = RunSummary(
        run_id=run_id,
        return_pct=round(return_pct, 2),
        emotion_overall=stats,
        grade=evaluate(return_pct, control),
        trap_counts={},
        clone_spec_snapshot=dict(clone_spec.trap_scores),
    )
    store.record_summary(summary)
    return summary


def run_for_symbol(store: RunStore, run_id: str, clone_spec: CloneSpec, *,
                   symbol: str, start_price: float, **kw) -> RunSummary:
    """심볼로 카테고리를 자동 매핑해 회차를 돌리는 편의 래퍼."""
    return simulate_run(store, run_id, clone_spec,
                        category=category_for_symbol(symbol),
                        start_price=start_price, **kw)
