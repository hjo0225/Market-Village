"""정적 성향 진단 (1층 "선언된 자아").

성향분석.md 정본: 전국투자자교육협의회 '투자 성향 진단표'(7문항)를 코인 맥락으로
재구성한 것. 문항별 가중 배점을 합산해 5단계 투자성향(안정형·안정추구형·위험중립형·
적극투자형·공격투자형)으로 판정한다. 공식 컷오프(20/28/36/44/45)를 그대로 쓴다.
게임 본편은 declared_type(5유형)과 expected_bias 파이프라인을 재사용한다.

순수함수만 — 상태·IO 없음. 답안(answers)은 {"Q1".."Q7": points} 형태
(각 문항 선택지 점수가 문항 내에서 유일하므로 점수로 선택지를 역참조해 seed를 얻는다).
"""

from __future__ import annotations

from .player_emotion.state import PlayerEmotionState, clamp

SOURCE = "전국투자자교육협의회 '투자 성향 진단표' 참고해 재구성"

# ── 문항 세트 ────────────────────────────────────────────────────────────
# 각 선택지: points(문항 내 유일, 클수록 위험지향) + seed(예상 편향 힌트).
# dim: capacity(감당능력) / attitude(감수태도) 하위차원 정규화용.
# 배점은 원 진단표 컷오프(20/28/36/44/45)에 맞춘 재구성 값 — 총점 13~53.
QUESTIONS: list[dict] = [
    {
        "id": "Q1", "dim": "capacity",
        "text": "여유자금 1,000만 원이 생겼다. 예금과 코인에 나눈다면?",
        "options": [
            {"label": "예금 1,000만 원", "points": 2, "seed": ["composure"]},
            {"label": "예금 700 · 코인 300", "points": 4, "seed": []},
            {"label": "예금 500 · 코인 500", "points": 6, "seed": []},
            {"label": "예금 300 · 코인 700", "points": 8, "seed": ["greed"]},
            {"label": "코인 1,000만 원", "points": 10, "seed": ["greed", "over", "fomo"]},
        ],
    },
    {
        "id": "Q2", "dim": "attitude",
        "text": "이 자금을 얼마 동안 굴릴 생각이야?",
        "options": [
            {"label": "1개월 미만", "points": 1, "seed": ["impatience"]},
            {"label": "1개월 이상 ~ 6개월 미만", "points": 2, "seed": ["impatience"]},
            {"label": "6개월 이상 ~ 1년 미만", "points": 3, "seed": []},
            {"label": "1년 이상 ~ 3년 미만", "points": 4, "seed": []},
            {"label": "3년 이상", "points": 5, "seed": ["patient"]},
        ],
    },
    {
        "id": "Q3", "dim": "capacity",
        "text": "매달 남는 100만 원을 적금과 코인 적립에 나눈다면?",
        "options": [
            {"label": "적금 100만 원", "points": 2, "seed": ["composure"]},
            {"label": "적금 70 · 코인 30", "points": 4, "seed": []},
            {"label": "적금 50 · 코인 50", "points": 6, "seed": []},
            {"label": "적금 30 · 코인 70", "points": 8, "seed": ["greed"]},
            {"label": "코인 100만 원", "points": 10, "seed": ["greed", "over"]},
        ],
    },
    {
        "id": "Q4", "dim": "attitude",
        "text": "자산관리에서 내가 우선하는 순서는?",
        "options": [
            {"label": "안전성 > 유동성 > 수익성", "points": 1, "seed": ["loss_aversion"]},
            {"label": "안전성 > 수익성 > 유동성", "points": 2, "seed": []},
            {"label": "유동성 > 안전성 > 수익성", "points": 3, "seed": []},
            {"label": "유동성 > 수익성 > 안전성", "points": 4, "seed": []},
            {"label": "수익성 > 안전성 > 유동성", "points": 5, "seed": []},
            {"label": "수익성 > 유동성 > 안전성", "points": 6, "seed": ["greed"]},
        ],
    },
    {
        "id": "Q5", "dim": "attitude",
        "text": "가장 선호하는 자산은?",
        "options": [
            {"label": "예금 · 스테이블코인", "points": 2, "seed": ["composure"]},
            {"label": "비트코인 · 이더 같은 우량 코인", "points": 4, "seed": []},
            {"label": "신규 · 알트코인", "points": 6, "seed": ["greed", "fomo"]},
        ],
    },
    {
        "id": "Q6", "dim": "attitude",
        "text": "더 선호하는 투자 전략은?",
        "options": [
            {"label": "분산된 포트폴리오로 시장 평균 정도의 성과", "points": 3, "seed": ["composure"]},
            {"label": "원금 손실 위험이 있어도 시장 평균보다 높은 수익", "points": 6, "seed": ["greed", "over"]},
        ],
    },
    {
        "id": "Q7", "dim": "capacity",
        "text": "투자 손실을 어디까지 견딜 수 있어?",
        "options": [
            {"label": "무슨 일이 있어도 원금은 지켜야 한다", "points": 2, "seed": ["loss_aversion", "fear"]},
            {"label": "10% 미만까지는 감수", "points": 4, "seed": []},
            {"label": "20% 미만까지는 감수", "points": 6, "seed": []},
            {"label": "40% 미만까지는 감수", "points": 8, "seed": ["greed"]},
            {"label": "기대수익이 높다면 위험은 상관없다", "points": 10, "seed": ["over", "greed"]},
        ],
    },
]

