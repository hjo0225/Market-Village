"""정적 성향 진단 (1층 "선언된 자아").

성향분석.md 정본: 겉은 MBTI 스타일 4축/16타입, 속은 국내 투자자정보 확인서의
합산 점수 → 5단계 투자성향 판정이다. 게임 본편은 기존 declared_type(5유형)과
expected_bias 파이프라인을 그대로 재사용하고, mbti_* 필드는 표현 레이어로만 쓴다.

순수함수만 — 상태·IO 없음. 답안(answers)은 {"Q1".."Q12": score(1~4)} 형태
(각 문항 선택지 점수가 유일하므로 점수로 선택지를 역참조해 seed/axis를 얻는다).
"""

from __future__ import annotations

from .player_emotion.state import PlayerEmotionState, clamp

# ── 문항 세트 (스펙 §1) ─────────────────────────────────────────────────
# 각 선택지: score(1~4, 높을수록 위험지향) + axis 극성 + seed.
# dim: 하위차원 정규화용. weight: 손실감내도(Q3)만 2배.
QUESTIONS: list[dict] = [
    {
        "id": "Q1", "axis": "AS", "dim": "attitude", "weight": 1,
        "text": "룸메이트가 눈을 반짝이며 말한다. '지금 아니면 못 사. 다들 타는 중이야.' 너라면?",
        "options": [
            {"label": "바로 산다. 기회는 안 기다려준다", "score": 4, "pole": 1, "seed": ["greed", "fomo"]},
            {"label": "일단 판을 보고 소액만 담근다", "score": 2, "pole": -1, "seed": []},
            {"label": "다들 탈 때가 제일 위험하다. 무시", "score": 1, "pole": -1, "seed": ["composure"]},
        ],
    },
    {
        "id": "Q2", "axis": "AS", "dim": "attitude", "weight": 1,
        "text": "투자한 돈이 하루 만에 −30%. 지금 네 심정은?",
        "options": [
            {"label": "기회다. 오히려 더 산다", "score": 4, "pole": 1, "seed": ["greed", "over"]},
            {"label": "오를 때까지 버틴다", "score": 3, "pole": 1, "seed": ["anxiety", "disposition_hold"]},
            {"label": "정해둔 선에서 손절한다", "score": 2, "pole": -1, "seed": ["composure"]},
            {"label": "밤새 잠을 못 잔다", "score": 1, "pole": -1, "seed": ["fear", "anxiety"]},
        ],
    },
    {
        "id": "Q3", "axis": "AS", "dim": "attitude", "weight": 2,
        "text": "얼마까지 잃어도 네 일상이 흔들리지 않아?",
        "options": [
            {"label": "전액 각오돼 있다", "score": 4, "pole": 1, "seed": ["greed", "over"]},
            {"label": "절반 정도까지", "score": 3, "pole": 1, "seed": []},
            {"label": "10% 정도까지", "score": 2, "pole": -1, "seed": []},
            {"label": "한 푼도 잃기 싫다", "score": 1, "pole": -1, "seed": ["fear", "loss_aversion"]},
        ],
    },
    {
        "id": "Q4", "axis": "LQ", "dim": "attitude", "weight": 1,
        "text": "투자 가능 기간을 고르라면 가장 가까운 쪽은?",
        "options": [
            {"label": "3년 이상 묻어둘 수 있다", "score": 4, "pole": 1, "seed": ["patient"]},
            {"label": "1년쯤은 기다릴 수 있다", "score": 3, "pole": 1, "seed": []},
            {"label": "몇 달 안에 결과를 보고 싶다", "score": 2, "pole": -1, "seed": ["impatience"]},
            {"label": "6개월도 길다", "score": 1, "pole": -1, "seed": ["impatience"]},
        ],
    },
    {
        "id": "Q5", "axis": "LQ", "dim": "attitude", "weight": 1,
        "text": "수익이 났다. 넌 언제 팔아?",
        "options": [
            {"label": "목표가까지 안 판다", "score": 4, "pole": 1, "seed": ["patient"]},
            {"label": "분할로 조금씩 줄인다", "score": 3, "pole": 1, "seed": []},
            {"label": "조금 오르면 바로 익절", "score": 2, "pole": -1, "seed": ["disposition_sell", "impatience"]},
            {"label": "원금 회복하는 순간 판다", "score": 1, "pole": -1, "seed": ["fear", "disposition_sell"]},
        ],
    },
    {
        "id": "Q6", "axis": "LQ", "dim": "attitude", "weight": 1,
        "text": "예상 못 한 100만원이 생겼다. 어디에 넣어?",
        "options": [
            {"label": "분산해서 천천히 옮긴다", "score": 3, "pole": 1, "seed": []},
            {"label": "장기 보유할 메이저에 넣는다", "score": 2, "pole": 1, "seed": []},
            {"label": "오늘 뜨는 신규/알트코인에 전부", "score": 4, "pole": -1, "seed": ["greed", "fomo"]},
            {"label": "일단 현금으로 두고 기회를 본다", "score": 1, "pole": -1, "seed": ["composure"]},
        ],
    },
    {
        "id": "Q7", "axis": "DF", "dim": "knowledge", "weight": 1,
        "text": "코인 결정을 내릴 때 넌 주로 뭘 믿어?",
        "options": [
            {"label": "내가 직접 조사한 자료", "score": 3, "pole": 1, "seed": ["composure"]},
            {"label": "재무·온체인·차트를 같이 본다", "score": 4, "pole": 1, "seed": ["composure"]},
            {"label": "커뮤니티/인플루언서 분위기", "score": 2, "pole": -1, "seed": ["fomo", "herd"]},
            {"label": "지인이 좋다 하면 일단 본다", "score": 1, "pole": -1, "seed": ["fomo", "herd"]},
        ],
    },
    {
        "id": "Q8", "axis": "DF", "dim": "knowledge", "weight": 1,
        "text": "새 상품 설명서를 받았다. 이해도는 어느 쪽에 가까워?",
        "options": [
            {"label": "구조와 수수료까지 대체로 읽힌다", "score": 4, "pole": 1, "seed": ["composure"]},
            {"label": "핵심 위험 정도는 파악한다", "score": 3, "pole": 1, "seed": []},
            {"label": "수익 예시만 눈에 들어온다", "score": 2, "pole": -1, "seed": ["greed"]},
            {"label": "설명보다 분위기가 더 중요하다", "score": 1, "pole": -1, "seed": ["herd"]},
        ],
    },
    {
        "id": "Q9", "axis": "DF", "dim": "knowledge", "weight": 1,
        "text": "매수 버튼을 누르기 직전 마지막으로 확인하는 것은?",
        "options": [
            {"label": "내 기준표와 손절/익절 규칙", "score": 4, "pole": 1, "seed": ["composure"]},
            {"label": "가격·거래량·뉴스의 일관성", "score": 3, "pole": 1, "seed": []},
            {"label": "실시간 채팅방의 온도", "score": 2, "pole": -1, "seed": ["herd"]},
            {"label": "놓치면 후회할 것 같은 느낌", "score": 1, "pole": -1, "seed": ["fomo"]},
        ],
    },
    {
        "id": "Q10", "axis": "RE", "dim": "capacity", "weight": 1,
        "text": "금융자산 중 투자에 넣어도 된다고 느끼는 비중은?",
        "options": [
            {"label": "40% 초과도 감당 가능하다", "score": 4, "pole": -1, "seed": ["over"]},
            {"label": "20~40% 정도", "score": 3, "pole": -1, "seed": []},
            {"label": "10~20% 정도", "score": 2, "pole": 1, "seed": []},
            {"label": "10% 이내만", "score": 1, "pole": 1, "seed": ["composure"]},
        ],
    },
    {
        "id": "Q11", "axis": "RE", "dim": "capacity", "weight": 1,
        "text": "수입원이 흔들릴 때 투자 계획은?",
        "options": [
            {"label": "그래도 승부금은 유지한다", "score": 4, "pole": -1, "seed": ["over"]},
            {"label": "기회가 확실하면 더 넣는다", "score": 3, "pole": -1, "seed": ["greed"]},
            {"label": "생활비와 비상금을 먼저 잠근다", "score": 2, "pole": 1, "seed": ["composure"]},
            {"label": "투자를 멈추고 현금을 확보한다", "score": 1, "pole": 1, "seed": ["fear"]},
        ],
    },
    {
        "id": "Q12", "axis": "RE", "dim": "capacity", "weight": 1,
        "text": "너에게 '투자'란 한마디로?",
        "options": [
            {"label": "인생 역전의 기회", "score": 4, "pole": -1, "seed": ["greed", "impatience"]},
            {"label": "빠르게 판을 키우는 도구", "score": 3, "pole": -1, "seed": ["over"]},
            {"label": "자산을 불리는 수단", "score": 2, "pole": 1, "seed": []},
            {"label": "생활을 지키는 장기 준비", "score": 1, "pole": 1, "seed": ["composure"]},
        ],
    },
]

