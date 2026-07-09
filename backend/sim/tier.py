"""§C2 — 통제 티어(목표 위젯). 신규 모듈.

score는 **기존 지표만 재사용**(새 수식 금지, 스펙 §C2): verdict가 쓰는
compute_score(감정 압축 편차)와 ending.py가 쓰는 composure(평정/자기통제) +
special_event_count 보너스. 새 저장 상태 없음 — 매 호출 `_state()`에서
현재 emotion/special_event_count로부터 파생한다(결정론·멱등).

5티어: 새싹 → 불개미 졸업 → 평정 수련 → 강철 멘탈 → 마을의 현자.
"""

from __future__ import annotations

from .player_emotion.state import PlayerEmotionState
from .player_emotion.verdict import compute_score

# 특수이벤트(체인 완주 등) 1회당 티어 점수 보너스. 새 상태 없이 기존
# special_event_count(EmoGameRun)를 그대로 재사용.
_SPECIAL_EVENT_BONUS = 3.0

# compute_score(=(greed+restlessness)-(fear+anxiety))의 절대값(편차)이 클수록
# 감정이 한쪽으로 쏠렸다는 뜻 — 이 편차를 이 배율만큼 감점(축소해 composure와
# 같은 스케일 0~100대에 놓는다).
_DEVIATION_PENALTY_SCALE = 0.25

# (하한 점수, 이름, 아이콘) — score >= 하한이면 그 티어. 오름차순.
_TIERS: tuple[tuple[float, str, str], ...] = (
    (0.0, "새싹", "🌱"),
    (35.0, "불개미 졸업", "🐜"),
    (55.0, "평정 수련", "🧘"),
    (72.0, "강철 멘탈", "🛡️"),
    (88.0, "마을의 현자", "🧙"),
)


def tier_score(emotion: PlayerEmotionState, special_event_count: int) -> float:
    """감정 통제 점수(0~100대, 상한 클램프 없음 — 표시 시 소비자가 처리).

    = composure(자기통제, ending.emotion_controlled와 같은 지표)
      − |compute_score(emotion)| × 축소배율(편차가 크면 감점, verdict와 같은 지표)
      + special_event_count × 보너스.
    """
    deviation = abs(compute_score(emotion))
    score = emotion.composure - deviation * _DEVIATION_PENALTY_SCALE
    score += special_event_count * _SPECIAL_EVENT_BONUS
    return max(0.0, round(score, 2))


def tier_for_score(score: float) -> dict:
    """점수 → {"name","icon","score","next_at"}. next_at은 다음 티어 하한
    (최고 티어면 None — 더 오를 곳 없음)."""
    current = _TIERS[0]
    next_at: float | None = None
    for i, (threshold, name, icon) in enumerate(_TIERS):
        if score >= threshold:
            current = (threshold, name, icon)
            next_at = _TIERS[i + 1][0] if i + 1 < len(_TIERS) else None
        else:
            break
    _, name, icon = current
    return {"name": name, "icon": icon, "score": score, "next_at": next_at}


def compute_tier(emotion: PlayerEmotionState, special_event_count: int) -> dict:
    """§C2 — `_state()`가 노출할 tier 전체(결정론·저장 없음)."""
    score = tier_score(emotion, special_event_count)
    return tier_for_score(score)


TIER_NAMES: tuple[str, ...] = tuple(name for _, name, _ in _TIERS)
