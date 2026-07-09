"""T-9: 게시판 강제노출 → 플레이어 감정 델타 (얇은 어댑터).

기존 board_v2.offline_conversation의 게시글/댓글 생성(threads)만 표시용으로
재사용하고, 그 agent_deltas/crowd_delta(삭제예정 NPC fold·crowd_mood 결합부)는
버린다. 노출 자체의 감정 이동은 player_emotion 델타(T-3 apply_event)로, 선택지
결과는 T-8 시나리오 델타로 플레이어 4축에 적용한다.

board_v2를 개조하지 않고 그 위에 얹는 얇은 어댑터라, 기존 board_v2 계약·테스트는
불변이고 T-7 턴 루프 재작성 시 이 어댑터를 배선만 하면 된다.
"""

from __future__ import annotations

import random

from .board_v2 import offline_conversation
from .npc_tone import board_tone_delta
from .player_emotion.deltas import apply_delta, apply_event
from .player_emotion.state import PlayerEmotionState
from .scenario import EVENT_CATEGORIES, get_scenario

# 이벤트 카테고리(T-8) → board_v2 게시판 컨텍스트(_CONTEXT_STANCE/_BOARD_CAST).
EVENT_TO_CONTEXT: dict[str, str] = {
    "market_crash": "fear",
    "market_surge": "greed",
    "rumor_spread": "unrest",
    "market_volatile": "fomo",
}


def render_board(
    event_id: str,
    rng: random.Random,
    drawn_news: list[dict] | None = None,
    *,
    seed: int | None = None,
    day: int | None = None,
) -> dict:
    """순수 표시용 게시판(글+댓글+시나리오). 감정 상태를 변이하지 않는다.

    같은 (event_id, 같은 시드의 rng)면 항상 같은 결과 → GET 멱등·재생 가능
    (PLAN-READY 4d). 미지의 event_id면 ValueError.

    seed·day를 주면(호출자=emo_game.board()) §4.2 3-of-6 풀 선택이 적용된
    choices를 반환한다(get_scenario(event_id, seed, day)). 생략하면(레거시
    호출부) 6개 전부(하위 호환)."""
    if event_id not in EVENT_CATEGORIES:
        raise ValueError(f"unknown board event_id: {event_id!r}")
    context = EVENT_TO_CONTEXT[event_id]
    conv = offline_conversation(context, {}, drawn_news or [], rng)
    scenario = get_scenario(event_id, seed, day)
    return {
        "event_id": event_id,
        "context": context,
        "verdict": conv["verdict"],
        "threads": conv["threads"],
        "scenario": {"text": scenario["text"], "choices": scenario["choices"]},
    }


def exposure_delta(event_id: str, threads: list[dict]) -> dict[str, float]:
    """노출이 플레이어 감정에 적용할 델타 = 이벤트 기본(T-3) + 게시판 톤(T-10).

    상태를 변이하지 않고 델타(dict)만 계산해 반환한다(적용은 호출자가 1회)."""
    from .player_emotion.deltas import EVENT_DELTAS

    delta = dict(EVENT_DELTAS.get(event_id, {}))
    for axis, v in board_tone_delta(threads).items():
        delta[axis] = delta.get(axis, 0.0) + v
    return delta


def build_board_exposure(
    event_id: str,
    emotion_state: PlayerEmotionState,
    rng: random.Random,
    drawn_news: list[dict] | None = None,
) -> dict:
    """render_board + 노출 델타 적용을 한 번에(편의 함수).

    - threads/scenario: render_board 재사용(표시용)
    - emotion_after: 노출 즉시 델타(이벤트 기본 T-3 + 톤 T-10) 적용된 플레이어 상태
    """
    board = render_board(event_id, rng, drawn_news)
    exposed = apply_event(emotion_state, event_id)
    exposed = apply_delta(exposed, board_tone_delta(board["threads"]))
    return {
        **board,
        "emotion_before": emotion_state,
        "emotion_after": exposed,
    }


def apply_choice(
    emotion_state: PlayerEmotionState, event_id: str, choice_id: str
) -> PlayerEmotionState:
    """시나리오 선택지의 결과 델타를 플레이어 상태에 적용한다(클램핑 포함).

    미지의 event_id/choice_id면 ValueError.
    """
    scenario = get_scenario(event_id)
    for ch in scenario["choices"]:
        if ch["id"] == choice_id:
            return apply_delta(emotion_state, ch["deltas"])
    raise ValueError(f"unknown choice {choice_id!r} for event {event_id!r}")