_Q = {q["id"]: q for q in QUESTIONS}
_POINTS = {qid: [o["points"] for o in q["options"]] for qid, q in _Q.items()}


# ── 유형 경계 (원 진단표 컷오프) ─────────────────────────────────────────
DECLARED_TYPES: tuple[str, ...] = (
    "안정형", "안정추구형", "위험중립형", "적극투자형", "공격투자형",
)
# (상한, 유형) — 총점 13~53. 20 이하 / 21~28 / 29~36 / 37~44 / 45 이상.
_TYPE_BANDS: tuple[tuple[int, str], ...] = (
    (20, "안정형"),
    (28, "안정추구형"),
    (36, "위험중립형"),
    (44, "적극투자형"),
    (999, "공격투자형"),
)

# 5단계 정의(투자자정보 확인서 표준) — 결과 카드 한 줄 설명.
TYPE_DESC: dict[str, str] = {
    "안정형": "원금 손실을 원치 않는다. 예금 수준의 안정 수익을 기대한다.",
    "안정추구형": "손실은 최소화하되, 이자·배당 이상을 위해 단기 소폭 손실은 감수한다.",
    "위험중립형": "위험과 수익은 비례한다고 본다. 예금+α를 위해 일정 손실을 감수한다.",
    "적극투자형": "원금 보전보다 수익을 우선한다. 상당한 위험을 감수한다.",
    "공격투자형": "시장 수익률을 크게 넘어서길 원한다. 자산가치 변동 손실을 적극 수용한다.",
}

RISK_GRADE_BY_TYPE: dict[str, str] = {
    "안정형": "5등급 이하",
    "안정추구형": "4등급 이하",
    "위험중립형": "3등급 이하",
    "적극투자형": "2등급 이하",
    "공격투자형": "1등급 이하",
}

# 2층 편향 5축 — expected_bias · 선택지 bias_tags(T-47b) · actual_bias(T-47c)의
# 공통 키. 단일 소스: scenario.py·chain.py 검증기가 이걸 import해 태그를 검사한다.
BIAS_AXES: tuple[str, ...] = ("loss", "fomo", "disp", "over", "panic")

# ── 기대값 테이블 — declared_type → 2층 편향 5축 ─────────────────────────
_EXPECTED_BIAS: dict[str, dict[str, int]] = {
    "안정형":     {"loss": 60, "fomo": 20, "disp": 40, "over": 15, "panic": 55},
    "안정추구형": {"loss": 55, "fomo": 30, "disp": 45, "over": 25, "panic": 45},
    "위험중립형": {"loss": 45, "fomo": 45, "disp": 50, "over": 40, "panic": 35},
    "적극투자형": {"loss": 35, "fomo": 60, "disp": 45, "over": 60, "panic": 25},
    "공격투자형": {"loss": 30, "fomo": 75, "disp": 40, "over": 75, "panic": 20},
}

# 하위차원 괴리 임계(점).
SUBDIM_GAP_THRESHOLD: int = 25


