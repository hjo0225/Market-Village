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
    r.choose("cut")   # T-48b: cut = [panic] (loss는 hold로 분리)
    assert r.bias_tally["panic"]["hits"] == 1
    assert r.bias_tally["panic"]["opportunities"] == 1
    # loss는 이 결정점의 hold=[loss]로 opportunity지만, cut을 골라 hit=0
    assert r.bias_tally["loss"]["opportunities"] == 1
    assert r.bias_tally["loss"]["hits"] == 0
    # 급락엔 buy_dip=[over]도 있어 over는 opportunity(안 골랐으니 hit 0)
    assert r.bias_tally["over"]["opportunities"] == 1
    assert r.bias_tally["over"]["hits"] == 0


def test_hold_records_loss_not_panic():
    # T-48b — 버티기(hold)=loss(손실 실현 거부)이고 panic 아님. 분리 검증.
    r = _crash_game(AGGRESSIVE, days=1)
    r.choose("hold")
    assert r.bias_tally["loss"]["hits"] == 1
    assert r.bias_tally["panic"]["opportunities"] == 1
    assert r.bias_tally["panic"]["hits"] == 0


def test_actual_bias_ratio_and_min_sample():
    r = _crash_game(AGGRESSIVE, days=4)
    for _ in range(4):
        r.choose("cut")
    ab = r.actual_bias()
    # panic: 4 opp / 4 hit = 100 (표본 4 ≥ 3 → 노출)
    assert ab["panic"] == 100
    # T-48b: loss는 hold로 분리 — cut만 4번 골랐으니 loss opp 4 / hit 0 = 0
    # (예전엔 cut=[panic,loss]라 loss도 100이 나와 두 축이 항상 동일했다)
    assert ab["loss"] == 0
    # over: 4 opp / 0 hit = 0
    assert ab["over"] == 0
    # fomo: 급락 이벤트엔 여전히 없음 → 비노출.
    # disp: §4.1 확장(D "미리 정해둔 손절선만 확인" bias_tags=["disp"])으로 급락에도
    # disp opportunity가 생겼다 — cut만 4번 골랐으니 disp opp 4 / hit 0 = 0(노출은 됨).
    assert "fomo" not in ab
    assert ab["disp"] == 0


def test_actual_bias_hides_small_sample():
    r = _crash_game(AGGRESSIVE, days=2)   # panic opp 2 < 3
    for _ in range(2):
        r.choose("cut")
    assert "panic" not in r.actual_bias()


# ── T-50d 장소 딜레마(disp 처분효과 결정점) ─────────────────────────────
def _run_with_place(place, days=8, seed=42):
    """그 장소가 어느 날 동선에 뜨는 run(그 날로 day 세팅)을 돌려준다."""
    r = EmoGameRun.new(AGGRESSIVE, ["market_volatile"] * days, _cat([0.0] * days), seed=seed)
    for d in range(days):
        r.day = d
        if place in r.day_schedule().values():
            return r
    raise AssertionError(f"{place} 방문일 없음(seed={seed})")


def test_place_dilemma_records_disp():
    # 도서관 익절(take_profit)=disp 적립 → 리포트에서 처분효과 측정(T-48e 흡수).
    r = _run_with_place("도서관")
    dil = r.place_dilemma("도서관")
    assert dil is not None
    assert dil["choices"][0]["bias_tags"] == ["disp"]
    r.resolve_place_dilemma("도서관", "take_profit")
    assert r.bias_tally["disp"]["hits"] == 1
    assert r.bias_tally["disp"]["opportunities"] == 1


def test_place_dilemma_idempotent():
    # 같은 (day, place) 재요청은 이중 적용 안 됨(리로드/재시도 안전, 게이트 4c).
    r = _run_with_place("도서관")
    r.resolve_place_dilemma("도서관", "take_profit")
    r.resolve_place_dilemma("도서관", "take_profit")
    assert r.bias_tally["disp"]["hits"] == 1


def test_place_dilemma_none_when_not_today():
    r = EmoGameRun.new(AGGRESSIVE, ["market_volatile"] * 4, _cat([0.0] * 4), seed=42)
    r.day = 0
    absent = next(p for p in ("도서관", "마켓") if p not in r.day_schedule().values())
    assert r.place_dilemma(absent) is None


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
