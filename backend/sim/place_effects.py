"""§2 일과 편성(플랜) — 장소별 행동력 비용 + 기본 감정 효과 (신규 모듈).

`emo_game._ROUTE_CYCLE`의 실제 장소 이름을 그대로 재사용한다(카페/광장/펍/
일터/운동/마켓/도서관) + 집(휴식, 비용 0). 값의 크기는 EVENT_DELTAS(±2~12)
대비 작게(축당 1~3)로 잡는다(스펙 §2.1). 방향은 스펙 표를 그대로 따른다.

I3(예고=실행): PLAN_PREVIEW(GET /plan forecast)와 밤 정산 적용(EmoGameRun.choose
가 호출하는 apply_place_effects)이 **반드시 이 모듈의 ACTIVITIES를 공유**한다
— 별도 표를 만들지 않는다.

v4 §1.2 — 활동(activity) 시스템: 지금까지는 장소당 효과 1종이 오전/오후/저녁에
동일했다. 이제 (밴드, 장소)마다 2~3개의 활동 변형을 두고, 날마다 결정론으로
1개가 선택된다(activity_for). PLACE_EFFECTS/place_cost/place_forecast는 활동
시스템 이전의 정적 표로, 하위 호환 및 활동표 스키마 린트의 "성격/방향" 참고용
으로 남긴다 — plan/정산 경로는 이제 활동표를 직접 쓴다.
"""

from __future__ import annotations

import random
import zlib

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
# v4 §1.2 이후: 이 표는 활동표(ACTIVITIES) 도입 이전의 정적 기준값 — 하위 호환
# 별칭(place_cost/place_forecast)과 활동 스키마 린트의 "장소 성격 방향" 참고용
# 으로만 남는다. plan_preview()/apply_place_effects()는 활동표를 직접 쓴다.
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
    """장소의 행동력 비용(활동 시스템 이전 하위 호환 기준값). 미지의 장소면 KeyError."""
    return PLACE_EFFECTS[place]["cost"]


def place_forecast(place: str) -> dict[str, float]:
    """장소의 기본 감정 효과(활동 시스템 이전 하위 호환 기준값). 미지의 장소면 KeyError."""
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


