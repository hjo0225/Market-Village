"""T-8: 시나리오 데이터 템플릿 로더.

이벤트 카테고리별 텍스트+선택지 3종+결과 감정 델타를 data/scenario_templates.json
에서 읽고 스키마를 검증한다. 선택지 델타의 축은 player_emotion 4축만 허용.
게시판(T-9)·NPC톤(T-10)·턴 루프(T-7)가 공통으로 소비할 콘텐츠 원본.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .player_emotion.state import AXES

TEMPLATES_PATH = Path(__file__).resolve().parent / "data" / "scenario_templates.json"

# 게시판 강제노출을 트리거하는 시장 이벤트 4종.
EVENT_CATEGORIES = ("market_crash", "market_surge", "rumor_spread", "market_volatile")

CHOICES_PER_SCENARIO = 3


class ScenarioError(ValueError):
    """시나리오 데이터가 스키마를 위반하거나 미지의 이벤트를 조회할 때."""


def validate_scenarios(scenarios: dict) -> dict:
    """스키마 검증(위반 시 ScenarioError). 통과하면 입력을 그대로 반환."""
    for cat in EVENT_CATEGORIES:
        if cat not in scenarios:
            raise ScenarioError(f"missing event category: {cat!r}")

    for cat, sc in scenarios.items():
        if cat not in EVENT_CATEGORIES:
            raise ScenarioError(f"unknown event category: {cat!r}")
        if not str(sc.get("text", "")).strip():
            raise ScenarioError(f"{cat}: empty text")
        choices = sc.get("choices") or []
        if len(choices) != CHOICES_PER_SCENARIO:
            raise ScenarioError(
                f"{cat}: expected {CHOICES_PER_SCENARIO} choices, got {len(choices)}"
            )
        seen_ids: set[str] = set()
        for ch in choices:
            cid = ch.get("id")
            if not cid or cid in seen_ids:
                raise ScenarioError(f"{cat}: missing or duplicate choice id {cid!r}")
            seen_ids.add(cid)
            if not str(ch.get("label", "")).strip():
                raise ScenarioError(f"{cat}/{cid}: empty label")
            deltas = ch.get("deltas") or {}
            if not deltas:
                raise ScenarioError(f"{cat}/{cid}: empty deltas")
            for axis in deltas:
                if axis not in AXES:
                    raise ScenarioError(f"{cat}/{cid}: invalid axis {axis!r}")
    return scenarios


@lru_cache(maxsize=1)
def load_scenarios() -> dict:
    """검증된 시나리오 템플릿을 로드(1회 캐시)."""
    with open(TEMPLATES_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return validate_scenarios(data)


def get_scenario(event_id: str) -> dict:
    """이벤트 카테고리의 시나리오를 조회. 미지의 event_id면 ScenarioError."""
    scenarios = load_scenarios()
    if event_id not in scenarios:
        raise ScenarioError(f"unknown event_id: {event_id!r}")
    return scenarios[event_id]
