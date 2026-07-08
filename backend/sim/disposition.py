"""T-47a — 정적 성향 진단 (1층 "선언된 자아").

스펙: docs/STATIC_DISPOSITION_SPEC.md
(근거: Grable & Lytton 위험감수척도 1999 각색 + 국내 금융투자상품 5단계.)

게임 시작 전 1회 실시하는 7문항 진단. 플레이어를 5개 유형 중 하나로 배치하고,
리포트의 기대값 테이블(2층 편향 5축)과 seed 플래그를 만든다. **본편에서 바뀌지
않는 기준점**(EmoGameRun.disposition, T-47c에서 배선)이다.

순수함수만 — 상태·IO 없음. 답안(answers)은 {"Q1".."Q7": score(1~4)} 형태
(각 문항 선택지 점수가 유일하므로 점수로 선택지를 역참조해 seed를 얻는다).
"""

from __future__ import annotations

from .player_emotion.state import PlayerEmotionState, clamp

# ── 문항 세트 (스펙 §1) ─────────────────────────────────────────────────
# 각 선택지: score(1~4, 높을수록 위험지향) + seed(예상 편향 힌트, 없으면 []).
# dim: 어느 하위차원(risk_capacity/risk_attitude)에 기여하는지. weight: Q5만 2배.
QUESTIONS: list[dict] = [
    {
        "id": "Q1", "dim": "attitude", "weight": 1,
        "text": "룸메이트가 눈을 반짝이며 말한다. '지금 아니면 못 사. 다들 타는 중이야.' 너라면?",
        "options": [
            {"label": "바로 산다. 기회는 안 기다려준다", "score": 4, "seed": ["greed", "fomo"]},
            {"label": "일단 뭔지 좀 알아본다", "score": 2, "seed": []},
            {"label": "다들 탈 때가 제일 위험하다. 무시", "score": 1, "seed": ["composure"]},
        ],
    },
    {
        "id": "Q2", "dim": "capacity", "weight": 1,
        "text": "투자한 돈이 하루 만에 −30%. 지금 네 심정은?",
        "options": [
            {"label": "기회다. 오히려 더 산다", "score": 4, "seed": ["greed"]},
            {"label": "오를 때까지 버틴다(존버)", "score": 3, "seed": ["anxiety", "disposition_hold"]},
            {"label": "정해둔 선에서 손절한다", "score": 2, "seed": ["composure"]},
            {"label": "밤새 잠을 못 잔다", "score": 1, "seed": ["fear", "anxiety"]},
        ],
    },
    {
        "id": "Q3", "dim": "attitude", "weight": 1,
        "text": "예상 못 한 100만원이 생겼다. 어디에 넣어?",
        "options": [
            {"label": "신규/알트코인에 전부", "score": 4, "seed": ["greed"]},
            {"label": "비트·이더 같은 메이저에", "score": 3, "seed": []},
            {"label": "절반만 투자, 절반은 예금", "score": 2, "seed": []},
            {"label": "전액 예적금", "score": 1, "seed": ["composure"]},
        ],
    },
    {
        "id": "Q4", "dim": "attitude", "weight": 1,
        "text": "너에게 '투자'란 한마디로?",
        "options": [
            {"label": "인생 역전의 기회", "score": 4, "seed": ["greed", "impatience"]},
            {"label": "자산을 불리는 수단", "score": 3, "seed": []},
            {"label": "노후를 위한 준비", "score": 2, "seed": []},
            {"label": "안 잃는 게 최우선", "score": 1, "seed": ["fear"]},
        ],
    },
    {
        "id": "Q5", "dim": "capacity", "weight": 2,  # ★가중 2배★
        "text": "얼마까지 잃어도 네 일상이 흔들리지 않아?",
        "options": [
            {"label": "전액 각오돼 있다", "score": 4, "seed": ["greed", "over"]},
            {"label": "절반 정도까지", "score": 3, "seed": []},
            {"label": "10% 정도까지", "score": 2, "seed": []},
            {"label": "한 푼도 잃기 싫다", "score": 1, "seed": ["fear", "loss_aversion"]},
        ],
    },
    {
        "id": "Q6", "dim": "attitude", "weight": 1,
        "text": "수익이 났다. 넌 언제 팔아?",
        "options": [
            {"label": "목표가까지 안 판다", "score": 4, "seed": ["patient"]},
            {"label": "조금 오르면 바로 익절", "score": 2, "seed": ["disposition_sell", "impatience"]},
            {"label": "원금 회복하는 순간 판다", "score": 1, "seed": ["fear", "disposition_sell"]},
        ],
    },
    {
        "id": "Q7", "dim": "attitude", "weight": 1,
        "text": "코인 결정을 내릴 때 넌 주로 뭘 믿어?",
        "options": [
            {"label": "커뮤니티/인플루언서 분위기", "score": 4, "seed": ["fomo", "herd"]},
            {"label": "유튜브·뉴스의 분석", "score": 3, "seed": []},
            {"label": "내가 직접 조사한 자료", "score": 2, "seed": ["composure"]},
            {"label": "아무도 안 믿는다, 안 한다", "score": 1, "seed": ["fear"]},
        ],
    },
]

