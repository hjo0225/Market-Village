"""§1/§2 스토리 보강 — 정적 텍스트 전용(I5: LLM 금지) 신규 모듈.

- `DAY_FRAMES`: 편성 화면 상단 아침 내레이션(20개, day % len로 순환 조회).
- `PLACE_FLAVOR`: 장소 기본 플레이버 한 줄. **단일 소스**(place_effects.py의
  구판은 이 딕셔너리를 재노출하는 별칭으로 남아 하위 호환만 유지한다).
- `PLACE_NPC_FLAVOR`: (장소, npc_id) 조우 플레이버 한 줄 — plan_preview()가
  그 밴드에 NPC가 있으면 npc_id 정렬 첫 번째로 이 표를 우선 조회하고, 없으면
  PLACE_FLAVOR로 폴백한다(스펙 §2 NPC-aware 규칙).

장소 키는 `place_effects.PLACE_EFFECTS`의 실제 상수와 정확히 일치시킨다:
집(HOME_PLACE)·카페·도서관·마켓·광장·일터·운동·펍.
"""

from __future__ import annotations

# §1 — 아침 내레이션(데이 프레임). day 인덱스로 조회, day >= len이면 day % len.
DAY_FRAMES: list[str] = [
    "이삿날. 상자보다 지갑이 먼저 풀렸다.",                      # D0
    "첫 아침. 커피포트가 아직 낯설다.",                          # D1
    "분리수거 날. 광장에서 다들 한 마디씩 얹는다.",               # D2
    "마을 장날. 마켓이 평소보다 소란하다.",                      # D3
    "안개 낀 아침. 차트도 마을도 뿌옇다.",                       # D4
    "닷새째. 단톡방 알림음을 구분할 수 있게 됐다.",               # D5
    "비 예보. 우산을 챙기는 사람과 안 챙기는 사람.",              # D6
    "일주일. 카페 사장이 이름을 기억해줬다.",                    # D7
    "바람 부는 날. 빨래가 잘 마른다고 정호가 말했다.",            # D8
    "반환점. 절반의 날들이 지났다.",                             # D9
    "늦잠의 유혹. 그래도 마을은 여덟 시에 깬다.",                 # D10
    "도서관 반납일. 미뤄둔 것들이 있다.",                        # D11
    "펍에 새 메뉴가 붙었다. 도철이 벌써 먹어봤단다.",             # D12
    "구름 많음. 광장 비둘기도 조용한 날.",                       # D13
    "2주. 이 마을의 소음에 익숙해졌다.",                         # D14
    "환기의 날. 창문을 열면 차트 생각이 덜 난다.",                # D15
    "꽃집 앞에 새 화분. 미나가 이름을 붙였다.",                   # D16
    "사흘 남았다. 달력을 보는 시간이 길어진다.",                  # D17
    "전야. 마을이 평소보다 다정하다.",                           # D18
    "마지막 날. 첫날과 같은 하늘.",                              # D19
]


def day_frame(day: int) -> str:
    """day 인덱스의 아침 내레이션. day가 20을 넘으면 순환(day % len)."""
    if not DAY_FRAMES:
        return ""
    return DAY_FRAMES[day % len(DAY_FRAMES)]


# §2 — 장소 기본 플레이버 한 줄. 키는 place_effects.PLACE_EFFECTS(=PLAN_PLACES)의
# 실제 장소 상수와 일치("집"=HOME_PLACE, 나머지는 표시명 그대로).
PLACE_FLAVOR: dict[str, str] = {
    "집":    "이불 속은 시장 밖. 오늘의 가장 싼 피난처.",
    "카페":  "김이 오르는 첫 잔. 창가 자리는 늘 경쟁이다.",
    "도서관": "책장 넘기는 소리뿐. 계획은 조용한 데서 자란다.",
    "마켓":  "저녁거리 흥정 소리. 숫자가 아니라 물건의 세계.",
    "광장":  "비둘기와 소문이 함께 내려앉는 곳.",
    "일터":  "몸을 움직이면 잡생각이 줄어든다.",
    "운동":  "숨이 차면, 차트 생각이 끊긴다.",
    "펍":    "간판 불이 켜지면 다들 조금씩 솔직해진다.",
}

# §2 — (장소, npc_id) 조우 플레이버 한 줄. npc_id는 personas.py TRADER_PERSONAS의
# 실제 id(panic_ant/fomo_scalper/conspiracy_influencer/value_investor/
# quant_trader/macro_whale/contrarian/jackpot_gambler)와 일치.
PLACE_NPC_FLAVOR: dict[tuple[str, str], str] = {
    ("카페", "panic_ant"):             "오늘의 첫 손님은 늘 동수다. 컵을 쥔 손이 조금 떨린다.",
    ("광장", "panic_ant"):             "동수가 광장 벤치에서 휴대폰을 껐다 켰다 한다.",
    ("카페", "fomo_scalper"):          "재훈이 헬멧을 벗지도 않고 아이스아메리카노를 시킨다.",
    ("광장", "fomo_scalper"):          "배달 오토바이가 광장을 가로지른다. 재훈이다.",
    ("광장", "conspiracy_influencer"): "만식이 광장 게시판 앞에서 누군가를 붙잡고 있다.",
    ("펍",   "conspiracy_influencer"): "구석 지정석. 만식의 '진짜 이야기'가 시작된다.",
    ("일터", "value_investor"):        "도시락과 작은 화분. 정호의 자리는 멀리서도 표가 난다.",
    ("카페", "value_investor"):        "정호는 커피를 반만 마시고 반은 남긴다. 늘 그렇다.",
    ("도서관", "value_investor"):      "정호가 두꺼운 책에 포스트잇을 붙이고 있다.",
    ("일터", "quant_trader"):          "유리의 모니터엔 숫자만 있다. 잡담은 초 단위로 끝난다.",
    ("운동", "quant_trader"):          "초시계 소리. 유리는 오늘도 기록 갱신 중이다.",
    ("운동", "macro_whale"):           "태산은 새벽 등산을 마치고 왔다는데 지치질 않는다.",
    ("카페", "macro_whale"):           "태산이 신문을 종이로 읽는다. 이 마을에서 유일하게.",
    ("일터", "contrarian"):            "미나가 콧노래를 부르며 상자를 나른다. 남들과 반대 방향으로.",
    ("광장", "contrarian"):            "미나는 다들 모인 곳 반대편 벤치에 앉는다.",
    ("마켓", "contrarian"):            "꽃집 앞, 미나가 물뿌리개를 든다. 맑은 날에도 우산을 챙기는 사람.",
    ("카페", "jackpot_gambler"):       "도철의 목소리는 주문보다 먼저 도착한다.",
    ("펍",   "jackpot_gambler"):       "도철의 웃음소리가 문밖까지 들린다. 오늘은 무슨 얘길까.",
}


def place_flavor(place: str, npc_ids: list[str] | None = None) -> str:
    """장소 플레이버 한 줄 — NPC-aware 규칙(스펙 §2):
    그 밴드에 NPC가 있으면 PLACE_NPC_FLAVOR[(place, npc_id)] 우선(여럿이면
    npc_id 정렬 첫 번째), 없으면 PLACE_FLAVOR[place]로 폴백."""
    if npc_ids:
        first = sorted(npc_ids)[0]
        hit = PLACE_NPC_FLAVOR.get((place, first))
        if hit is not None:
            return hit
    return PLACE_FLAVOR.get(place, "")
