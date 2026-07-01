"""T-216 · §8.5 위기 이벤트 다중종목 번들링 (D4).

분산 보유(T-215) 시 같은 날 2개 이상 종목이 트리거 조건을 만족하면, 기존
"하루 1위기" 페이싱은 유지한 채 하나의 위기 이벤트로 묶는다(PRD_MULTI_ASSET_
PORTFOLIO.md D4). 전략(A/B/C)은 번들 내 각 함정에 개별 적용 — 종목별로 성공/
실패가 갈릴 수 있다.

실제 시장 데이터엔 2개 카테고리가 같은 날 동시에 -15% 이상 크래시하는 날이
없어서(조사 완료), 번들링 로직 자체는 통제된 가짜 FateLine으로 테스트한다
(crisis_day.py는 fate_line을 주입받는 순수 오케스트레이션이라 이 자체가
"실제 데이터로 시장을 만든다"는 원칙5의 대상이 아님 — market_seed.json
생성만 그 대상). 단일종목 회귀는 실제 데이터로 별도 검증(test_game_run.py).
"""

from __future__ import annotations

from sim import crisis_day as CD
from sim import clone_spec as CS
from sim.fate_line import FateLine
from sim.trap_pipeline import Intervention
from sim.resistance import STRATEGY_B


def _stats():
    return {"급락패닉저항": 20.0, "멘탈마모저항": 50.0, "익절거부제어": 50.0,
            "과대베팅제어": 50.0, "추격매수저항": 50.0, "막차불안저항": 50.0,
            "멘탈회복": 50.0}


def _spec(panic=1.0, fomo=0.0):
    return CS.build_clone_spec({"q_panic": panic, "q_fomo": fomo})


def _fate(series: dict[str, list[tuple]]) -> FateLine:
    return FateLine({"days": max(len(v) for v in series.values()),
                     "categories": {c: {"ohlc": v} for c, v in series.items()}})


# day0: 전 카테고리 종가 100. day1: large_stable·meme -20%(F1), mid_alt·stable 횡보.
_TWO_CRASH = _fate({
    "large_stable": [(100, 100, 100, 100), (80, 82, 78, 80)],
    "mid_alt":      [(100, 100, 100, 100), (100, 101, 99, 100)],
    "meme":         [(100, 100, 100, 100), (80, 82, 78, 80)],
    "stable":       [(100, 100, 100, 100), (100, 100, 100, 100)],
})

# day1: large_stable만 -20%(F1), 나머지 횡보 — 단일 트리거 회귀 확인용.
_ONE_CRASH = _fate({
    "large_stable": [(100, 100, 100, 100), (80, 82, 78, 80)],
    "mid_alt":      [(100, 100, 100, 100), (100, 101, 99, 100)],
    "meme":         [(100, 100, 100, 100), (100, 101, 99, 100)],
    "stable":       [(100, 100, 100, 100), (100, 100, 100, 100)],
})

_HOLDING_DIVERSIFIED = {
    "avg_cost": 100.0, "quantity": 0.4, "cash": 0.0,
    "positions": {
        "mid_alt": {"avg_cost": 100.0, "quantity": 0.3},
        "meme": {"avg_cost": 100.0, "quantity": 0.2},
        "stable": {"avg_cost": 100.0, "quantity": 0.1},
    },
}


def test_calm_day_with_positions_returns_empty_bundle():
    snap = CD.simulate_clone_day_multi(
        clone_spec=_spec(), stats=_stats(), fate_line=_ONE_CRASH,
        category="mid_alt", day=1, holding={
            "avg_cost": 100.0, "quantity": 0.3, "cash": 0.0,
            "positions": {"stable": {"avg_cost": 100.0, "quantity": 0.1}},
        },
    )
    assert snap.trap is None
    assert snap.bundle == []
    assert snap.swayed is False


