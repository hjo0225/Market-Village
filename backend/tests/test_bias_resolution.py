"""T-55 (F4): 3액션 편향 해상도 실측.

리스크(T-53): 6선택지→3액션이 편향 표본을 얇게 만드나? 실 운명선(고정)에서
20일 플레이 시 5축(over/panic/loss/fomo/disp) 전부 opportunity n≥3인지 실측.
opportunity는 선택과 무관(매일 제시된 3액션 bias_tags의 union) — 'hold'만 눌러도
그날의 전체 기회가 적립된다.
"""
from sim.emo_api import _build_market
from sim.emo_game import EmoGameRun

ANSWERS = {"q_panic": 0.5, "q_fomo": 0.5, "q_rumor": 0.5, "q_check": 0.5}
BIAS_AXES = ("over", "panic", "loss", "fomo", "disp")


def _opportunities(days: int) -> dict[str, int]:
    events, cat_returns = _build_market(seed=1, days=days)
    run = EmoGameRun.new(ANSWERS, events, cat_returns, seed=1)
    while not run.is_over:
        run.choose("hold")   # 선택 무관 — union opportunity만 본다
    return {ax: run.bias_tally.get(ax, {}).get("opportunities", 0) for ax in BIAS_AXES}


def test_20day_all_five_bias_axes_have_min_sample():
    # DoD: 20일 실측 — 5축 전부 opportunity n≥3(리포트 노출 임계 BIAS_MIN_SAMPLE=3).
    opp = _opportunities(20)
    for ax in BIAS_AXES:
        assert opp[ax] >= 3, f"{ax} opportunity={opp[ax]} < 3 (20일 실측 {opp})"


def test_disposition_effect_axis_measurable_over_20_days():
    # T-53 리스크의 핵심: disp(처분효과)가 급등 매도(익절)로 부활했는지 — 20일 n≥3.
    assert _opportunities(20)["disp"] >= 3


def test_report_distribution_10_vs_20_days():
    # 실측 리포트(보강 판정용). 10일(현 기본)에서 얇아지는 축이 있으면 드러난다.
    ten, twenty = _opportunities(10), _opportunities(20)
    # 20일은 확실히 견고 — 이 테스트는 분포를 남기는 관측(리포트).
    assert all(twenty[ax] >= 3 for ax in BIAS_AXES), f"20일 {twenty}"
    print(f"[T-55 실측] 10일 opportunities={ten} · 20일={twenty}")