# --------------------------------------------------------------------------- #
# v4 §1.2 — 활동(activity) 시스템
# --------------------------------------------------------------------------- #
# ACTIVITIES[(band, place)] = [ {id, name, cost, deltas, note}, ... ]  (2~3개)
#
# 범위: cost 0~3(예산 5 유지 → cost 3짜리 둘은 이미 불가), 축당 델타 1~6
# (약 1-2 / 중 3-4 / 강 5-6). 순이득 금지 — 축이 전부 "이로운 방향"
# (fear/greed/anxiety/restlessness 감소 or composure 증가)인 활동은 cost>=2.
# 밴드 성격: 오전=차분/준비(약~중), 오후=활동/사람(중), 저녁=회복or유혹(약~강,
# 부작용 동반 많게). 대사 톤은 story_texts.PLACE_FLAVOR/PLACE_NPC_FLAVOR와
# 맞춘다 — 가격 예측 발언 금지, 잔잔한 일상물.
ACTIVITIES: dict[tuple[str, str], list[dict]] = {
    # --- 집 (cost 0, 항상 약함) — 순이득 금지: 비용 0 활동은 부작용 축을 하나
    # 동반시켜(약한 트레이드오프) "전부 이로운 방향" 조합을 만들지 않는다. ---- #
    ("오전", "집"): [
        {"id": "home_am_stretch", "name": "이불 속 뒹굴", "cost": 0,
         "deltas": {"restlessness": -1, "greed": 1}},
        {"id": "home_am_tea", "name": "물 한 잔 챙기기", "cost": 0,
         "deltas": {"composure": 1, "restlessness": 1}},
    ],
    ("오후", "집"): [
        {"id": "home_pm_laundry", "name": "밀린 빨래", "cost": 0,
         "deltas": {"restlessness": -1, "anxiety": 1}},
        {"id": "home_pm_nap", "name": "짧은 낮잠", "cost": 0,
         "deltas": {"anxiety": -1, "restlessness": 1}},
    ],
    ("저녁", "집"): [
        {"id": "home_pm_lightsoff", "name": "일찍 불 끄기", "cost": 0,
         "deltas": {"composure": 1, "greed": 1}},
        {"id": "home_pm_diary", "name": "하루 마무리 메모", "cost": 0,
         "deltas": {"anxiety": -1, "restlessness": 1}},
    ],

    # --- 카페 --------------------------------------------------------------- #
    ("오전", "카페"): [
        {"id": "cafe_am_brew", "name": "모닝 브루", "cost": 1,
         "deltas": {"anxiety": -2, "restlessness": 1}},
        {"id": "cafe_am_news", "name": "신문 훑어보기", "cost": 2,
         "deltas": {"fear": -3, "restlessness": 1}},
        {"id": "cafe_am_window", "name": "창가 자리 차지", "cost": 1,
         "deltas": {"anxiety": -1, "greed": 1}},
    ],
    ("오후", "카페"): [
        {"id": "cafe_pm_chat", "name": "동수와 수다", "cost": 1,
         "deltas": {"anxiety": -2, "restlessness": 1}},
        {"id": "cafe_pm_refill", "name": "리필 한 잔 더", "cost": 2,
         "deltas": {"composure": 2, "greed": 1}},
    ],
    ("저녁", "카페"): [
        {"id": "cafe_pm_decaf", "name": "디카페인 한 잔", "cost": 1,
         "deltas": {"anxiety": -2, "restlessness": 1}},
        {"id": "cafe_pm_closing", "name": "마감 직전 눌러앉기", "cost": 2,
         "deltas": {"composure": 3, "restlessness": 1}},
    ],

    # --- 도서관 (익절복기 딜레마 가능) -------------------------------------- #
    ("오전", "도서관"): [
        {"id": "lib_am_review", "name": "차트 복기 노트", "cost": 1,
         "deltas": {"fear": -2, "restlessness": 1}},
        {"id": "lib_am_plan", "name": "이번 주 계획 짜기", "cost": 2,
         "deltas": {"fear": -3, "restlessness": -1}},
    ],
    ("오후", "도서관"): [
        {"id": "lib_pm_book", "name": "책장 넘기기", "cost": 1,
         "deltas": {"fear": -1, "restlessness": 1}},
        {"id": "lib_pm_deepread", "name": "긴 책 정독", "cost": 2,
         "deltas": {"fear": -3, "greed": -2}},
        {"id": "lib_pm_quiet", "name": "조용한 열람실", "cost": 1,
         "deltas": {"anxiety": -1, "greed": 1}},
    ],
    ("저녁", "도서관"): [
        {"id": "lib_pm_lastpage", "name": "마지막 장까지", "cost": 2,
         "deltas": {"fear": -3, "greed": -2, "restlessness": 1}},
        {"id": "lib_pm_reshelf", "name": "책 정리하고 나오기", "cost": 1,
         "deltas": {"composure": 1, "restlessness": 1}},
    ],

    # --- 마켓 (현실소비 딜레마 가능) ---------------------------------------- #
    ("오전", "마켓"): [
        {"id": "mkt_am_errand", "name": "아침 장보기", "cost": 1,
         "deltas": {"restlessness": -1, "greed": 1}},
        {"id": "mkt_am_flowers", "name": "꽃집 앞 구경", "cost": 1,
         "deltas": {"anxiety": -1, "greed": 1}},
    ],
    ("오후", "마켓"): [
        {"id": "mkt_pm_haggle", "name": "저녁거리 흥정", "cost": 1,
         "deltas": {"restlessness": -1, "greed": 1}},
        {"id": "mkt_pm_splurge", "name": "충동구매 한 건", "cost": 2,
         "deltas": {"greed": 3, "restlessness": -2}},
    ],
    ("저녁", "마켓"): [
        {"id": "mkt_pm_closeout", "name": "마감 세일 훑기", "cost": 2,
         "deltas": {"greed": 3, "restlessness": -1, "anxiety": 1}},
        {"id": "mkt_pm_walk", "name": "장바구니 없이 산책", "cost": 1,
         "deltas": {"restlessness": -1, "greed": 1}},
    ],

    # --- 광장 (NPC 다수, 소문) ----------------------------------------------- #
    ("오전", "광장"): [
        {"id": "sq_am_bench", "name": "벤치에서 볕쬐기", "cost": 1,
         "deltas": {"anxiety": -1, "restlessness": 1}},
        {"id": "sq_am_pigeons", "name": "비둘기 구경", "cost": 1,
         "deltas": {"anxiety": -1, "restlessness": 1}},
    ],
    ("오후", "광장"): [
        {"id": "sq_pm_gossip", "name": "소문 주워듣기", "cost": 2,
         "deltas": {"restlessness": 2, "anxiety": -2}},
        {"id": "sq_pm_crowd", "name": "장터 인파 구경", "cost": 2,
         "deltas": {"restlessness": 3, "anxiety": -1, "greed": 1}},
        {"id": "sq_pm_stroll", "name": "느긋한 광장 산책", "cost": 1,
         "deltas": {"restlessness": 1, "anxiety": -1}},
    ],
    ("저녁", "광장"): [
        {"id": "sq_pm_streetlamp", "name": "가로등 아래 서성이기", "cost": 2,
         "deltas": {"restlessness": 2, "anxiety": -2, "fear": 1}},
        {"id": "sq_pm_lastbus", "name": "막차 정류장 잡담", "cost": 1,
         "deltas": {"anxiety": -1, "restlessness": 1}},
    ],

    # --- 일터 (루틴) ---------------------------------------------------------- #
    ("오전", "일터"): [
        {"id": "work_am_checklist", "name": "출근 전 체크리스트", "cost": 1,
         "deltas": {"composure": 2, "restlessness": 1}},
        {"id": "work_am_early", "name": "일찍 나와 자리 정리", "cost": 2,
         "deltas": {"composure": 3, "restlessness": -1}},
    ],
    ("오후", "일터"): [
        {"id": "work_pm_routine", "name": "루틴대로 처리", "cost": 2,
         "deltas": {"composure": 2, "greed": -1}},
        {"id": "work_pm_overtime", "name": "잔업 조금 더", "cost": 3,
         "deltas": {"composure": 4, "greed": -2, "restlessness": -1}},
    ],
    ("저녁", "일터"): [
        {"id": "work_pm_deskclean", "name": "책상 정리하고 퇴근", "cost": 1,
         "deltas": {"composure": 2, "restlessness": 1}},
        {"id": "work_pm_lastcheck", "name": "내일 할 일 메모", "cost": 2,
         "deltas": {"composure": 3, "greed": -1}},
    ],

    # --- 운동 (강한 회복) -------------------------------------------------- #
    ("오전", "운동"): [
        {"id": "gym_am_jog", "name": "가벼운 조깅", "cost": 1,
         "deltas": {"fear": -1, "greed": 1}},
        {"id": "gym_am_stretch", "name": "아침 스트레칭", "cost": 1,
         "deltas": {"restlessness": -1, "greed": 1}},
    ],
    ("오후", "운동"): [
        {"id": "gym_pm_run", "name": "땀나게 달리기", "cost": 2,
         "deltas": {"fear": -2, "restlessness": -2}},
        {"id": "gym_pm_spar", "name": "스파링 한 판", "cost": 3,
         "deltas": {"fear": -5, "restlessness": -4, "anxiety": -1}},
    ],
    ("저녁", "운동"): [
        {"id": "gym_pm_lap", "name": "야간 러닝", "cost": 2,
         "deltas": {"fear": -2, "restlessness": -2}},
        {"id": "gym_pm_maxout", "name": "한계까지 밀어붙이기", "cost": 3,
         "deltas": {"fear": -5, "restlessness": -3, "anxiety": 1}},
    ],

    # --- 펍 (밤 분위기, NPC) ------------------------------------------------ #
    ("오전", "펍"): [
        {"id": "pub_am_clean", "name": "오픈 전 청소 거들기", "cost": 1,
         "deltas": {"composure": 1, "restlessness": 1}},
        {"id": "pub_am_delivery", "name": "재료 들여오는 것 구경", "cost": 1,
         "deltas": {"restlessness": -1, "greed": 1}},
    ],
    ("오후", "펍"): [
        {"id": "pub_pm_earlyseat", "name": "이른 자리 잡기", "cost": 1,
         "deltas": {"anxiety": -1, "greed": 1}},
        {"id": "pub_pm_snack", "name": "안주 한 접시", "cost": 2,
         "deltas": {"greed": 2, "anxiety": -2}},
    ],
    ("저녁", "펍"): [
        {"id": "pub_pm_talk", "name": "왁자지껄 한 잔", "cost": 3,
         "deltas": {"anxiety": -5, "greed": 2}},
        {"id": "pub_pm_corner", "name": "구석에서 듣기만", "cost": 1,
         "deltas": {"anxiety": -2, "fear": 1}},
        {"id": "pub_pm_lastcall", "name": "라스트 콜까지", "cost": 2,
         "deltas": {"anxiety": -3, "greed": 2, "restlessness": 1}},
    ],
}


