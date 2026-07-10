"""T-63 (2안): 클론 본능 배지 + 거스름 비용.

성향(declared_type)이 무의식적으로 끌리는 게시판 액션(2-1-2). 본능을 거스르면
감정 비용(anxiety) + 규율 집계(discipline_tally) → 엔딩 리포트 규율 요약으로 소비.
🔒 관찰오염 없음 — declared_type만 쓰고 expected_bias(편향축)는 비노출.
"""
import random

from sim import board_exposure
from sim.disposition import instinct_action
from sim.disposition_report import compute_report
from sim.emo_game import INSTINCT_DEFY_DELTA, EmoGameRun
from sim.fate_line import CATEGORIES

ANSWERS = {"Q1": 2, "Q2": 2, "Q3": 2, "Q4": 2, "Q5": 2, "Q6": 2, "Q7": 2}


def _cat(returns):
    return {c: list(returns) for c in CATEGORIES}


def _aggressive_run(days=3):
    run = EmoGameRun.new(ANSWERS, ["market_crash"] * days, _cat([-0.1, 0.05, 0.02]), seed=1)
    run.disposition = {**run.disposition, "declared_type": "공격투자형"}   # 본능 = buy
    return run


# --- instinct_action 순수함수 (2-1-2) ------------------------------------- #
def test_instinct_action_two_one_two_mapping():
    assert instinct_action("안정형") == "sell"
    assert instinct_action("안정추구형") == "sell"
    assert instinct_action("위험중립형") == "hold"
    assert instinct_action("적극투자형") == "buy"
    assert instinct_action("공격투자형") == "buy"


def test_instinct_action_unknown_is_none():
    assert instinct_action("없는유형") is None


# --- render_board instinct 배지 ------------------------------------------- #
def test_render_board_flags_instinct_choice():
    board = _aggressive_run().board()
    flag = {c["action"]: c["instinct"] for c in board["scenario"]["choices"]}
    assert flag["buy"] is True                      # 공격형 본능 = 매수
    assert flag["sell"] is False and flag["hold"] is False


def test_render_board_without_declared_type_omits_instinct():
    # 레거시 호출(declared_type 생략) → instinct 필드 없이 하위호환.
    b = board_exposure.render_board("market_crash", random.Random(1), seed=1, day=0)
    assert all("instinct" not in c for c in b["scenario"]["choices"])


# --- 거스름 비용 + 규율 집계 --------------------------------------------- #
def test_defying_instinct_costs_anxiety_and_counts():
    run = _aggressive_run()
    run.choose("sell", coin_target="meme")           # 본능(buy) 거스름
    assert run.discipline_tally == {"defied": 1, "total": 1}
    step = next(s for s in run.last_settlement["emotion_steps"] if s["source"] == "instinct")
    assert step["deltas"]["anxiety"] == INSTINCT_DEFY_DELTA["anxiety"]
    assert step["instinct"] == "buy" and step["action"] == "sell"


def test_following_instinct_is_free():
    run = _aggressive_run()
    run.choose("buy", coin_target="meme")            # 본능(buy) 따름
    assert run.discipline_tally == {"defied": 0, "total": 1}
    sources = [s["source"] for s in run.last_settlement["emotion_steps"]]
    assert "instinct" not in sources


def test_no_disposition_skips_discipline_entirely():
    # 성향 없는(레거시) 게임은 본능도 규율도 없음 — total 0 유지.
    run = EmoGameRun.new(ANSWERS, ["market_crash"] * 3, _cat([-0.1, 0.05, 0.02]), seed=1)
    run.disposition = None
    run.choose("sell", coin_target="meme")
    assert run.discipline_tally == {"defied": 0, "total": 0}


def test_discipline_tally_survives_serialization():
    run = _aggressive_run()
    run.choose("sell", coin_target="meme")
    restored = EmoGameRun.from_doc(run.to_doc())
    assert restored.discipline_tally == run.discipline_tally == {"defied": 1, "total": 1}


# --- 리포트 규율 요약 ----------------------------------------------------- #
def test_report_discipline_summary_from_tally():
    disp = {"declared_type": "공격투자형", "expected_bias": {}}
    rep = compute_report(disp, {}, discipline_tally={"defied": 3, "total": 4})
    assert rep["discipline"] == {"defied": 3, "total": 4, "defy_rate": 75}


def test_report_discipline_absent_when_no_samples():
    disp = {"declared_type": "공격투자형", "expected_bias": {}}
    rep = compute_report(disp, {}, discipline_tally={"defied": 0, "total": 0})
    assert rep["discipline"] is None
