"""v3 §D1 — 진단 결과 화면(설문 직후)의 근거 제시. 신규 모듈.

`disposition.diagnose()`가 이미 계산한 값(declared_type/capacity_score/
attitude_score)을 노출하는 것 외에 **신규 계산은 점수 역추적뿐**이다: 각
문항의 답을 QUESTIONS에서 역참조해 그 선택지의 label과 (dim, 가중치 반영
점수)를 얻는다. 순수함수·정적 텍스트(I5: LLM 금지).
"""

from __future__ import annotations

from .disposition import DECLARED_TYPES, QUESTIONS, _score, diagnose

_Q = {q["id"]: q for q in QUESTIONS}

# 축 표시 라벨(capacity/attitude → 한글).
_AXIS_LABELS = {"capacity": "감당 능력", "attitude": "위험 감수 태도"}


def _axes(disp: dict) -> list[dict]:
    """§D1 — axes: [{"axis","label","score","max"}]. diagnose()가 이미 낸
    capacity_score/attitude_score(0~100 정규화)를 그대로 노출."""
    return [
        {"axis": "capacity", "label": _AXIS_LABELS["capacity"],
         "score": disp["capacity_score"], "max": 100},
        {"axis": "attitude", "label": _AXIS_LABELS["attitude"],
         "score": disp["attitude_score"], "max": 100},
    ]


def _chosen_option(qid: str, answers: dict) -> dict | None:
    """그 문항에서 실제 선택된 옵션(점수로 역참조, disposition._score와 동일
    폴백 규칙 — 누락/무효는 중앙값)."""
    s = _score(answers, qid)
    for opt in _Q[qid]["options"]:
        if opt["points"] == s:
            return opt
    return None


def _contributions(answers: dict) -> list[dict]:
    """§D1 — contributions: [{"q","q_label","choice_label","axis","points"}].
    각 문항의 실제 선택이 그 축(dim)에 기여한 점(가중치 반영 score)으로 점수를
    역추적한다(신규 계산 아님 — QUESTIONS/스코어 산식의 재노출)."""
    out: list[dict] = []
    for q in QUESTIONS:
        qid = q["id"]
        opt = _chosen_option(qid, answers)
        if opt is None:
            continue
        points = opt["points"]   # 새 스키마: 가중치가 points에 이미 반영됨
        out.append({
            "q": qid,
            "q_label": q["text"],
            "choice_label": opt["label"],
            "axis": q["dim"],
            "points": points,
        })
    return out


# §D1 — declared_type별 정적 요약 2줄 + 공통 고정 마무리 문장.
_SUMMARY_LINES: dict[str, list[str]] = {
    "안정형": [
        "당신은 원금을 지키는 것을 최우선으로 둡니다.",
        "손실보다, 남들이 벌 때 조급해지는 순간이 진짜 시험대입니다.",
    ],
    "안정추구형": [
        "안정을 우선하면서도 초과 수익의 기회를 놓치고 싶어 하지 않습니다.",
        "안전과 욕심 사이 경계에서 자주 흔들립니다.",
    ],
    "위험중립형": [
        "위험과 기회 사이에서 균형을 잡으려 합니다.",
        "다만 시장이 한쪽으로 쏠리면 중심을 잃기 쉽습니다.",
    ],
    "적극투자형": [
        "수익을 위해 위험을 기꺼이 감수하는 편입니다.",
        "문제는 감수가 규율을 넘어서는 순간입니다.",
    ],
    "공격투자형": [
        "전액을 걸어도 괜찮다고 말할 만큼 공격적입니다.",
        "태도가 아니라 규율이 당신의 진짜 승부처입니다.",
    ],
}

_CLOSING_LINE = "클론은 이 성향대로 열흘을 산다. 진짜 당신과 같은지는, 끝에 확인하자."


def _summary(declared_type: str) -> list[str]:
    lines = list(_SUMMARY_LINES.get(declared_type, _SUMMARY_LINES[DECLARED_TYPES[2]]))
    lines.append(_CLOSING_LINE)
    return lines


def build_diagnosis(answers: dict) -> dict:
    """§D1 — POST /emo/start 응답의 `diagnosis` 필드 전체.

    {"declared_type", "axes", "contributions", "summary"}. disposition.diagnose()
    결과의 노출 + 문항별 기여 분해(점수 역추적)만 신규다."""
    disp = diagnose(answers)
    return {
        "declared_type": disp["declared_type"],
        "axes": _axes(disp),
        "contributions": _contributions(answers),
        "summary": _summary(disp["declared_type"]),
    }