def activity_variants(band: str, place: str) -> list[dict]:
    """(밴드, 장소)의 활동 변형 목록. 미지 조합이면 KeyError."""
    return ACTIVITIES[(band, place)]


def activity_for(seed: int, day: int, band: str, place: str) -> dict:
    """오늘의 활동 결정론 선택 — I3/I2: GET /plan forecast와 밤 정산 적용이
    **반드시 이 함수**를 공유해 같은 (seed, day, band, place)면 같은 활동을
    얻는다. `zlib.crc32(f"act:{seed}:{day}:{band}:{place}")`를 시드로 한
    `random.Random`에서 `rng.choice(variants)`(스펙 §1.2)."""
    variants = activity_variants(band, place)
    rng = random.Random(zlib.crc32(f"act:{seed}:{day}:{band}:{place}".encode()))
    return rng.choice(variants)


def activity_cost(seed: int, day: int, band: str, place: str) -> int:
    """오늘의 활동 비용(활동 시스템 기준값) — I3 소스."""
    return int(activity_for(seed, day, band, place)["cost"])


def activity_forecast(seed: int, day: int, band: str, place: str) -> dict[str, float]:
    """오늘의 활동 예상 감정 델타(활동 시스템 기준값) — I3 소스."""
    return dict(activity_for(seed, day, band, place)["deltas"])