# ── 답안 파싱 ───────────────────────────────────────────────────────────
def _mid(qid: str) -> int:
    """문항 중앙값 옵션 점수(누락·무효 폴백, 결정론)."""
    pts = _POINTS[qid]
    return pts[len(pts) // 2]


def _score(answers: dict, qid: str) -> int:
    """qid의 선택 점수. 문항의 유효 옵션 점수가 아니면 중앙값으로 폴백."""
    raw = answers.get(qid)
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return _mid(qid)
    return v if v in _POINTS[qid] else _mid(qid)


def _option_for(qid: str, points: int) -> dict | None:
    for opt in _Q[qid]["options"]:
        if opt["points"] == points:
            return opt
    return None


def _seeds_for(qid: str, points: int) -> list[str]:
    opt = _option_for(qid, points)
    return list(opt["seed"]) if opt else []


# ── 채점 ────────────────────────────────────────────────────────────────
def _dim_bounds(dim: str) -> tuple[int, int]:
    qs = [q for q in QUESTIONS if q["dim"] == dim]
    return (
        sum(min(_POINTS[q["id"]]) for q in qs),
        sum(max(_POINTS[q["id"]]) for q in qs),
    )


def _dim_score(answers: dict, dim: str) -> int:
    qs = [q for q in QUESTIONS if q["dim"] == dim]
    raw = sum(_score(answers, q["id"]) for q in qs)
    lo, hi = _dim_bounds(dim)
    return round((raw - lo) / (hi - lo) * 100) if hi > lo else 50


def score_answers(answers: dict) -> dict:
    """총점 + capacity/attitude 하위점수(0~100 정규화)."""
    return {
        "raw_score": sum(_score(answers, qid) for qid in _Q),
        "capacity_score": _dim_score(answers, "capacity"),
        "attitude_score": _dim_score(answers, "attitude"),
    }


def declared_type(raw_score: int) -> str:
    """총점 → 5단계 유형(원 진단표 컷오프)."""
    for hi, name in _TYPE_BANDS:
        if raw_score <= hi:
            return name
    return DECLARED_TYPES[-1]


def expected_bias(dtype: str) -> dict[str, int]:
    """declared_type → 2층 편향 5축 기대값(리포트 괴리 계산의 기준). 사본 반환."""
    return dict(_EXPECTED_BIAS[dtype])


def collect_seeds(answers: dict) -> tuple[list[str], list[str]]:
    """선택지 seed 수집(중복 제거·순서 보존). seed_conflicts는 현재 없음([])."""
    seeds: list[str] = []
    for qid in _Q:
        for token in _seeds_for(qid, _score(answers, qid)):
            if token not in seeds:
                seeds.append(token)
    return seeds, []


def subdimension_pattern(*, attitude_score: int, capacity_score: int) -> str:
    """하위차원 괴리 패턴. 임계 25점 이상 벌어지면 진단 소재."""
    gap = attitude_score - capacity_score
    if gap >= SUBDIM_GAP_THRESHOLD:
        return "attitude_over_capacity"
    if gap <= -SUBDIM_GAP_THRESHOLD:
        return "capacity_over_attitude"
    if capacity_score >= 60 and attitude_score >= 60:
        return "both_high"
    if capacity_score <= 40 and attitude_score <= 40:
        return "both_low"
    return "balanced"


def diagnose(answers: dict) -> dict:
    """7문항 답 → 진단 결과 전체. 시작 시 1회, 이후 불변."""
    scored = score_answers(answers)
    dtype = declared_type(scored["raw_score"])
    seeds, conflicts = collect_seeds(answers)
    return {
        "answers": {qid: _score(answers, qid) for qid in _Q},
        "raw_score": scored["raw_score"],
        "declared_type": dtype,
        "type_desc": TYPE_DESC[dtype],
        "risk_grade": RISK_GRADE_BY_TYPE[dtype],
        "capacity_score": scored["capacity_score"],
        "attitude_score": scored["attitude_score"],
        "seeds": seeds,
        "seed_conflicts": conflicts,
        "expected_bias": expected_bias(dtype),
        "source": SOURCE,
    }


# ── 감정 초기화 (7문항 → 4부정축) ───────────────────────────────────────
def _n(answers: dict, qid: str) -> float:
    """선택 점수 → 0~1 정규화(문항 최소~최대). 누락은 중립 0.5."""
    if qid not in answers:
        return 0.5
    lo, hi = min(_POINTS[qid]), max(_POINTS[qid])
    return (_score(answers, qid) - lo) / (hi - lo) if hi > lo else 0.5


def _axis(signal: float) -> float:
    """0~1 신호 → 중립 50 중심 초기 감정치 [30,70]."""
    return round(50.0 + (signal - 0.5) * 40.0, 2)


def build_initial_emotion_v2(answers: dict) -> PlayerEmotionState:
    """7문항 답 → 플레이어 초기 감정(결정론). 4부정축만 초기화하고
    **평정(composure)은 중립 50 유지** — 평정은 시장이 아니라 본편의 원칙 있는
    선택으로만 성장하는 지표라 진단으로 선입력하지 않는다.

    매핑(신호가 높을수록 그 감정↑):
      fear         ← 낮은 위험감수(손실허용·자금배분)   : 1−(Q7,Q1)
      greed        ← 공격적 자금배분·손실무관            : (Q1,Q3,Q7)
      anxiety      ← 손실회피·보수 전략·안전 우선        : 1−(Q7,Q6,Q4)
      restlessness ← 단기 호흡 + 알트 선호               : 1−Q2, Q5
    """
    def mean(*xs: float) -> float:
        return sum(xs) / len(xs)

    fear = _axis(mean(1 - _n(answers, "Q7"), 1 - _n(answers, "Q1")))
    greed = _axis(mean(_n(answers, "Q1"), _n(answers, "Q3"), _n(answers, "Q7")))
    anxiety = _axis(mean(1 - _n(answers, "Q7"), 1 - _n(answers, "Q6"), 1 - _n(answers, "Q4")))
    restlessness = _axis(mean(1 - _n(answers, "Q2"), _n(answers, "Q5")))
    return clamp(
        PlayerEmotionState(
            fear=fear, greed=greed, anxiety=anxiety, restlessness=restlessness,
        )  # composure는 기본값(EQUILIBRIUM 50) 유지
    )
