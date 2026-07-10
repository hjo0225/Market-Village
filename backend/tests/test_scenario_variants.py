"""T-56: 시나리오 텍스트 변주 — TYPE별 여러 서사, 열릴 때마다 결정론 변주.

"급락이라도 열릴 때마다 시나리오가 달라야 한다"(🙋). 같은 날=같은 텍스트(4d 리로드
안전), 다른 날 같은 이벤트=다른 서사. 3액션(메커닉)은 불변, 상황 서사만 변주.
"""
from sim.scenario import get_scenario, load_scenarios, pick_variant_index


def test_every_type_has_multiple_text_variants():
    scenarios = load_scenarios()
    for cat in ("market_crash", "market_surge", "rumor_spread", "market_volatile"):
        assert len(scenarios[cat]["text_variants"]) >= 3, cat


def test_get_scenario_text_comes_from_variants():
    sc = load_scenarios()["market_crash"]
    got = get_scenario("market_crash", seed=1, day=3)["text"]
    assert got in sc["text_variants"]


def test_same_seed_day_gives_same_text_reload_safe():
    # 4d: 같은 날 리로드/리마운트 → 같은 서사(순간이동·이중 방지).
    a = get_scenario("market_crash", seed=7, day=2)["text"]
    b = get_scenario("market_crash", seed=7, day=2)["text"]
    assert a == b


def test_different_days_can_change_the_scenario_text():
    # 급락이 여러 날 열리면 서사가 매번 같지 않다(변주 존재).
    texts = {get_scenario("market_crash", seed=1, day=d)["text"] for d in range(20)}
    assert len(texts) >= 2, f"급락 서사가 20일 내내 동일: {texts}"


def test_text_and_choices_vary_independently():
    # 텍스트 rng(:text)와 선택지 rng가 분리 — 텍스트가 바뀌어도 3액션 id는 불변.
    sc = get_scenario("market_surge", seed=3, day=5)
    assert {c["id"] for c in sc["choices"]} == {"buy", "sell", "hold"}


def test_pick_variant_index_deterministic():
    assert pick_variant_index(4, 1, 5, "x") == pick_variant_index(4, 1, 5, "x")
    assert 0 <= pick_variant_index(4, 1, 5, "x") < 4


def test_choice_labels_vary_by_day_with_consume_spec():
    # T-56: 선택지 문구도 변주 — 급락 매수 버튼이 날마다 다른 문구 + 소모 스펙 유지.
    def buy_label(d: int) -> str:
        chs = get_scenario("market_crash", seed=1, day=d)["choices"]
        return next(c["label"] for c in chs if c["id"] == "buy")
    labels = {buy_label(d) for d in range(20)}
    assert len(labels) >= 2, f"버튼 문구가 20일 내내 동일: {labels}"
    assert all("탐욕" in lab and "소모" in lab for lab in labels)
