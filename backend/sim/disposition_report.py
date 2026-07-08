"""T-47d — 진단 리포트: 1층 '선언된 자아' vs 2층 '실제 행동'의 괴리.

스펙 docs/STATIC_DISPOSITION_SPEC.md §3 + 부록 C. 순수함수·결정론(LLM은 선택적
서술 계층이며, 이 계산이 항상 폴백). 엔딩 후 GET /emo/{id}/report에서만 노출된다
(플레이 중 숨김 — 관찰 오염 방지, council D리스크2).
"""

from __future__ import annotations

from .disposition import BIAS_AXES, subdimension_pattern

# 2층 편향 5축 한글 라벨(리포트 표시용).
BIAS_LABELS = {
    "loss": "손실회피", "fomo": "FOMO", "disp": "처분효과",
    "over": "과신", "panic": "패닉",
}

# 부록 C — 하위차원 괴리 패턴별 진단 문장.
_SUBDIM_TEXT = {
    "attitude_over_capacity": "공격적으로 투자하고 싶어 하지만, 실제 감당할 수 있는 손실은 작습니다. 이 간극이 폭락장에서 패닉으로 터집니다.",
    "capacity_over_attitude": "잃어도 괜찮은 여유가 있는데도 지나치게 방어적입니다. 기회 국면에서 과도하게 움츠러들 수 있습니다.",
    "both_high": "욕망과 여력이 일치하는 공격형. 문제는 태도가 아니라 규율입니다.",
    "both_low": "욕망도 여력도 낮은 안정형. 가장 위험한 순간은 남과 비교하며 조급해질 때입니다.",
    "balanced": "감당 능력과 태도가 균형을 이룹니다.",
}


def compute_gaps(expected: dict, actual: dict) -> dict[str, int]:
    """측정된(actual에 존재하는) 편향축만 |기대값 − 실제값| 괴리."""
    return {ax: abs(expected[ax] - actual[ax]) for ax in actual if ax in expected}


def self_awareness(expected: dict, actual: dict) -> int | None:
    """자기 인식 정확도 = 100 − mean(측정축 괴리). 측정축 없으면 None.

    스펙 §3-③은 5축 평균이나, 표본 n<3 축은 actual에서 이미 제외(RETRO 4b)되므로
    '측정된 축'만 평균한다(과소표본 왜곡 배제)."""
    gaps = compute_gaps(expected, actual)
    if not gaps:
        return None
    return round(100 - sum(gaps.values()) / len(gaps))


def _seed_insights(disposition: dict, actual: dict) -> list[str]:
    """§3-② seed 플래그 × 실제 행동 대조 서사(결정론). 측정된 축만 발화."""
    seeds = set(disposition.get("seeds", []))
    conflicts = set(disposition.get("seed_conflicts", []))
    out: list[str] = []

    fomo = actual.get("fomo")
    if fomo is not None and fomo >= 50:
        if "composure" in seeds:
            out.append("냉정하다고 선언했지만, 실제로는 군중에 휩쓸렸습니다. — 가장 큰 괴리.")
        elif "fomo" in seeds:
            out.append("예고된 FOMO가 그대로 실현됐습니다.")

    panic = actual.get("panic")
    if panic is not None and panic >= 50 and "loss_aversion" in seeds:
        out.append("손실을 못 견디는 성향이 실제 패닉 매도로 터졌습니다.")

    disp = actual.get("disp")
    if "disposition" in conflicts and disp is not None and disp >= 50:
        out.append("처분효과 — 선언 단계에서 이미 드러난 패턴이 실현됐습니다.")

    over = actual.get("over")
    if over is not None and over >= 50 and "over" in seeds:
        out.append("'전액 각오' 선언대로, 과신이 행동으로 나타났습니다.")

    return out


def compute_report(disposition: dict | None, actual_bias: dict) -> dict:
    """리포트 전체(결정론). disposition 없으면(구 게임) available=False."""
    if not disposition:
        return {"available": False}

    expected = disposition.get("expected_bias", {})
    comparison = [
        {
            "axis": ax,
            "label": BIAS_LABELS.get(ax, ax),
            "expected": expected.get(ax),
            "actual": actual_bias[ax],
            "gap": abs(expected.get(ax, 0) - actual_bias[ax]),
        }
        for ax in BIAS_AXES
        if ax in actual_bias
    ]
    pattern = subdimension_pattern(
        attitude_score=disposition.get("attitude_score", 50),
        capacity_score=disposition.get("capacity_score", 50),
    )
    return {
        "available": True,
        "declared_type": disposition.get("declared_type"),
        "capacity_score": disposition.get("capacity_score"),
        "attitude_score": disposition.get("attitude_score"),
        "subdimension": {"pattern": pattern, "text": _SUBDIM_TEXT.get(pattern, "")},
        "bias_comparison": comparison,
        "measured_axes": [c["axis"] for c in comparison],
        "self_awareness": self_awareness(expected, actual_bias),
        "insights": _seed_insights(disposition, actual_bias),
    }