_Q = {q["id"]: q for q in QUESTIONS}

# ── 유형 경계 (스펙 §2) ─────────────────────────────────────────────────
DECLARED_TYPES: tuple[str, ...] = (
    "안정형", "안정추구형", "위험중립형", "적극투자형", "공격투자형",
)
# (하한, 상한, 유형) — raw 총점 8~32.
_TYPE_BANDS: tuple[tuple[int, int, str], ...] = (
    (8, 12, "안정형"),
    (13, 17, "안정추구형"),
    (18, 22, "위험중립형"),
    (23, 27, "적극투자형"),
    (28, 32, "공격투자형"),
)

# ── 기대값 테이블 (스펙 §3-①) — declared_type → 2층 편향 5축 ────────────
_EXPECTED_BIAS: dict[str, dict[str, int]] = {
    "안정형":     {"loss": 60, "fomo": 20, "disp": 40, "over": 15, "panic": 55},
    "안정추구형": {"loss": 55, "fomo": 30, "disp": 45, "over": 25, "panic": 45},
    "위험중립형": {"loss": 45, "fomo": 45, "disp": 50, "over": 40, "panic": 35},
    "적극투자형": {"loss": 35, "fomo": 60, "disp": 45, "over": 60, "panic": 25},
    "공격투자형": {"loss": 30, "fomo": 75, "disp": 40, "over": 75, "panic": 20},
}

# 부록 C: 하위차원 괴리 임계(점).
SUBDIM_GAP_THRESHOLD: int = 25


# ── 답안 파싱 ───────────────────────────────────────────────────────────
def _score(answers: dict, qid: str) -> int:
    """qid의 선택 점수(1~4). 누락/무효는 보수적 중립 2로 폴백(결정론)."""
    raw = answers.get(qid)
    try:
        s = int(raw)
    except (TypeError, ValueError):
        return 2
    return s if 1 <= s <= 4 else 2


def _seeds_for(qid: str, score: int) -> list[str]:
    """점수로 선택지를 역참조해 seed 리스트를 얻는다(점수 유일 가정)."""
    for opt in _Q[qid]["options"]:
        if opt["score"] == score:
            return list(opt["seed"])
    return []


# ── 채점 (스펙 §2) ──────────────────────────────────────────────────────
def score_answers(answers: dict) -> dict:
    """raw 총점 + capacity/attitude 하위점수(0~100 정규화)."""
    s = {qid: _score(answers, qid) for qid in _Q}
    raw = s["Q1"] + s["Q2"] + s["Q3"] + s["Q4"] + s["Q5"] * 2 + s["Q6"] + s["Q7"]

    capacity_raw = s["Q2"] + s["Q5"] * 2          # 3~12
    attitude_raw = s["Q1"] + s["Q3"] + s["Q4"] + s["Q6"] + s["Q7"]  # 5~20
    capacity_score = round((capacity_raw - 3) / (12 - 3) * 100)
    attitude_score = round((attitude_raw - 5) / (20 - 5) * 100)
    return {
        "raw_score": raw,
        "capacity_score": capacity_score,
        "attitude_score": attitude_score,
    }


