"""T-113 · §8.6.2 하루치 결정 파이프라인 — 새 시스템들의 end-to-end 조립.

결정/표현 분리(§8.6.3): [1] 자극 반영 → [2] 평상시 행동 → [3] 함정 판정 →
[4] 매매 실행 + 회계 까지는 전부 규칙 엔진(결정적·회차 재현). [5] LLM 표현은 범위 밖.
이 테스트는 모듈들이 실제로 맞물려 한 클론의 하루를 결정론으로 굴리는지 본다
(RETRO 규칙1: 배선 버그는 통합 테스트만 잡는다).
"""

from __future__ import annotations

from sim import crisis_day as CD
from sim import clone_spec as CS
from sim import clone_stats as CSt
from sim import fate_line as FL
from sim.trap_pipeline import Intervention
from sim.resistance import STRATEGY_B

FATE = FL.load_fate_line()


def _spec(panic=1.0, fomo=0.0):
    return CS.build_clone_spec({"q_panic": panic, "q_fomo": fomo})


def _stats():
    return {"급락패닉저항": 20.0, "멘탈마모저항": 50.0, "익절거부제어": 50.0,
            "과대베팅제어": 50.0, "추격매수저항": 50.0, "막차불안저항": 50.0,
            "멘탈회복": 50.0}


def test_calm_day_snapshot():
    # 횡보 카테고리(stable)는 트리거 없음 → 평온
    snap = CD.simulate_clone_day(
        clone_spec=_spec(), stats=_stats(), fate_line=FATE,
        category="stable", day=5, holding={"avg_cost": 100.0, "quantity": 1.0},
    )
    assert snap.swayed is False
    assert snap.fund_flow == ""
    assert snap.trap is None


def test_true_calm_day_leaves_all_stats_unchanged():
    # 사람 결정: 관련 함정이 없는 진짜 평온한 날엔 아무 스탯도 안 움직인다
    # (8:3:1 비대칭 희석 방지 — 회복은 오직 함정을 견뎌야만).
    before = _stats()
    snap = CD.simulate_clone_day(
        clone_spec=_spec(), stats=dict(before), fate_line=FATE,
        category="stable", day=5, holding={"avg_cost": 100.0, "quantity": 1.0},
    )
    assert snap.emotion_stats == before


def test_m1_surge_context_triggers_chase_fund_flow():
    # T-210 — 미보유 종목 급등(§8.3 M1)이 실제로 컨텍스트에 흘러 함정을 켠다.
    # stable day(가격변동 트리거 없음) + unheld_surge_pct만으로 M1 단독 유발.
    stats = _stats()
    stats["추격매수저항"] = 20.0   # 취약(우선순위 확보)
    snap = CD.simulate_clone_day(
        clone_spec=_spec(panic=0.0, fomo=1.0), stats=stats, fate_line=FATE,
        category="stable", day=5, holding={"avg_cost": 100.0, "quantity": 1.0},
        unheld_surge_pct=25.0,   # M1_SURGE_PCT=20 초과
    )
    assert snap.trap == "M1"
    assert snap.swayed is True
    assert snap.fund_flow == "to_hotter"


def test_g2_confidence_context_triggers_concentrate_fund_flow():
    # T-210 — 멘탈회복을 자신감 프록시로 재사용(§8.3 G2). 직전 매매 수익 실현 + 고자신감.
    stats = _stats()
    stats["과대베팅제어"] = 20.0   # 취약
    snap = CD.simulate_clone_day(
        clone_spec=_spec(panic=0.0, fomo=0.0), stats=stats, fate_line=FATE,
        category="stable", day=5, holding={"avg_cost": 100.0, "quantity": 1.0},
        confidence=80.0, just_realized_profit=True,
    )
    assert snap.trap == "G2"
    assert snap.swayed is True
    assert snap.fund_flow == "concentrate"


def test_m2_fgi_crowd_buying_context_triggers_hotter_fund_flow():
    # T-210b — FGI(단톡방 과열도)+군중매수 우세만으로 M2 단독 유발.
    stats = _stats()
    stats["막차불안저항"] = 20.0   # 취약
    snap = CD.simulate_clone_day(
        clone_spec=_spec(panic=0.0, fomo=1.0), stats=stats, fate_line=FATE,
        category="stable", day=5, holding={"avg_cost": 100.0, "quantity": 1.0},
        fgi=80.0, crowd_buying=True,   # M2_FGI=75 초과 + 군중매수
    )
    assert snap.trap == "M2"
    assert snap.swayed is True
    assert snap.fund_flow == "to_hotter"


def test_crash_day_sways_panicky_clone():
    # meme day27 = 실 업비트 DOGE 단일봉 −21.6% 급락(F1). 패닉형+낮은 내성+개입없음 → 휘둘림
    snap = CD.simulate_clone_day(
        clone_spec=_spec(panic=1.0), stats=_stats(), fate_line=FATE,
        category="meme", day=27, holding={"avg_cost": 100.0, "quantity": 1.0},
    )
    assert snap.trap == "F1"
    assert snap.swayed is True
    assert snap.fund_flow == "to_cash"                 # 공포 → 현금 도피(§8.3)
    # 함정에 빠지면 급락패닉저항 −8 (§11.5 비대칭). 짝인 멘탈마모저항(F2)은 안 바뀜.
    assert snap.emotion_stats["급락패닉저항"] == 12.0
    assert snap.emotion_stats["멘탈마모저항"] == 50.0


def test_good_intervention_saves_clone():
    # 같은 급락이라도 좋은 개입(B+높은 래포)이면 저항 → 안 휘둘림
    spec = CS.build_clone_spec({"q_panic": 0.0})        # F1 비약점
    stats = _stats(); stats["급락패닉저항"] = 90.0
    snap = CD.simulate_clone_day(
        clone_spec=spec, stats=stats,
        fate_line=FATE, category="meme", day=27,
        holding={"avg_cost": 100.0, "quantity": 1.0},
        intervention=Intervention(strategy=STRATEGY_B, rapport=100.0),
        roll=0.0,
    )
    assert snap.trap == "F1"
    assert snap.swayed is False
    # 견디면 +3 회복
    assert snap.emotion_stats["급락패닉저항"] == 93.0


def test_deterministic():
    args = dict(clone_spec=_spec(), stats=_stats(), fate_line=FATE,
                category="meme", day=27, holding={"avg_cost": 100.0, "quantity": 1.0})
    a = CD.simulate_clone_day(**args)
    b = CD.simulate_clone_day(**args)
    assert a == b


def test_news_shifts_emotion_not_price():
    # 뉴스는 감정만(§7.1). day1 가격은 운명선 그대로.
    from sim import news
    pool = news.load_news_pool()
    fear_news = next(n for n in pool.news if n["tone"] == "fear")
    before = FATE.day_ohlc("meme", 20)
    CD.simulate_clone_day(
        clone_spec=_spec(), stats=_stats(), fate_line=FATE, category="meme", day=27,
        holding={"avg_cost": 100.0, "quantity": 1.0}, news=fear_news,
    )
    after = FATE.day_ohlc("meme", 20)
    assert before == after  # 운명선 가격 불변
