"""T-47d — 진단 리포트 계산(순수함수) + GET /emo/{id}/report.

API는 TestClient 소켓 플레이크(RETRO 규칙5)를 피해 핸들러를 직접 호출해 검증한다.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from sim import disposition_report as R
from sim import emo_api, emo_store
from sim.emo_game import EmoGameRun
from sim.fate_line import CATEGORIES

AGGRESSIVE = {"Q1": 10, "Q2": 5, "Q3": 10, "Q4": 6, "Q5": 6, "Q6": 6, "Q7": 10}

DISP = {
    "declared_type": "공격투자형",
    "capacity_score": 90, "attitude_score": 90,
    "expected_bias": {"loss": 30, "fomo": 75, "disp": 40, "over": 75, "panic": 20},
    "seeds": ["greed", "fomo", "over"],
    "seed_conflicts": [],
}


# ── 순수 계산 ───────────────────────────────────────────────────────────
def test_compute_gaps_measured_only():
    gaps = R.compute_gaps({"fomo": 75, "panic": 20}, {"fomo": 60, "panic": 100})
    assert gaps == {"fomo": 15, "panic": 80}


def test_self_awareness_perfect_and_none():
    assert R.self_awareness({"fomo": 75}, {"fomo": 75}) == 100
    assert R.self_awareness({"fomo": 75}, {}) is None


def test_self_awareness_lowers_with_gap():
    # 기대 75인데 실제 25 → 괴리 50 → SA 50
    assert R.self_awareness({"fomo": 75}, {"fomo": 25}) == 50


def test_compute_report_unavailable_without_disposition():
    assert R.compute_report(None, {})["available"] is False


def test_compute_report_structure():
    rep = R.compute_report(DISP, {"panic": 100, "loss": 100, "over": 0})
    assert rep["available"] is True
    assert rep["declared_type"] == "공격투자형"
    assert set(rep["measured_axes"]) == {"panic", "loss", "over"}
    assert rep["subdimension"]["pattern"] == "both_high"
    # SA = 100 - mean(|20-100|,|30-100|,|75-0|) = 100 - 75 = 25
    assert rep["self_awareness"] == 25
    # fomo/disp는 미측정 → 비교표에서 제외
    assert all(c["axis"] in ("panic", "loss", "over") for c in rep["bias_comparison"])


# --- v3 §A: 측정축 0개(10일 전환으로 표본 부족) 정적 안내 ------------------- #
def test_compute_report_low_sample_notice_when_no_measured_axes():
    rep = R.compute_report(DISP, {})   # actual_bias 빈 dict → measured_axes=[]
    assert rep["measured_axes"] == []
    assert rep["low_sample_notice"] == R.LOW_SAMPLE_NOTICE
    # T-66 — 3일 압축 모드에서도 노출되는 문구라 일수 표기 없이 말한다.
    assert rep["low_sample_notice"] == "이번 계절은 짧았다. 더 놀러 오면 더 정확해진다."


def test_compute_report_low_sample_notice_none_when_axes_measured():
    rep = R.compute_report(DISP, {"panic": 100, "loss": 100, "over": 0})
    assert rep["low_sample_notice"] is None


def test_seed_insight_fomo_realized():
    ins = R._seed_insights(DISP, {"fomo": 70})
    assert any("FOMO" in s for s in ins)


def test_seed_insight_composure_contradicted():
    disp = dict(DISP, seeds=["composure"])
    ins = R._seed_insights(disp, {"fomo": 70})
    assert any("냉정" in s for s in ins)


# ── API 핸들러 (직접 호출) ─────────────────────────────────────────────
def _played_game_id(days=4):
    events = ["market_crash"] * days
    run = EmoGameRun.new(AGGRESSIVE, events, {c: [-0.1] * days for c in CATEGORIES}, seed=1)
    for _ in range(days):
        run.choose("sell", coin_target="meme")   # T-53: 급락 매도 = [panic]
    gid = "test-report-" + str(days)
    emo_store.save_run(gid, run)
    return gid


def test_report_endpoint_after_ending():
    gid = _played_game_id(days=4)
    rep = emo_api.report(gid)
    assert rep["available"] is True
    assert rep["declared_type"] == "공격투자형"
    assert "panic" in rep["measured_axes"]


def test_report_endpoint_409_when_ongoing():
    run = EmoGameRun.new(AGGRESSIVE, ["market_crash"] * 4,
                         {c: [-0.1] * 4 for c in CATEGORIES}, seed=1)
    gid = "test-report-ongoing"
    emo_store.save_run(gid, run)   # day 0, 미완
    with pytest.raises(HTTPException) as ei:
        emo_api.report(gid)
    assert ei.value.status_code == 409


# ── 서술 계층 (T-47f) ───────────────────────────────────────────────────
def test_deterministic_narrative_uses_numbers_and_coach():
    rep = R.compute_report(DISP, {"panic": 100, "over": 0})
    joined = " ".join(R._deterministic_narrative(rep, None))
    assert str(rep["self_awareness"]) in joined   # 일치도 점수 인용
    assert "규율" in joined                        # 공격투자형 코칭


def test_generate_narrative_none_client_is_deterministic():
    rep = R.compute_report(DISP, {"over": 100})
    assert R.generate_narrative(rep, None, None) == R._deterministic_narrative(rep, None)


def test_generate_narrative_llm_rewrites():
    from sim.llm import FakeLLM
    fake = FakeLLM(response='{"narrative": ["과신을 75로 봤지만 실제 100.", "말보다 손이 빨랐습니다."]}')
    rep = R.compute_report(DISP, {"over": 100, "panic": 33})
    assert R.generate_narrative(rep, None, fake) == ["과신을 75로 봤지만 실제 100.", "말보다 손이 빨랐습니다."]


def test_generate_narrative_falls_back_on_bad_llm():
    from sim.llm import FakeLLM
    fake = FakeLLM(response="완전히 JSON이 아님")   # extract_json 실패 → 폴백
    rep = R.compute_report(DISP, {"over": 100})
    assert R.generate_narrative(rep, None, fake) == R._deterministic_narrative(rep, None)


def test_report_endpoint_includes_narrative():
    # conftest가 OS 키를 strip → default_client().available=False → 결정론 폴백.
    gid = _played_game_id(days=4)
    rep = emo_api.report(gid)
    assert rep.get("narrative")   # 서술 존재(결정론)


def test_report_endpoint_caches_narrative(monkeypatch):
    from sim.llm import FakeLLM
    fake = FakeLLM(response='{"narrative": ["한 번만 생성됩니다."]}')
    monkeypatch.setattr(emo_api._llm, "default_client", lambda: fake)
    gid = _played_game_id(days=4)
    r1 = emo_api.report(gid)
    r2 = emo_api.report(gid)
    assert r1["narrative"] == ["한 번만 생성됩니다."]
    assert r2["narrative"] == r1["narrative"]
    assert len(fake.calls) == 1   # 캐시 → 두 번째는 LLM 미호출(과금 상한)


# ── T-48c 표본수 · T-48d 타임라인 · T-49c 블라인드 공개 ─────────────────
def test_report_includes_sample_and_low_flag():
    tally = {"panic": {"hits": 4, "opportunities": 6}, "over": {"hits": 0, "opportunities": 2}}
    rep = R.compute_report(DISP, {"panic": 67, "over": 0}, bias_tally=tally)
    by = {c["axis"]: c for c in rep["bias_comparison"]}
    assert by["panic"]["sample"] == 6 and by["panic"]["low_sample"] is False
    assert by["over"]["sample"] == 2 and by["over"]["low_sample"] is True   # n<5 참고


def test_report_timeline_skips_disciplined():
    ch = [
        {"day": 1, "kind": "scenario", "hits": ["panic"], "opportunities": ["panic", "loss"]},
        {"day": 2, "kind": "scenario", "hits": [], "opportunities": ["panic", "loss"]},   # 절제
        {"day": 3, "kind": "place", "hits": ["disp"], "opportunities": ["disp"]},
    ]
    rep = R.compute_report(DISP, {"panic": 100}, choice_history=ch)
    tl = rep["timeline"]
    assert [t["day"] for t in tl] == [1, 3]   # 절제한 day2 생략(신호 선명)
    assert tl[0]["biases"] == ["패닉"] and tl[1]["biases"] == ["처분효과"]


def test_fate_reveal_blind_origin():
    from sim.fate_line import load_fate_line
    rev = load_fate_line().reveal()
    meme = next(r for r in rev if r["category"] == "meme")
    assert meme["symbol"] == "DOGE" and meme["name"] == "도지코인"
    assert meme["date"] == "2021-04-20"


# --- v3 §B: blind_reveal 설계 전환 — 시기(period) 공개가 리빌의 센터피스 ----- #
def test_fate_reveal_includes_period_alongside_symbol_and_date():
    from sim.fate_line import load_fate_line
    rev = load_fate_line().reveal()
    meme = next(r for r in rev if r["category"] == "meme")
    assert meme["period"] == "2021년 4월"
    # 종목명도 계속 포함(프론트가 재구성할 수 있게) — v3 설계 전환은 '추가'다.
    assert meme["symbol"] == "DOGE" and meme["name"] == "도지코인"
    assert meme["date"] == "2021-04-20"


def test_report_endpoint_includes_reveal_and_sample():
    gid = _played_game_id(days=4)
    rep = emo_api.report(gid)
    assert any(r["symbol"] == "DOGE" for r in rep.get("blind_reveal", []))   # T-49c
    assert all("sample" in c for c in rep["bias_comparison"])                # T-48c


def test_report_endpoint_includes_period_centric_headline():
    # 3일 압축 모드 도입(days_word)으로 헤드라인이 실제 일수를 말하게 됐다 —
    # 4일 게임이면 "열흘"이 아니라 "4일"(days_word 폴백)이어야 정확하다.
    gid = _played_game_id(days=4)
    rep = emo_api.report(gid)
    assert rep["blind_reveal_headline"] == "당신의 4일은 사실 2021년 4월이었다."