def validate_plan(plan: dict[str, str], *, seed: int | None = None, day: int = 0) -> None:
    """플랜 검증 — 3밴드 모두 지정 + 알려진 장소 + 총비용 ≤ PLAN_BUDGET.

    `seed`가 주어지면(v4 §1.2 활동 시스템) 그날의 활동 비용(activity_cost)으로
    검증한다 — GET /plan에 보여준 비용과 동일 소스(I3). `seed`가 None이면
    (레거시 호출부·하위 호환) PLACE_EFFECTS 기준값으로 검증한다.

    위반 시 ValueError(호출자가 400으로 변환).
    """
    missing = [b for b in PLAN_BANDS if b not in plan]
    if missing:
        raise ValueError(f"missing bands in plan: {missing}")
    unknown = [p for p in plan.values() if p not in PLACE_EFFECTS]
    if unknown:
        raise ValueError(f"unknown place(s) in plan: {unknown}")
    if seed is None:
        total_cost = sum(place_cost(plan[b]) for b in PLAN_BANDS)
    else:
        total_cost = sum(
            activity_cost(seed, day, b, plan[b]) for b in PLAN_BANDS
        )
    if total_cost > PLAN_BUDGET:
        raise ValueError(
            f"plan cost {total_cost} exceeds budget {PLAN_BUDGET}"
        )


def apply_place_effects(
    emotion: PlayerEmotionState, plan: dict[str, str],
    *, seed: int | None = None, day: int = 0,
) -> tuple[PlayerEmotionState, list[dict]]:
    """플랜의 3개 장소 활동 효과를 감정에 순서대로(오전→오후→저녁) 합산 적용.

    (새 감정, emotion_steps 목록)을 반환한다. 각 step은
    {"source": "place", "label": "...", "place": "...", "deltas": {...}}
    (스펙 §2.2/§5.1 emotion_steps 스키마). `seed`가 주어지면(v4 §1.2) 그날의
    활동(activity_for)을 적용하고 라벨을 활동명 기반("「{활동명}」 후")으로
    남긴다 — 미지 장소면 KeyError(사전에 validate_plan으로 걸러졌다고 가정)."""
    steps: list[dict] = []
    state = emotion
    for band in PLAN_BANDS:
        place = plan.get(band)
        if place is None:
            continue
        if seed is None:
            deltas = place_forecast(place)
            label = f"{place}에 다녀와서"
            extra = {"place": place}
        else:
            activity = activity_for(seed, day, band, place)
            deltas = dict(activity["deltas"])
            label = f"「{activity['name']}」 후"
            extra = {"place": place, "activity_id": activity["id"],
                      "activity_name": activity["name"]}
        state = apply_delta(state, deltas)
        steps.append({
            "source": "place",
            "label": label,
            "deltas": deltas,
            **extra,
        })
    return state, steps
