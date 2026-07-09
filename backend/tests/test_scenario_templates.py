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


def test_each_scenario_has_text_and_three_actions():
    # T-53 (F4): 게시판 선택지 = 감정-소모 3액션(매수/매도/유지). 6개 풀이 아니라
    # 정확히 3개(방어=매도/관망=유지/공격=매수 각 1개)만 저장하고 전부 노출한다.
    scenarios = load_scenarios()
    for cat, sc in scenarios.items():
        assert sc["text"].strip(), f"{cat} 텍스트 비어있음"
        assert len(sc["choices"]) == 3, f"{cat} 선택지 3개(3액션) 아님"
        assert {c["id"] for c in sc["choices"]} == {"buy", "sell", "hold"}, cat


def test_every_choice_uses_valid_action_and_consume_axis():
    # T-53: 게시판 선택지에서 per-choice `deltas`가 제거됐다. 대신 3액션 필수 필드
    # action(buy/sell/hold)·consume_axis(4축 중 1)·consume_fraction((0,1])를 검증.
    scenarios = load_scenarios()
    for cat, sc in scenarios.items():
        for ch in sc["choices"]:
            assert ch["label"].strip()
            assert ch["action"] in ("buy", "sell", "hold"), f"{cat}/{ch['id']} 잘못된 action"
            assert ch["consume_axis"] in AXES, f"{cat}/{ch['id']} 잘못된 consume_axis"
            frac = ch["consume_fraction"]
            assert isinstance(frac, (int, float)) and 0.0 < float(frac) <= 1.0, (
                f"{cat}/{ch['id']} consume_fraction 범위 밖: {frac!r}"
            )


def test_choice_labels_have_no_trap_name_prefix():
    """T-23: 선택지 라벨은 함정명 접두(추격매수 등)를 노출하지 않는다 —
    유독 chase만 '추격매수 —' 접두가 붙어 다른 선택지와 톤이 어긋났다."""
    scenarios = load_scenarios()
    for cat, sc in scenarios.items():
        for ch in sc["choices"]:
            assert "추격매수" not in ch["label"], (
                f"{cat}/{ch['id']} 라벨에 함정명 접두: {ch['label']!r}"
            )
    # T-53: 급등 매수(buy) 라벨도 함정명 접두 없이 '놓칠 수 없다'로 시작한다.
    buy = next(c for c in get_scenario("market_surge")["choices"] if c["id"] == "buy")
    assert buy["label"].startswith("놓칠 수 없다")


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
