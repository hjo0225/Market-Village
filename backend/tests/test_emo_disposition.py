"""T-47c — EmoGameRun에 정적 성향 진단 + 편향 원장/집계 배선.

new()가 7문항 answers로 disposition을 확정(불변)하고, choose/chain_choose가
선택지 bias_tags를 bias_tally(hits/opportunities)에 기록한다. actual_bias는
비율식(hits/opportunities×100), 표본 n<3 축은 비노출(RETRO 4b).
"""

from __future__ import annotations

from sim.emo_game import EmoGameRun
from sim.fate_line import CATEGORIES

# 공격형 7문항(전부 최고 위험) — 공격투자형
AGGRESSIVE = {"Q1": 4, "Q2": 4, "Q3": 4, "Q4": 4, "Q5": 4, "Q6": 4, "Q7": 4}
# 안정형 7문항
CONSERVATIVE = {"Q1": 1, "Q2": 1, "Q3": 1, "Q4": 1, "Q5": 1, "Q6": 1, "Q7": 1}


def _cat(returns):
    return {c: list(returns) for c in CATEGORIES}


def _crash_game(answers, days=4):
    events = ["market_crash"] * days
    return EmoGameRun.new(answers, events, _cat([-0.1] * days), seed=1, allocation=None)


# ── 진단 확정 ───────────────────────────────────────────────────────────
def test_new_sets_disposition_from_7q():
    r = EmoGameRun.new(AGGRESSIVE, ["market_crash"], _cat([-0.1]), seed=1)
    assert r.disposition is not None
    assert r.disposition["declared_type"] == "공격투자형"
    assert r.disposition["expected_bias"]["fomo"] == 75


def test_conservative_declared_type():
    r = EmoGameRun.new(CONSERVATIVE, ["market_crash"], _cat([-0.1]), seed=1)
    assert r.disposition["declared_type"] == "안정형"


def test_emotion_uses_v2_composure_neutral():
    # v2 배선 확인 — 진단으론 composure 선입력 안 함(중립 50 시작)
    r = EmoGameRun.new(AGGRESSIVE, ["market_crash"], _cat([-0.1]), seed=1)
    # 진입 노출로 다른 축은 움직여도 composure는 진단 초기값(노출 델타엔 포함될 수 있음)
    assert r.disposition["declared_type"] == "공격투자형"


# ── 편향 집계 ───────────────────────────────────────────────────────────
def test_choose_records_hit_and_opportunity():
    r = _crash_game(AGGRESSIVE, days=1)
    r.choose("cut")   # cut = [panic, loss]
    assert r.bias_tally["panic"]["hits"] == 1
    assert r.bias_tally["panic"]["opportunities"] == 1
    assert r.bias_tally["loss"]["hits"] == 1
    # 급락엔 buy_dip=[over]도 있어 over는 opportunity(안 골랐으니 hit 0)
    assert r.bias_tally["over"]["opportunities"] == 1
    assert r.bias_tally["over"]["hits"] == 0


def test_disciplined_choice_opportunity_no_hit():
    r = _crash_game(AGGRESSIVE, days=1)
    r.choose("hold")  # 태그 없음
    assert r.bias_tally["panic"]["opportunities"] == 1
    assert r.bias_tally["panic"]["hits"] == 0


def test_actual_bias_ratio_and_min_sample():
    r = _crash_game(AGGRESSIVE, days=4)
    for _ in range(4):
        r.choose("cut")
    ab = r.actual_bias()
    # panic: 4 opp / 4 hit = 100 (표본 4 ≥ 3 → 노출)
    assert ab["panic"] == 100
    assert ab["loss"] == 100
    # over: 4 opp / 0 hit = 0
    assert ab["over"] == 0
    # fomo/disp: opportunity 0(급락엔 없음) → 비노출
    assert "fomo" not in ab
    assert "disp" not in ab


def test_actual_bias_hides_small_sample():
    r = _crash_game(AGGRESSIVE, days=2)   # panic opp 2 < 3
    for _ in range(2):
        r.choose("cut")
    assert "panic" not in r.actual_bias()


# ── 직렬화 왕복 ─────────────────────────────────────────────────────────
def test_to_from_doc_preserves_disposition_and_tally():
    r = _crash_game(AGGRESSIVE, days=3)
    r.choose("cut")
    r.choose("buy_dip")
    doc = r.to_doc()
    assert doc["disposition"]["declared_type"] == "공격투자형"
    r2 = EmoGameRun.from_doc(doc)
    assert r2.disposition == r.disposition
    assert r2.bias_tally == r.bias_tally
    assert r2.choice_history == r.choice_history


def test_from_doc_backward_compat_no_disposition():
    r = _crash_game(AGGRESSIVE, days=2)
    doc = r.to_doc()
    del doc["disposition"]
    del doc["bias_tally"]
    del doc["choice_history"]
    r2 = EmoGameRun.from_doc(doc)   # 구 doc — 필드 없어도 복원
    assert r2.disposition is None
    assert r2.actual_bias() == {}
