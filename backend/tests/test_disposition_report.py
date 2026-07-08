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

AGGRESSIVE = {"Q1": 4, "Q2": 4, "Q3": 4, "Q4": 4, "Q5": 4, "Q6": 4, "Q7": 4}

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
        run.choose("cut")
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