_Q = {q["id"]: q for q in QUESTIONS}

# ── 유형 경계 (스펙 §2) ─────────────────────────────────────────────────
DECLARED_TYPES: tuple[str, ...] = (
    "안정형", "안정추구형", "위험중립형", "적극투자형", "공격투자형",
)
# (하한, 상한, 유형) — raw 총점 13~52.
_TYPE_BANDS: tuple[tuple[int, int, str], ...] = (
    (13, 20, "안정형"),
    (21, 28, "안정추구형"),
    (29, 36, "위험중립형"),
    (37, 44, "적극투자형"),
    (45, 52, "공격투자형"),
)

_AXES: dict[str, tuple[str, str, str]] = {
    "AS": ("A", "S", "위험 태도"),
    "LQ": ("L", "Q", "시계"),
    "DF": ("D", "F", "판단 근거"),
    "RE": ("R", "E", "자금 여력"),
}

_MBTI_META: dict[str, dict[str, str]] = {
    "ALDR": {"name": "냉혈 설계자", "summary": "긴 호흡과 숫자로 판을 설계하고, 여유자금 안에서 움직인다.", "good": "SQFR", "bad": "AQFE"},
    "ALDE": {"name": "장기 엔진", "summary": "데이터를 믿고 오래 끌고 가지만, 베팅 크기는 과감해질 수 있다.", "good": "SLDR", "bad": "SQFR"},
    "ALFR": {"name": "낭만 설계자", "summary": "큰 방향감은 길게 보되, 확신의 출처가 사람과 분위기에 자주 흔들린다.", "good": "AQDR", "bad": "SQDE"},
    "ALFE": {"name": "확신형 장투러", "summary": "오래 버티는 힘은 강하지만, 한 번 꽂히면 자금까지 밀어 넣는다.", "good": "SLDR", "bad": "SQDR"},
    "AQDR": {"name": "전술 스나이퍼", "summary": "짧은 기회도 데이터로 쪼개 보고, 현금 방어선은 지키려 한다.", "good": "ALFR", "bad": "SLFE"},
    "AQDE": {"name": "단타 엔지니어", "summary": "속도와 분석을 함께 쓰지만, 포지션 크기가 쉽게 커진다.", "good": "SLDR", "bad": "SQFR"},
    "AQFR": {"name": "뉴스 추격자", "summary": "빠르게 움직이고 시장 온도도 잘 읽지만, 예비 현금은 남겨둔다.", "good": "ALDR", "bad": "SLDE"},
    "AQFE": {"name": "불나방", "summary": "뜨거운 신호에 빠르게 반응하고, 한 번 타면 크게 싣는 편이다.", "good": "SLDR", "bad": "SQDR"},
    "SLDR": {"name": "돌다리 감별사", "summary": "천천히 확인하고 숫자로 검증하며, 생활 방어선을 먼저 세운다.", "good": "AQFE", "bad": "ALFE"},
    "SLDE": {"name": "신중한 탐험가", "summary": "장기 데이터는 보지만, 기회가 보이면 계획보다 크게 들어갈 수 있다.", "good": "AQFR", "bad": "ALFR"},
    "SLFR": {"name": "평온한 저축가", "summary": "오래 보고 천천히 움직이며, 감으로 고르더라도 여유를 남긴다.", "good": "AQDE", "bad": "ALDE"},
    "SLFE": {"name": "느긋한 모험가", "summary": "서두르진 않지만, 마음이 움직이면 생각보다 크게 싣는다.", "good": "SQDR", "bad": "AQDR"},
    "SQDR": {"name": "체크리스트 방어수", "summary": "짧게 확인하고 빠르게 정리하되, 기준표와 현금선을 놓지 않는다.", "good": "SLFE", "bad": "AQFE"},
    "SQDE": {"name": "안전벨트 스캘퍼", "summary": "보수적인 성향에 빠른 매매를 섞고, 데이터로 과감함을 정당화한다.", "good": "ALFR", "bad": "SLFR"},
    "SQFR": {"name": "분위기 관망러", "summary": "시장 소음은 듣지만 크게 던지기보다 짧게 확인하고 빠진다.", "good": "ALDE", "bad": "AQDE"},
    "SQFE": {"name": "소심한 돌격대", "summary": "불안해서 빨리 움직이지만, 막상 꽂히면 방어선이 얇아진다.", "good": "ALDR", "bad": "SLDR"},
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


def _option_for(qid: str, score: int) -> dict | None:
    for opt in _Q[qid]["options"]:
        if opt["score"] == score:
            return opt
    return None


# ── 채점 (스펙 §2) ──────────────────────────────────────────────────────
def score_answers(answers: dict) -> dict:
    """raw 총점 + capacity/attitude 하위점수(0~100 정규화)."""
    s = {qid: _score(answers, qid) for qid in _Q}
    raw = sum(s[qid] * int(q["weight"]) for qid, q in _Q.items())

    capacity_q = [q for q in QUESTIONS if q["dim"] == "capacity"]
    attitude_q = [q for q in QUESTIONS if q["dim"] == "attitude"]
    capacity_raw = sum(s[q["id"]] * int(q["weight"]) for q in capacity_q)
    attitude_raw = sum(s[q["id"]] * int(q["weight"]) for q in attitude_q)
    capacity_min = sum(int(q["weight"]) for q in capacity_q)
    capacity_max = sum(4 * int(q["weight"]) for q in capacity_q)
    attitude_min = sum(int(q["weight"]) for q in attitude_q)
    attitude_max = sum(4 * int(q["weight"]) for q in attitude_q)
    capacity_score = round((capacity_raw - capacity_min) / (capacity_max - capacity_min) * 100)
    attitude_score = round((attitude_raw - attitude_min) / (attitude_max - attitude_min) * 100)
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


def mbti_type(answers: dict) -> dict:
    """12문항 답 → 4축 문자 코드와 표시 메타. 게임 로직 분기는 하지 않는다."""
    axis_sum: dict[str, int] = {axis: 0 for axis in _AXES}
    for qid, q in _Q.items():
        opt = _option_for(qid, _score(answers, qid))
        axis_sum[q["axis"]] += int(opt["pole"]) if opt else -1

    code = ""
    axis_detail: dict[str, dict] = {}
    for axis, total in axis_sum.items():
        left, right, label = _AXES[axis]
        left_pct = round((total + 3) / 6 * 100)
        right_pct = 100 - left_pct
        code += left if total > 0 else right
        axis_detail[axis] = {
            "label": label,
            "left": left,
            "right": right,
            "left_pct": left_pct,
            "right_pct": right_pct,
            "selected": left if total > 0 else right,
        }

    meta = _MBTI_META[code]
    return {"code": code, "axes": axis_detail, **meta}


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
    if "disposition_hold" in per_q["Q2"] and "disposition_sell" in per_q["Q5"]:
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
    """12문항 답 → 진단 결과 전체. 시작 시 1회, 이후 불변."""
    scored = score_answers(answers)
    dtype = declared_type(scored["raw_score"])
    seeds, conflicts = collect_seeds(answers)
    mtype = mbti_type(answers)
    return {
        "answers": {qid: _score(answers, qid) for qid in _Q},
        "raw_score": scored["raw_score"],
        "declared_type": dtype,
        "risk_grade": RISK_GRADE_BY_TYPE[dtype],
        "capacity_score": scored["capacity_score"],
        "attitude_score": scored["attitude_score"],
        "mbti_type": mtype["code"],
        "mbti_name": mtype["name"],
        "mbti_summary": mtype["summary"],
        "mbti_axes": mtype["axes"],
        "mbti_good_match": mtype["good"],
        "mbti_bad_match": mtype["bad"],
        "seeds": seeds,
        "seed_conflicts": conflicts,
        "expected_bias": expected_bias(dtype),
    }


# ── 감정 초기화 (12문항 → 4부정축) ──────────────────────────────────────
def _n(answers: dict, qid: str) -> float:
    """점수(1~4) → 0~1 정규화. 누락은 중립 0.5."""
    if qid not in answers:
        return 0.5
    return (_score(answers, qid) - 1) / 3.0


def _axis(signal: float) -> float:
    """0~1 신호 → 중립 50 중심 초기 감정치 [30,70](기존 interview idiom)."""
    return round(50.0 + (signal - 0.5) * 40.0, 2)


def build_initial_emotion_v2(answers: dict) -> PlayerEmotionState:
    """12문항 답 → 플레이어 초기 감정(결정론). 4부정축만 진단으로 초기화하고
    **평정(composure)은 중립 50 유지** — T-37 설계상 평정은 시장이 아니라
    본편의 원칙 있는 선택으로만 성장하는 지표라 진단으로 선입력하지 않는다.

    매핑(신호가 높을수록 그 감정↑):
      fear         ← 낮은 손실허용/손실반응/현금확보     : 1−(Q3,Q2,Q11)
      greed        ← 유혹·배분·역전욕망                 : (Q1,Q10,Q12)
      anxiety      ← 손실 불안 + 여론 의존               : 1−Q2, 1−Q7, 1−Q9
      restlessness ← 단기호흡·급익절·FOMO                : 1−Q4, 1−Q5, Q1
    """
    def mean(*xs: float) -> float:
        return sum(xs) / len(xs)

    fear = _axis(mean(1 - _n(answers, "Q3"), 1 - _n(answers, "Q2"), 1 - _n(answers, "Q11")))
    greed = _axis(mean(_n(answers, "Q1"), _n(answers, "Q10"), _n(answers, "Q12")))
    anxiety = _axis(mean(1 - _n(answers, "Q2"), 1 - _n(answers, "Q7"), 1 - _n(answers, "Q9")))
    restlessness = _axis(mean(1 - _n(answers, "Q4"), 1 - _n(answers, "Q5"), _n(answers, "Q1")))
    return clamp(
        PlayerEmotionState(
            fear=fear, greed=greed, anxiety=anxiety, restlessness=restlessness,
        )  # composure는 기본값(EQUILIBRIUM 50) 유지
    )
