"""T-3: 감정 델타 엔진.

이벤트ID -> {축: 델타값} 데이터 테이블 + 적용 함수(적용 후 T-1 클램핑 재사용).
이벤트 추가/수정은 EVENT_DELTAS 데이터만 바꾸면 된다(코드 변경 불필요).
"""

from __future__ import annotations

from .state import PlayerEmotionState, clamp

# 이벤트ID -> {축: 델타값}. 델타값은 해당 축에 더해진다(음수면 감소).
# 초안: T-9(게시판 강제 노출)의 4종 이벤트(급락/급등/루머/변동) + 시세 확인(restlessness) 대응.
EVENT_DELTAS: dict[str, dict[str, float]] = {
    "market_crash": {"fear": 20, "anxiety": 10},
    "market_surge": {"greed": 20, "restlessness": 10},
    "rumor_spread": {"anxiety": 15},
    "market_volatile": {"restlessness": 15, "anxiety": 5},
    "market_calm": {"fear": -10, "anxiety": -10},
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
    )
    return clamp(updated)


def apply_event(state: PlayerEmotionState, event_id: str) -> PlayerEmotionState:
    """event_id에 연결된 델타를 state에 적용한 새 상태를 반환한다(클램핑 포함, 입력 불변).

    미지의 event_id면 ValueError.
    """
    if event_id not in EVENT_DELTAS:
        raise ValueError(f"unknown player_emotion event_id: {event_id!r}")
    return apply_delta(state, EVENT_DELTAS[event_id])
