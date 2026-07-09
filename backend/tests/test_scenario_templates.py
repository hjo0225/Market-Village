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


def test_each_scenario_has_text_and_six_choices():
    # §4.1 — 선택지 풀이 3→6으로 확장(방어/관망/공격 버킷당 2개). 노출은 3개지만
    # (test_scenario_pool.py) 저장된 풀 자체는 6개.
    scenarios = load_scenarios()
    for cat, sc in scenarios.items():
        assert sc["text"].strip(), f"{cat} 텍스트 비어있음"
        assert len(sc["choices"]) == 6, f"{cat} 선택지 6개 아님"


def test_every_choice_delta_uses_valid_axes():
    scenarios = load_scenarios()
    for cat, sc in scenarios.items():
        for ch in sc["choices"]:
            assert ch["label"].strip()
            assert ch["deltas"], f"{cat}/{ch['id']} 델타 비어있음"
            for axis in ch["deltas"]:
                assert axis in AXES, f"{cat}/{ch['id']} 잘못된 축 {axis!r}"


def test_choice_labels_have_no_trap_name_prefix():
    """T-23: 선택지 라벨은 함정명 접두(추격매수 등)를 노출하지 않는다 —
    유독 chase만 '추격매수 —' 접두가 붙어 다른 선택지와 톤이 어긋났다."""
    scenarios = load_scenarios()
    for cat, sc in scenarios.items():
        for ch in sc["choices"]:
            assert "추격매수" not in ch["label"], (
                f"{cat}/{ch['id']} 라벨에 함정명 접두: {ch['label']!r}"
            )
    # chase 선택지는 접두 없이 '놓칠 수 없다'만 남긴다.
    chase = next(c for c in get_scenario("market_surge")["choices"] if c["id"] == "chase")
    assert chase["label"] == "놓칠 수 없다"


def test_buy_choices_are_composite_multi_axis():
    """T-27: 매수류 선택지는 단일 축(greed)이 아니라 여러 축을 복합 변동시킨다 —
    사용자 "구매하면 무조건 탐욕만 오른다"의 해소. 각 매수 선택지는 ≥3축을 건드리고,
    greed 단독 지배(다른 축 합보다 크지 않게)가 아니어야 한다."""
    scenarios = load_scenarios()
    buys = {
        "market_crash": "buy_dip",
        "market_surge": "chase",
        "market_volatile": "day_trade",
    }
    for cat, cid in buys.items():
        ch = next(c for c in scenarios[cat]["choices"] if c["id"] == cid)
        deltas = ch["deltas"]
        moved = [a for a, v in deltas.items() if v != 0]
        assert len(moved) >= 3, f"{cat}/{cid} 복합 아님(축 {moved})"
        greed = abs(deltas.get("greed", 0))
        others = sum(abs(v) for a, v in deltas.items() if a != "greed")
        assert others >= greed, f"{cat}/{cid} greed 단독 지배({deltas})"


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
