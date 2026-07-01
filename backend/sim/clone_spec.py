"""§5.5 클론 스펙 — 인터뷰 답변을 게임 로직이 받아먹는 규격으로 변환.

복제가 얕으면 그 위 모든 것이 무너진다(§5 최우선 깊이). 인터뷰 답변에서 6함정
취약점·뉴스톤 계수·합리화 언어·고유 이벤트를 **결정론**으로 산출한다(같은 답=같은
스펙 → 거울 정확도). 점수 판단을 LLM에 위임할 수도 있으나(§5.3.2), v1은 결정론
규칙으로 충분하고 회차 재현성(기둥3)에 유리하다.

interview.build_player_persona(5축 Persona)와 별개의 dataclass로 둔다(모델 변경
없이 가산 → 회귀 위험 0). 두 산출물은 같은 답변을 공유한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import tuning as T


def _num(answers: dict, key: str, default: float = 0.5) -> float:
    try:
        return float(answers.get(key))
    except (TypeError, ValueError):
        return default


# 함정별 합리화 언어(§5.1 3층) — 무너지며 자기에게 하는 말. 거울 모먼트의 핵심.
_RATIONALIZATION: dict[str, list[str]] = {
    "F1": ["지금 안 팔면 더 떨어져, 일단 살리자", "손절도 실력이야"],
    "F2": ["계속 빠지네… 그냥 정리하고 마음 편하자", "이 종목은 글렀어"],
    "G1": ["본전 생각하면 아직 못 팔지", "조금만 더 오르면 그때 팔자"],
    "G2": ["이건 확실해, 다 걸어도 돼", "분산은 수익을 깎을 뿐이야"],
    "M1": ["이번엔 진짜 막차야, 지금이라도 타자", "남들 다 버는데 나만 빠질 순 없어"],
    "M2": ["다들 사는데는 이유가 있겠지", "지금 안 사면 바보 되는 거야"],
}


@dataclass
class CloneSpec:
    trap_scores: dict[str, float] = field(default_factory=dict)       # F1..M2 0~100
    news_tone_coef: dict[str, float] = field(default_factory=dict)    # 0.5~1.5
    confirmation_bias: float = 50.0                                   # §8.4 (루머)
    rationalization: dict[str, list[str]] = field(default_factory=dict)
    unique_events: list[dict] = field(default_factory=list)


def _unique_events(panic: float, fomo: float, check: float, rumor: float) -> list[dict]:
    """§5.4 — 각 답변이 클론만의 고유 이벤트 카드가 된다."""
    events: list[dict] = []
    if panic >= 0.66:
        events.append({"id": "shaky_hands", "trigger": "손실 본 날 아침 커피 쏟음",
                       "effect": "멘탈 급락, 충동 매매 확률↑"})
    if fomo >= 0.66:
        events.append({"id": "neighbor_car", "trigger": "게시판 수익 인증 노출",
                       "effect": "FOMO 게이지 폭발"})
    if check >= 0.66:
        events.append({"id": "midnight_chart", "trigger": "새벽에 혼자 차트 봄",
                       "effect": "피로 누적, 멘탈마모 게이지↑"})
    if rumor >= 0.66:
        events.append({"id": "whisper", "trigger": "출처 불명 귓속말",
                       "effect": "확증편향 잠금 강화"})
    if not events:
        # 폴백: 모든 클론은 적어도 하나의 고유 이벤트를 갖는다(§5.4).
        events.append({"id": "ordinary_day", "trigger": "평범한 하루",
                       "effect": "감정 미동"})
    return events


def build_clone_spec(answers: dict) -> CloneSpec:
    """인터뷰 답변 → 클론 스펙(결정론). 빈 답은 중립 폴백."""
    panic = _num(answers, "q_panic")
    fomo = _num(answers, "q_fomo")
    rumor = _num(answers, "q_rumor")
    check = _num(answers, "q_check")
    # 무경험자는 시점선호로 충동성 보정(interview와 동일 규칙).
    if answers.get("q_experience") == "none":
        tp = _num(answers, "q_time_pref")
        panic = (panic + tp) / 2
        fomo = (fomo + tp) / 2

    def pct(x: float) -> float:
        return T.clamp(x * 100.0, 0.0, 100.0)

    trap_scores = {
        "F1": pct(panic),                          # 급락 패닉
        "F2": pct(0.6 * panic + 0.4 * check),       # 멘탈 마모
        "G1": pct(0.8 * fomo),                     # 익절 거부
        "G2": pct(0.7 * fomo),                     # 과대 베팅
        "M1": pct(fomo),                           # 추격 매수
        "M2": pct(0.5 * fomo + 0.5 * check),        # 막차 불안
    }

    # 뉴스톤 계수 0.5~1.5 (§5.5): 해당 톤에 약할수록 1.5에 가까움. 빈 답이면 1.0.
    lo, hi = T.NEWS_COEF_RANGE  # (0.5, 1.5)
    def coef(x: float) -> float:
        return round(lo + (hi - lo) * x, 4)
    news_tone_coef = {
        "fear": coef(panic),
        "optimism": coef(fomo),
        "uncertain": coef(check),
    }

    return CloneSpec(
        trap_scores=trap_scores,
        news_tone_coef=news_tone_coef,
        confirmation_bias=pct(rumor),
        rationalization={k: list(v) for k, v in _RATIONALIZATION.items()},
        unique_events=_unique_events(panic, fomo, check, rumor),
    )
