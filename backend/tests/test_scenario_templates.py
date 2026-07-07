"""T-8: 시나리오 데이터 템플릿 + 로더 검증.

이벤트 카테고리별 텍스트·선택지 3종·결과 감정 델타가 데이터파일로 존재하고,
로더가 스키마를 검증한다(잘못된 데이터는 거부). 선택지 델타의 축은
player_emotion 4축(fear/greed/anxiety/restlessness)만 허용.
"""

import pytest

from sim.player_emotion.state import AXES
from sim.scenario import (
    EVENT_CATEGORIES,
    ScenarioError,
    get_scenario,
    load_scenarios,
    validate_scenarios,
)


def test_four_event_categories_present():
    scenarios = load_scenarios()
    for cat in ("market_crash", "market_surge", "rumor_spread", "market_volatile"):
        assert cat in scenarios
    assert set(EVENT_CATEGORIES) == set(scenarios)


def test_each_scenario_has_text_and_three_choices():
    scenarios = load_scenarios()
    for cat, sc in scenarios.items():
        assert sc["text"].strip(), f"{cat} 텍스트 비어있음"
        assert len(sc["choices"]) == 3, f"{cat} 선택지 3개 아님"


def test_every_choice_delta_uses_valid_axes():
    scenarios = load_scenarios()
    for cat, sc in scenarios.items():
        for ch in sc["choices"]:
            assert ch["label"].strip()
            assert ch["deltas"], f"{cat}/{ch['id']} 델타 비어있음"
            for axis in ch["deltas"]:
                assert axis in AXES, f"{cat}/{ch['id']} 잘못된 축 {axis!r}"


def test_choice_ids_unique_within_scenario():
    scenarios = load_scenarios()
    for cat, sc in scenarios.items():
        ids = [c["id"] for c in sc["choices"]]
        assert len(ids) == len(set(ids)), f"{cat} 선택지 id 중복"


def test_get_scenario_returns_and_raises():
    assert get_scenario("market_crash")["text"]
    with pytest.raises(ScenarioError):
        get_scenario("nonexistent_event")


def test_validate_rejects_bad_axis():
    bad = {
        "market_crash": {
            "id": "market_crash",
            "text": "x",
            "choices": [
                {"id": "a", "label": "a", "deltas": {"fear": 1}},
                {"id": "b", "label": "b", "deltas": {"nope": 1}},
                {"id": "c", "label": "c", "deltas": {"greed": 1}},
            ],
        }
    }
    with pytest.raises(ScenarioError):
        validate_scenarios(bad)


def test_validate_rejects_wrong_choice_count():
    bad = {
        "market_crash": {
            "id": "market_crash",
            "text": "x",
            "choices": [{"id": "a", "label": "a", "deltas": {"fear": 1}}],
        }
    }
    with pytest.raises(ScenarioError):
        validate_scenarios(bad)
