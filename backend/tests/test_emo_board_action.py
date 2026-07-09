"""T-53 (F4): 게시판 3액션(감정 소모 매매)의 choose() 거동 — authoritative 스펙.

각 게시판 이벤트 = [상황] + 매수(탐욕 소모·현금→코인)/매도(공포 소모·코인→현금)/
유지(평정 소모·무매매) 3액션. 매매 규모 = 소모 전 감정 level 비례. 편향 태그는
council 매핑(급락 매수=over·매도=panic·유지=loss).
"""
import pytest

from sim.emo_game import CASH, EmoGameRun
from sim.fate_line import CATEGORIES
from sim.player_emotion.state import PlayerEmotionState
from sim.scenario import get_scenario

ANSWERS = {"q_panic": 0.5, "q_fomo": 0.5, "q_rumor": 0.5, "q_check": 0.5}


def _run(events=("market_crash",)):
    # 수익률 0 → 시장 실현이 holdings를 안 바꿔 매매 검증이 깨끗함.
    return EmoGameRun.new(ANSWERS, list(events), {c: [0.0] for c in CATEGORIES}, seed=1)


def test_scenario_has_exactly_three_actions_buy_sell_hold():
    sc = get_scenario("market_crash")
    ids = [c["id"] for c in sc["choices"]]
    assert ids == ["buy", "sell", "hold"] or set(ids) == {"buy", "sell", "hold"}
    assert len(sc["choices"]) == 3


def test_sell_consumes_fear_and_moves_chosen_coin_to_cash():
    r = _run()
    r.emotion = PlayerEmotionState(fear=80, greed=20, composure=50)
    r.holdings = {CASH: 0.0, "meme": 1000.0, "large_stable": 0.0, "mid_alt": 0.0, "stable": 0.0}
    r.choose("sell", coin_target="meme")
    s = r.last_settlement["choice"]
    assert s["action"] == "sell"
    assert s["consumed"] == pytest.approx(40.0)          # 공포 80의 50%
    assert s["coin_target"] == "meme"
    assert s["traded"] == pytest.approx(800.0)           # fear level 80 → meme 1000의 80%
    assert r.holdings["meme"] == pytest.approx(200.0)
    assert r.holdings[CASH] == pytest.approx(800.0)


def test_buy_consumes_greed_and_moves_cash_into_chosen_coin():
    r = _run()
    r.emotion = PlayerEmotionState(greed=90, fear=20, composure=50)
    r.holdings = {CASH: 1000.0, "meme": 0.0, "large_stable": 0.0, "mid_alt": 0.0, "stable": 0.0}
    r.choose("buy", coin_target="meme")
    s = r.last_settlement["choice"]
    assert s["action"] == "buy"
    assert s["consumed"] == pytest.approx(18.0)           # 탐욕 90의 20%
    assert s["traded"] == pytest.approx(900.0)            # greed level 90 → 현금 1000의 90%
    assert r.holdings["meme"] == pytest.approx(900.0)
    assert r.holdings[CASH] == pytest.approx(100.0)


def test_hold_consumes_composure_and_does_not_trade():
    r = _run()
    r.emotion = PlayerEmotionState(composure=60, fear=30, greed=30)
    before = dict(r.holdings)
    r.choose("hold")                                       # coin_target 불필요
    s = r.last_settlement["choice"]
    assert s["action"] == "hold"
    assert s["consumed"] == pytest.approx(6.0)             # 평정 60의 10%
    assert s["traded"] == 0.0
    assert r.holdings == before                            # 무매매


def test_higher_fear_sells_more():
    hi, lo = _run(), _run()
    for r, f in ((hi, 90), (lo, 20)):
        r.emotion = PlayerEmotionState(fear=f, composure=50)
        r.holdings = {CASH: 0.0, "meme": 1000.0, "large_stable": 0.0, "mid_alt": 0.0, "stable": 0.0}
        r.choose("sell", coin_target="meme")
    assert hi.last_settlement["choice"]["traded"] > lo.last_settlement["choice"]["traded"]


def test_buy_or_sell_without_coin_target_raises():
    r = _run()
    with pytest.raises(ValueError):
        r.choose("buy")
    r2 = _run()
    with pytest.raises(ValueError):
        r2.choose("sell", coin_target="not_a_coin")


def test_crash_bias_mapping_buy_over_sell_panic_hold_loss():
    # council 매핑(급락): 매수=over·매도=panic·유지=loss. _record_bias union으로 적립.
    for action, axis in (("buy", "over"), ("sell", "panic"), ("hold", "loss")):
        r = _run()
        r.emotion = PlayerEmotionState(fear=60, greed=60, composure=60)
        r.holdings = {CASH: 500.0, "meme": 500.0, "large_stable": 0.0, "mid_alt": 0.0, "stable": 0.0}
        kw = {} if action == "hold" else {"coin_target": "meme"}
        r.choose(action, **kw)
        assert r.bias_tally[axis]["hits"] == 1, f"{action} → {axis}"
