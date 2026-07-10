"""T-52 (F4): per-코인 지정 매수/매도 + 감정 비례 매매 규모.

게시판 3액션의 포트폴리오 경로 — 카테고리(=코인) 버킷 자동(_rebalance) 대신
코인 1개를 지정해 현금↔코인 이동. 매매 규모는 소모 전 감정 level에 비례한다.
(감정 소모 자체는 T-51, choose() 재배선·편향은 T-53.)
"""
import pytest

from sim.emo_game import CASH, TRADE_INTENSITY, EmoGameRun
from sim.fate_line import CATEGORIES

ANSWERS = {"q_panic": 0.5, "q_fomo": 0.5, "q_rumor": 0.5, "q_check": 0.5}


def _run():
    return EmoGameRun.new(ANSWERS, ["market_crash"], {c: [0.0] for c in CATEGORIES}, seed=1)


def test_board_trade_size_proportional_to_emotion_level():
    r = _run()
    assert r._board_trade_size(92, 1000) > r._board_trade_size(20, 1000)
    assert r._board_trade_size(0, 1000) == 0
    assert r._board_trade_size(100, 1000) == pytest.approx(1000 * TRADE_INTENSITY)


def test_buy_coin_moves_cash_into_coin_and_conserves_total():
    r = _run()
    r.holdings = {CASH: 1000.0, "meme": 0.0}
    before = r.portfolio_value
    moved = r._buy_coin("meme", 300.0)
    assert moved == 300.0
    assert r.holdings[CASH] == 700.0
    assert r.holdings["meme"] == 300.0
    assert r.portfolio_value == pytest.approx(before)  # 총액 보존(돈은 이동만, 생성 아님)


def test_buy_coin_capped_at_available_cash():
    r = _run()
    r.holdings = {CASH: 200.0, "meme": 0.0}
    moved = r._buy_coin("meme", 999.0)
    assert moved == 200.0
    assert r.holdings[CASH] == 0.0
    assert r.holdings["meme"] == 200.0


def test_buy_zero_or_negative_is_noop():
    r = _run()
    r.holdings = {CASH: 100.0, "meme": 0.0}
    assert r._buy_coin("meme", 0.0) == 0.0
    assert r._buy_coin("meme", -50.0) == 0.0
    assert r.holdings[CASH] == 100.0


def test_sell_coin_moves_coin_into_cash_and_conserves_total():
    r = _run()
    r.holdings = {CASH: 100.0, "meme": 500.0}
    before = r.portfolio_value
    moved = r._sell_coin("meme", 200.0)
    assert moved == 200.0
    assert r.holdings["meme"] == 300.0
    assert r.holdings[CASH] == 300.0
    assert r.portfolio_value == pytest.approx(before)


def test_sell_coin_capped_at_holding():
    r = _run()
    r.holdings = {CASH: 0.0, "meme": 150.0}
    moved = r._sell_coin("meme", 999.0)
    assert moved == 150.0
    assert r.holdings["meme"] == 0.0
    assert r.holdings[CASH] == 150.0


def test_sell_unheld_coin_is_noop():
    r = _run()
    r.holdings = {CASH: 100.0, "meme": 0.0}
    assert r._sell_coin("meme", 50.0) == 0.0
    assert r.holdings[CASH] == 100.0


def test_higher_greed_buys_more_of_chosen_coin():
    # 감정 비례(4b): 탐욕 레벨↑ → 같은 코인 더 크게 매수.
    hi, lo = _run(), _run()
    hi.holdings = {CASH: 1000.0, "meme": 0.0}
    lo.holdings = {CASH: 1000.0, "meme": 0.0}
    hi._buy_coin("meme", hi._board_trade_size(90, 1000.0))
    lo._buy_coin("meme", lo._board_trade_size(20, 1000.0))
    assert hi.holdings["meme"] > lo.holdings["meme"]
