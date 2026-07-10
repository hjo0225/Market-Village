"""T-8: 시나리오 데이터 템플릿 로더.

이벤트 카테고리별 텍스트+선택지 6종 풀(§4)+결과 감정 델타를
data/scenario_templates.json에서 읽고 스키마를 검증한다. 선택지 델타의 축은
player_emotion 4축만 허용. 게시판(T-9)·NPC톤(T-10)·턴 루프(T-7)가 공통으로
소비할 콘텐츠 원본.

§4 — 게시판 선택지 6개 풀 → 3개 노출: 각 이벤트는 이제 6개 선택지를 갖고,
버킷(방어 A/D, 관망 B/E, 공격 C/F)에서 1개씩 결정론으로 뽑아 3개를 노출한다
(get_scenario(event_id, seed, day)). seed/day를 안 주면(레거시 호출부·테스트)
버킷 뽑기 없이 6개 전부를 반환한다(하위 호환, I6).
"""

from __future__ import annotations

import json
import random
import zlib
from functools import lru_cache
from pathlib import Path

from .disposition import BIAS_AXES
from .player_emotion.state import AXES

TEMPLATES_PATH = Path(__file__).resolve().parent / "data" / "scenario_templates.json"

# 게시판 강제노출을 트리거하는 시장 이벤트 4종.
EVENT_CATEGORIES = ("market_crash", "market_surge", "rumor_spread", "market_volatile")

# T-53 (F4): 게시판 선택지 = 감정-소모 3액션(매수/매도/유지)으로 대체. 각 시나리오는
# 정확히 3액션(방어=매도/관망=유지/공격=매수 각 1개)을 갖고 전부 노출한다(추첨 없음).
CHOICES_PER_SCENARIO = 3   # 매수/매도/유지
CHOICES_EXPOSED = 3        # 3액션 전부 노출(버킷당 1개)
CHOICES_PER_BUCKET = 1     # 방어(매도)/관망(유지)/공격(매수) 각 1개

# T-53: 3액션. 매수=탐욕 소모·현금→코인(공격), 매도=공포 소모·코인→현금(방어),
# 유지=평정 소모·무매매(관망). action·consume_axis·consume_fraction이 필수 필드.
# 버킷은 position 부호로 판정(_bucket_of): 매도 -0.5=방어, 유지 0.0=관망, 매수 0.4=공격.
ACTIONS = ("buy", "sell", "hold")


class ScenarioError(ValueError):
    """시나리오 데이터가 스키마를 위반하거나 미지의 이벤트를 조회할 때."""


def _bucket_of(position: float) -> str:
    if position <= -0.2:
        return "defense"
    if position >= 0.2:
        return "aggressive"
    return "neutral"


def validate_scenarios(scenarios: dict) -> dict:
    """스키마 검증(위반 시 ScenarioError). 통과하면 입력을 그대로 반환."""
    for cat in EVENT_CATEGORIES:
        if cat not in scenarios:
            raise ScenarioError(f"missing event category: {cat!r}")

    for cat, sc in scenarios.items():
        if cat not in EVENT_CATEGORIES:
            raise ScenarioError(f"unknown event category: {cat!r}")
        # T-56: 시나리오 텍스트는 단일 text 또는 text_variants[](열릴 때마다 변주) 중 하나.
        variants = sc.get("text_variants")
        if variants is not None:
            if not isinstance(variants, list) or not variants or any(
                not str(v).strip() for v in variants
            ):
                raise ScenarioError(f"{cat}: text_variants must be non-empty strings")
        elif not str(sc.get("text", "")).strip():
            raise ScenarioError(f"{cat}: empty text (or provide text_variants)")
        choices = sc.get("choices") or []
        if len(choices) != CHOICES_PER_SCENARIO:
            raise ScenarioError(
                f"{cat}: expected {CHOICES_PER_SCENARIO} choices, got {len(choices)}"
            )
        seen_ids: set[str] = set()
        seen_buckets: dict[str, int] = {"defense": 0, "neutral": 0, "aggressive": 0}
        for ch in choices:
            cid = ch.get("id")
            if not cid or cid in seen_ids:
                raise ScenarioError(f"{cat}: missing or duplicate choice id {cid!r}")
            seen_ids.add(cid)
            if not str(ch.get("label", "")).strip():
                raise ScenarioError(f"{cat}/{cid}: empty label")
            # T-53: 3액션 필수 필드 — action·consume_axis·consume_fraction.
            action = ch.get("action")
            if action not in ACTIONS:
                raise ScenarioError(f"{cat}/{cid}: invalid action {action!r}")
            axis = ch.get("consume_axis")
            if axis not in AXES:
                raise ScenarioError(f"{cat}/{cid}: invalid consume_axis {axis!r}")
            frac = ch.get("consume_fraction")
            if not isinstance(frac, (int, float)) or not 0.0 < float(frac) <= 1.0:
                raise ScenarioError(f"{cat}/{cid}: consume_fraction must be in (0,1]: {frac!r}")
            # T-47b: 선택적 편향 태그. 있으면 5축의 부분집합이어야 한다.
            tags = ch.get("bias_tags")
            if tags is not None:
                if not isinstance(tags, list) or any(t not in BIAS_AXES for t in tags):
                    raise ScenarioError(f"{cat}/{cid}: invalid bias_tags {tags!r}")
            seen_buckets[_bucket_of(float(ch.get("position", 0.0)))] += 1
        # §4.1 — 버킷마다 정확히 2개(기존 1 + 신규 1)라 항상 방어/관망/공격 스펙트럼 보장.
        for bucket, count in seen_buckets.items():
            if count != CHOICES_PER_BUCKET:
                raise ScenarioError(
                    f"{cat}: bucket {bucket!r} expected {CHOICES_PER_BUCKET} choices, got {count}"
                )
    return scenarios