def test_single_trigger_matches_legacy_single_category_path():
    # 번들 크기 1(회귀 없음 확인) — 기존 simulate_clone_day와 동일 결과.
    legacy = CD.simulate_clone_day(
        clone_spec=_spec(), stats=_stats(), fate_line=_ONE_CRASH,
        category="large_stable", day=1, holding={"avg_cost": 100.0, "quantity": 0.4},
        intervention=Intervention(STRATEGY_B, 50.0), roll=10.0,
    )
    bundled = CD.simulate_clone_day_multi(
        clone_spec=_spec(), stats=_stats(), fate_line=_ONE_CRASH,
        category="large_stable", day=1, holding={
            "avg_cost": 100.0, "quantity": 0.4, "cash": 0.0,
            "positions": {"mid_alt": {"avg_cost": 100.0, "quantity": 0.3}},
        },
        intervention=Intervention(STRATEGY_B, 50.0), roll=10.0,
    )
    assert len(bundled.bundle) == 1
    assert bundled.trap == legacy.trap == "F1"
    assert bundled.swayed == legacy.swayed
    assert bundled.emotion_stats["급락패닉저항"] == legacy.emotion_stats["급락패닉저항"]


def test_secondary_only_trigger_leaves_primary_untouched():
    snap = CD.simulate_clone_day_multi(
        clone_spec=_spec(), stats=_stats(), fate_line=_ONE_CRASH,
        category="mid_alt", day=1, holding={
            "avg_cost": 100.0, "quantity": 0.3, "cash": 0.0,
            "positions": {"large_stable": {"avg_cost": 100.0, "quantity": 0.4},
                         "stable": {"avg_cost": 100.0, "quantity": 0.1}},
        },
        intervention=Intervention(STRATEGY_B, 50.0), roll=10.0,
    )
    assert len(snap.bundle) == 1
    assert snap.bundle[0]["category"] == "large_stable"
    assert snap.bundle[0]["trap"] == "F1"
    # 주력(mid_alt)은 트리거 조건을 안 만족했으니 안 건드림.
    assert snap.holdings["mid_alt"]["quantity"] == 0.3


def test_bundles_two_simultaneous_triggers_with_independent_outcomes():
    stats = _stats()
    stats["급락패닉저항"] = 90.0    # 강한 내성 — 저항 성공 쪽으로
    snap = CD.simulate_clone_day_multi(
        clone_spec=_spec(), stats=stats, fate_line=_TWO_CRASH,
        category="large_stable", day=1, holding=_HOLDING_DIVERSIFIED,
        intervention=Intervention(STRATEGY_B, 90.0), roll=50.0,
    )
    cats_in_bundle = {b["category"] for b in snap.bundle}
    assert cats_in_bundle == {"large_stable", "meme"}
    assert all(b["trap"] == "F1" for b in snap.bundle)
    # 번들 안 각 항목이 독립 reason/결과를 갖는다(같은 함정이라도 종목별 별개 판정).
    assert len({id(b) for b in snap.bundle}) == 2


def test_bundle_swayed_categories_sell_to_cash_independently():
    # roll을 크게 줘서 확실히 저항 실패(swayed)로 몰아 자금 이동까지 검증.
    stats = _stats()
    stats["급락패닉저항"] = 5.0     # 매우 취약 — 저항 실패 쪽으로
    snap = CD.simulate_clone_day_multi(
        clone_spec=_spec(), stats=stats, fate_line=_TWO_CRASH,
        category="large_stable", day=1, holding=_HOLDING_DIVERSIFIED,
        intervention=None, roll=99.0,
    )
    swayed_cats = {b["category"] for b in snap.bundle if not b["resisted"]}
    assert swayed_cats  # 최소 하나는 넘어감
    for cat in swayed_cats:
        if cat == "large_stable":
            assert snap.holdings["large_stable"]["quantity"] == 0.0
        else:
            assert snap.holdings[cat]["quantity"] == 0.0
    assert snap.cash > 0.0
    assert snap.realized_pnl < 0.0   # -20% 크래시 후 손절 → 손실 확정
