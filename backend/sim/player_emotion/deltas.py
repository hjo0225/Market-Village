"""T-3: 감정 델타 엔진.

이벤트ID -> {축: 델타값} 데이터 테이블 + 적용 함수(적용 후 T-1 클램핑 재사용).
이벤트 추가/수정은 EVENT_DELTAS 데이터만 바꾸면 된다(코드 변경 불필요).
"""

from __future__ import annotations

from .config import DAILY_DECAY_RATE, EMOTION_ACTION_FLOOR, EQUILIBRIUM
from .state import PlayerEmotionState, clamp, get_axis

# 이벤트ID -> {축: 델타값}. 양방향(pole) 모델 — 감정은 두 극으로 묶인다:
#   위축극 = fear + anxiety (하락장 감정)   /   과열극 = greed + restlessness (상승장 감정)
# 좋은 이벤트(급등)는 과열극 ↑ & 위축극 ↓, 나쁜 이벤트(급락)는 그 반대. 어떤 이벤트도
# 한 방향으로만 밀지 않아 감정이 위아래로 진동한다(포화 방지 — RETRO 4b 평형). 압축판정
# (greed+restlessness)-(fear+anxiety)과 같은 그룹핑이라 일관.
# 4 이벤트는 위축 2(급락·루머) + 과열 2(급등·변동)로 대칭 — 각 축의 4이벤트 합이
# ≈0이라 균등 시장에선 드리프트 없이 평형(감쇠 불요). 이벤트별 리드 축으로 flavor 유지:
# 급락=공포리드, 루머=불안리드, 급등=탐욕리드, 변동=조급리드.
EVENT_DELTAS: dict[str, dict[str, float]] = {
    "market_crash": {"fear": 12, "anxiety": 6, "greed": -9, "restlessness": -9},
    "rumor_spread": {"anxiety": 12, "fear": 4, "greed": -8, "restlessness": -8},
    "market_surge": {"greed": 12, "restlessness": 6, "fear": -9, "anxiety": -9},
    "market_volatile": {"restlessness": 12, "greed": 4, "fear": -8, "anxiety": -8},
    "market_calm": {"fear": -10, "anxiety": -10, "greed": -2, "restlessness": -2},
    "check_portfolio": {"restlessness": 5},
}


def apply_delta(state: PlayerEmotionState, delta: dict[str, float]) -> PlayerEmotionState:
    """임의의 {축: 값} 델타를 state에 더한 새 상태를 반환한다(클램핑 포함, 입력 불변).

    시나리오 선택지 델타(T-8)·게시판 노출(T-9) 등 EVENT_DELTAS 밖의 델타를
    공통 경로로 적용한다. 미지의 축 키는 무시(get 기본 0)."""
    updated = PlayerEmotionState(
        fear=state.fear + delta.get("fear", 0),
        greed=state.greed + delta.get("greed", 0),
        anxiety=state.anxiety + delta.get("anxiety", 0),
        restlessness=state.restlessness + delta.get("restlessness", 0),
        composure=state.composure + delta.get("composure", 0),
    )
    return clamp(updated)


def decay_toward_equilibrium(
    state: PlayerEmotionState,
    rate: float = DAILY_DECAY_RATE,
    equilibrium: float = EQUILIBRIUM,
) -> PlayerEmotionState:
    """T-27 (4b): 각 축을 평형값으로 rate만큼 회귀시킨 새 상태(입력 불변).

    밤사이 감정이 중립으로 일부 가라앉는 모델 — 한 방향 강제입력(반복 매수→greed)이
    클램프 천장까지 램프업하는 것을 막는다(포화 방지). rate=0이면 무회귀(항등)."""
    def d(v: float) -> float:
        return v + rate * (equilibrium - v)
    return clamp(PlayerEmotionState(
        fear=d(state.fear), greed=d(state.greed),
        anxiety=d(state.anxiety), restlessness=d(state.restlessness),
        composure=d(state.composure),
    ))


def consume_amount(state: PlayerEmotionState, axis: str, fraction: float) -> float:
    """T-51: axis의 현재값 × fraction = 소모될 양(상태 불변).

    게시판 액션의 매매 규모 원천 — 감정이 클수록 소모량↑ → 매매↑(감정 비례, 4b).
    fraction은 [0, 1]. 범위 밖이면 ValueError, 미지의 axis면 get_axis가 ValueError."""
    if not 0.0 <= fraction <= 1.0:
        raise ValueError(f"consume fraction must be in [0,1]: {fraction!r}")
    return get_axis(state, axis) * fraction


def consume_axis(
    state: PlayerEmotionState, axis: str, fraction: float
) -> tuple[PlayerEmotionState, float]:
    """T-51: axis를 현재값의 fraction만큼 감산한 새 상태 + 소모량을 반환(입력 불변, 클램프).

    반환 (new_state, consumed). consumed는 T-52 매매 규모 산정에 쓰인다.
    바닥(0)이면 소모량 0·상태 불변(클램프)."""
    amount = consume_amount(state, axis, fraction)
    return apply_delta(state, {axis: -amount}), amount


def can_act_on(
    state: PlayerEmotionState, axis: str, floor: float = EMOTION_ACTION_FLOOR
) -> bool:
    """T-51: 감정이 플로어 이상이어야 그 감정 기반 액션(매수=탐욕/매도=공포/유지=평정)이
    실행 가능하다 — "안 느끼는 감정으론 못 움직인다". 미지의 axis면 ValueError."""
    return get_axis(state, axis) >= floor


def apply_event(state: PlayerEmotionState, event_id: str) -> PlayerEmotionState:
    """event_id에 연결된 델타를 state에 적용한 새 상태를 반환한다(클램핑 포함, 입력 불변).

    미지의 event_id면 ValueError.
    """
    if event_id not in EVENT_DELTAS:
        raise ValueError(f"unknown player_emotion event_id: {event_id!r}")
    return apply_delta(state, EVENT_DELTAS[event_id])