@lru_cache(maxsize=1)
def load_scenarios() -> dict:
    """검증된 시나리오 템플릿을 로드(1회 캐시)."""
    with open(TEMPLATES_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return validate_scenarios(data)


def _pool_rng(seed: int, day: int, event_id: str) -> random.Random:
    return random.Random(zlib.crc32(f"bpick:{seed}:{day}:{event_id}".encode()))


def pick_exposed_choices(all_choices: list[dict], seed: int, day: int, event_id: str) -> list[dict]:
    """§4.2 — 6개 풀에서 버킷(방어/관망/공격)당 1개씩 결정론 추첨해 3개 반환.

    같은 (seed, day, event_id)는 항상 같은 3개(I2/I4). 버킷 소속은 선택지의
    position 부호로 판정(_bucket_of) — id 접두 규약(A/D·B/E·C/F)에 의존하지 않아
    데이터 순서가 바뀌어도 안전하다."""
    rng = _pool_rng(seed, day, event_id)
    by_bucket: dict[str, list[dict]] = {"defense": [], "neutral": [], "aggressive": []}
    for ch in all_choices:
        by_bucket[_bucket_of(float(ch.get("position", 0.0)))].append(ch)
    exposed: list[dict] = []
    for bucket in ("defense", "neutral", "aggressive"):
        options = by_bucket[bucket]
        if not options:
            continue
        exposed.append(rng.choice(options))
    return exposed


def pick_text_variant(variants: list[str], seed: int, day: int, event_id: str) -> str:
    """T-56: TYPE별 시나리오 텍스트 여러 개 중 하나를 (seed, day, event_id)로 결정론
    선택. 같은 날=같은 텍스트(4d 리로드 안전), 다른 날 같은 이벤트=다른 서사(급락도
    매번 다르게). choices 추첨과 독립된 rng 스트림(:text)이라 텍스트·선택지가 따로 변주."""
    rng = _pool_rng(seed, day, event_id + ":text")
    return rng.choice(variants)


def get_scenario(event_id: str, seed: int | None = None, day: int | None = None) -> dict:
    """이벤트 카테고리의 시나리오를 조회. 미지의 event_id면 ScenarioError.

    seed·day를 둘 다 주면 §4.2 3-of-6 노출 선택을 적용한 choices로 교체해
    반환한다(원본 6개는 건드리지 않고 복사본). 하나라도 생략하면(레거시 호출부)
    choices는 6개 전부(하위 호환, I6)."""
    scenarios = load_scenarios()
    if event_id not in scenarios:
        raise ScenarioError(f"unknown event_id: {event_id!r}")
    scenario = scenarios[event_id]
    if seed is None or day is None:
        return scenario
    exposed = pick_exposed_choices(scenario["choices"], seed, day, event_id)
    result = {**scenario, "choices": exposed}
    variants = scenario.get("text_variants")
    if variants:   # T-56 — 열릴 때마다 다른 서사(결정론)
        result["text"] = pick_text_variant(variants, seed, day, event_id)
    return result


def get_choice(event_id: str, choice_id: str) -> dict:
    """시나리오 선택지 하나를 조회(deltas·position 포함, 6개 풀 전부에서). 없으면 ScenarioError."""
    scenarios = load_scenarios()
    if event_id not in scenarios:
        raise ScenarioError(f"unknown event_id: {event_id!r}")
    for ch in scenarios[event_id]["choices"]:
        if ch["id"] == choice_id:
            return ch
    raise ScenarioError(f"unknown choice {choice_id!r} for event {event_id!r}")
