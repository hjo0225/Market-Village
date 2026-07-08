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


# ── 서술 계층 (T-47f) — 결정론 리치 폴백 + 선택적 LLM 재작성 ────────────
# declared_type별 코칭 한 줄(규율의 급소를 짚는다).
_TYPE_COACH = {
    "안정형": "원금을 지키려는 본능이 강합니다. 진짜 위험은 손실이 아니라, 남들이 벌 때 조급해지는 순간입니다.",
    "안정추구형": "안정을 우선하면서도 초과 수익을 노립니다. 그 경계에서 흔들릴 때가 당신의 급소입니다.",
    "위험중립형": "균형을 지향하지만, 시장이 한쪽으로 쏠릴 때 중심을 잃기 쉽습니다.",
    "적극투자형": "수익을 위해 위험을 감수합니다. 감수가 규율을 넘어서는 순간이 함정입니다.",
    "공격투자형": "전액 리스크도 불사합니다. 태도가 아니라 규율이 당신의 승부처입니다.",
}


def _deterministic_narrative(report: dict, ending: dict | None) -> list[str]:
    """LLM 없이도 성립하는 리치 서술(항상 폴백). 실제 수치·최대 괴리·유형 코칭."""
    out: list[str] = []
    sa = report.get("self_awareness")
    if sa is not None:
        tone = ("선언과 행동이 대체로 일치했습니다" if sa >= 75
                else "선언과 행동이 절반쯤 어긋났습니다" if sa >= 50
                else "선언과 행동이 크게 어긋났습니다")
        out.append(f"열흘 동안 당신의 말과 행동의 일치도는 {sa}점 — {tone}.")
    comp = report.get("bias_comparison") or []
    if comp:
        worst = max(comp, key=lambda c: c.get("gap", 0))
        if worst.get("gap", 0) >= 15:
            out.append(
                f"가장 크게 벌어진 건 '{worst['label']}'입니다. 스스로는 {worst['expected']}쯤으로 봤지만, "
                f"실제 행동은 {worst['actual']}이었습니다."
            )
    coach = _TYPE_COACH.get(report.get("declared_type", ""))
    if coach:
        out.append(coach)
    out.extend(report.get("insights") or [])
    return out or ["열흘의 기록이 아직 충분치 않습니다."]


_NARRATIVE_SYSTEM = (
    "너는 투자 심리 코치다. 플레이어가 스스로 선언한 투자 성향과, 열흘 시뮬레이션에서 "
    "실제로 보인 행동 편향의 괴리를 짧고 강하게 짚어준다. 2인칭('당신')으로 사람에게 "
    "말하듯 직설적이고 따뜻하게. 주어진 구체 수치(예상 vs 실제)를 반드시 인용하되, "
    "학술적·완곡한 표현('~할 수 있습니다', '암시합니다', '영향을 미칠 수 있음', "
    "'부정적인 영향')은 금지. 가장 크게 벌어진 편향 하나에 집중해 콕 찌른다. "
    "한국어 3문장, 각 문장 40자 내외. 이모지·클리셰·번호매기기 금지. 반드시 "
    '{"narrative": ["문장", "문장", "문장"]} JSON 하나로만 답하라.'
)


def _narrative_prompt(report: dict, ending: dict | None) -> str:
    lines = [
        f"선언 유형: {report.get('declared_type')} "
        f"(감당능력 {report.get('capacity_score')}, 감수태도 {report.get('attitude_score')})"
    ]
    for c in report.get("bias_comparison") or []:
        lines.append(f"- {c['label']}: 예상 {c['expected']} vs 실제 {c['actual']} (괴리 {c['gap']})")
    if report.get("self_awareness") is not None:
        lines.append(f"자기인식 일치도: {report['self_awareness']}/100")
    if report.get("insights"):
        lines.append("힌트: " + " / ".join(report["insights"]))
    if ending:
        lines.append(f"엔딩: {ending.get('title')} ({ending.get('grade')})")
    return "\n".join(lines)


def generate_narrative(report: dict, ending: dict | None, client=None) -> list[str]:
    """리포트 서술 문장 리스트. LLM(client)이 있으면 재작성, 실패·미허용 시
    결정론 폴백(_deterministic_narrative). 게이트·한도·캐시는 client.chat이 처리."""
    det = _deterministic_narrative(report, ending)
    if client is None:
        return det
    from .llm import safe_json
    out = safe_json(
        client, _narrative_prompt(report, ending),
        fallback={"narrative": det}, system=_NARRATIVE_SYSTEM,
    )
    narr = out.get("narrative")
    if isinstance(narr, list) and narr and all(isinstance(x, str) and x.strip() for x in narr):
        return [str(x).strip() for x in narr][:5]
    return det
