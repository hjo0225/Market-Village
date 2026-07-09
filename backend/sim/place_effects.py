"""§2 일과 편성(플랜) — 장소별 행동력 비용 + 기본 감정 효과 (신규 모듈).

`emo_game._ROUTE_CYCLE`의 실제 장소 이름을 그대로 재사용한다(카페/광장/펍/
일터/운동/마켓/도서관) + 집(휴식, 비용 0). 값의 크기는 EVENT_DELTAS(±2~12)
대비 작게(축당 1~3)로 잡는다(스펙 §2.1). 방향은 스펙 표를 그대로 따른다.

I3(예고=실행): PLAN_PREVIEW(GET /plan forecast)와 밤 정산 적용(EmoGameRun.choose
가 호출하는 apply_place_effects)이 **반드시 이 모듈의 PLACE_EFFECTS를 공유**한다
— 별도 표를 만들지 않는다.
"""

from __future__ import annotations

from . import story_texts as _story_texts
from .player_emotion.deltas import apply_delta
from .player_emotion.state import PlayerEmotionState

# 집(휴식)의 정식 표기 — day_schedule()의 "집_차트"와 구분(플랜 UI 표시용 별칭).
HOME_PLACE = "집"

# 하루 행동력 예산(신규 튜닝 상수, 스펙 §2.1 권장 시작값).
PLAN_BUDGET = 5

# 플레이어가 배정 가능한 3밴드(점심은 고정 — 게시판).
PLAN_BANDS = ("오전", "오후", "저녁")

# 장소 → (행동력 비용, 밴드당 1회 합산되는 기본 감정 효과). 스펙 §2.1 표 그대로:
# 순이득 금지 — 비용 0인 집은 가장 약하고, 강한 회복(운동)은 비용이 크다.
PLACE_EFFECTS: dict[str, dict] = {
    HOME_PLACE: {"cost": 0, "deltas": {"composure": 1, "restlessness": -1}},
    "카페":      {"cost": 1, "deltas": {"anxiety": -2, "composure": 1}},
    "도서관":    {"cost": 1, "deltas": {"fear": -2, "greed": -1}},
    "마켓":      {"cost": 1, "deltas": {"restlessness": -1, "greed": 1}},
    "광장":      {"cost": 2, "deltas": {"restlessness": 2, "anxiety": -2}},
    "일터":      {"cost": 2, "deltas": {"composure": 2, "greed": -1}},
    "운동":      {"cost": 2, "deltas": {"fear": -2, "restlessness": -2}},
    "펍":        {"cost": 2, "deltas": {"greed": 2, "anxiety": -1}},
}

# 플레이어가 편성 화면에서 고를 수 있는 장소 목록(표시 순서 고정).
PLAN_PLACES: tuple[str, ...] = tuple(PLACE_EFFECTS)

# 장소 성격 한 줄(스펙 §2.1 표 "성격" 컬럼) — 배지/설명에 재사용 가능.
PLACE_PERSONALITY: dict[str, str] = {
    HOME_PLACE: "회복. 아무 일도 안 일어남",
    "카페": "사람 만나기 좋음",
    "도서관": "익절복기 딜레마 가능성",
    "마켓": "현실소비 딜레마 가능성",
    "광장": "NPC 다수, 소문",
    "일터": "루틴",
    "운동": "강한 회복",
    "펍": "밤 분위기, NPC",
}

# 장소 플레이버 한 줄 — §2(v2 스토리보강 스펙) 이관: 단일 소스는
# story_texts.PLACE_FLAVOR. 이 이름은 하위 호환 별칭으로만 남긴다(기존
# import 유지). plan_preview()는 story_texts.place_flavor()(NPC-aware)를
# 직접 쓰고, 이 딕셔너리는 더 이상 plan 응답 생성에 쓰이지 않는다.
PLACE_FLAVOR: dict[str, str] = _story_texts.PLACE_FLAVOR

# 딜레마 가능성이 있는 장소(배지 "dilemma") — emo_game._PLACE_DILEMMAS와 정합.
_DILEMMA_PLACES = frozenset({"도서관", "마켓"})


def place_cost(place: str) -> int:
    """장소의 행동력 비용. 미지의 장소면 KeyError."""
    return PLACE_EFFECTS[place]["cost"]


def place_forecast(place: str) -> dict[str, float]:
    """장소의 기본 감정 효과(밴드당 1회분) — I3: GET /plan forecast와
    밤 정산 apply_place_effects가 이 값을 공유한다. 미지의 장소면 KeyError."""
    return dict(PLACE_EFFECTS[place]["deltas"])


def place_badges(place: str, npcs: list) -> list[str]:
    """표시용 가능성 배지 — 숫자가 아니라 배지로만 확률 요소를 알린다(스펙 I3)."""
    badges: list[str] = []
    if npcs:
        badges.append("npc")
    if place in _DILEMMA_PLACES:
        badges.append("dilemma")
    if not badges:
        badges.append("quiet")
    return badges


def validate_plan(plan: dict[str, str]) -> None:
    """플랜 검증 — 3밴드 모두 지정 + 알려진 장소 + 총비용 ≤ PLAN_BUDGET.

    위반 시 ValueError(호출자가 400으로 변환).
    """
    missing = [b for b in PLAN_BANDS if b not in plan]
    if missing:
        raise ValueError(f"missing bands in plan: {missing}")
    unknown = [p for p in plan.values() if p not in PLACE_EFFECTS]
    if unknown:
        raise ValueError(f"unknown place(s) in plan: {unknown}")
    total_cost = sum(place_cost(plan[b]) for b in PLAN_BANDS)
    if total_cost > PLAN_BUDGET:
        raise ValueError(
            f"plan cost {total_cost} exceeds budget {PLAN_BUDGET}"
        )


def apply_place_effects(
    emotion: PlayerEmotionState, plan: dict[str, str]
) -> tuple[PlayerEmotionState, list[dict]]:
    """플랜의 3개 장소 기본 효과를 감정에 순서대로(오전→오후→저녁) 합산 적용.

    (새 감정, emotion_steps 목록)을 반환한다. 각 step은
    {"source": "place", "label": "...", "place": "...", "deltas": {...}}
    (스펙 §2.2/§5.1 emotion_steps 스키마). 미지 장소면 KeyError(사전에
    validate_plan으로 걸러졌다고 가정)."""
    steps: list[dict] = []
    state = emotion
    for band in PLAN_BANDS:
        place = plan.get(band)
        if place is None:
            continue
        deltas = place_forecast(place)
        state = apply_delta(state, deltas)
        steps.append({
            "source": "place",
            "label": f"{place}에 다녀와서",
            "place": place,
            "deltas": deltas,
        })
    return state, steps