def declared_type(raw_score: int) -> str:
    """raw 총점(8~32) → 5단계 유형. 범위 밖은 양끝으로 클램프."""
    for lo, hi, name in _TYPE_BANDS:
        if raw_score <= hi:
            return name if raw_score >= lo else DECLARED_TYPES[0]
    return DECLARED_TYPES[-1]


def expected_bias(dtype: str) -> dict[str, int]:
    """declared_type → 2층 편향 5축 기대값(리포트 괴리 계산의 기준). 사본 반환."""
    return dict(_EXPECTED_BIAS[dtype])


def collect_seeds(answers: dict) -> tuple[list[str], list[str]]:
    """선택지 seed 수집(중복 제거·순서 보존) + seed_conflicts.

    seed_conflict 'disposition': Q2 존버(disposition_hold) + Q6 급익절
    (disposition_sell) → 선언 단계에서 이미 처분효과가 드러난 조합.
    """
    seeds: list[str] = []
    per_q: dict[str, list[str]] = {}
    for qid in _Q:
        sd = _seeds_for(qid, _score(answers, qid))
        per_q[qid] = sd
        for token in sd:
            if token not in seeds:
                seeds.append(token)

    conflicts: list[str] = []
    if "disposition_hold" in per_q["Q2"] and "disposition_sell" in per_q["Q6"]:
        conflicts.append("disposition")
    return seeds, conflicts


def subdimension_pattern(*, attitude_score: int, capacity_score: int) -> str:
    """부록 C — 하위차원 괴리 패턴. 임계 25점 이상 벌어지면 진단 소재."""
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
    """7문항 답 → 진단 결과 전체(스펙 §4 스키마). 시작 시 1회, 이후 불변."""
    scored = score_answers(answers)
    dtype = declared_type(scored["raw_score"])
    seeds, conflicts = collect_seeds(answers)
    return {
        "answers": {qid: _score(answers, qid) for qid in _Q},
        "raw_score": scored["raw_score"],
        "declared_type": dtype,
        "capacity_score": scored["capacity_score"],
        "attitude_score": scored["attitude_score"],
        "seeds": seeds,
        "seed_conflicts": conflicts,
        "expected_bias": expected_bias(dtype),
    }


# ── 감정 초기화 (7문항 → 4부정축) ───────────────────────────────────────
def _n(answers: dict, qid: str) -> float:
    """점수(1~4) → 0~1 정규화. 누락은 중립 0.5."""
    if qid not in answers:
        return 0.5
    return (_score(answers, qid) - 1) / 3.0


def _axis(signal: float) -> float:
    """0~1 신호 → 중립 50 중심 초기 감정치 [30,70](기존 interview idiom)."""
    return round(50.0 + (signal - 0.5) * 40.0, 2)


def build_initial_emotion_v2(answers: dict) -> PlayerEmotionState:
    """7문항 답 → 플레이어 초기 감정(결정론). 4부정축만 진단으로 초기화하고
    **평정(composure)은 중립 50 유지** — T-37 설계상 평정은 시장이 아니라
    본편의 원칙 있는 선택으로만 성장하는 지표라 진단으로 선입력하지 않는다.

    매핑(신호가 높을수록 그 감정↑):
      fear         ← 낮은 손실허용/손실반응/'안 잃기'  : 1−(Q5,Q2,Q4)
      greed        ← 유혹·배분·손실각오               : (Q1,Q3,Q5)
      anxiety      ← 손실 불안 + 여론 의존             : 1−Q2, Q7
      restlessness ← 즉시행동·역전조급·급익절          : Q1, Q4, 1−Q6
    """
    def mean(*xs: float) -> float:
        return sum(xs) / len(xs)

    fear = _axis(mean(1 - _n(answers, "Q5"), 1 - _n(answers, "Q2"), 1 - _n(answers, "Q4")))
    greed = _axis(mean(_n(answers, "Q1"), _n(answers, "Q3"), _n(answers, "Q5")))
    anxiety = _axis(mean(1 - _n(answers, "Q2"), _n(answers, "Q7")))
    restlessness = _axis(mean(_n(answers, "Q1"), _n(answers, "Q4"), 1 - _n(answers, "Q6")))
    return clamp(
        PlayerEmotionState(
            fear=fear, greed=greed, anxiety=anxiety, restlessness=restlessness,
        )  # composure는 기본값(EQUILIBRIUM 50) 유지
    )
