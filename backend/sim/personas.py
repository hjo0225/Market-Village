"""§9.5 페르소나 풀 — 매매 에이전트 8종(맵 등장) + 게시판 관중 8종(맵 미등장).

T-246 — name=사람 이름(표시용), role=역할명(부기·선정 규칙 문서용).

데이터 원본: Market_Village_PRD_FINAL.md §9.5.3(매매 수치 그대로) +
PRD_SOCIAL_NPC_BOARD.md §7(관중 수치 신규 작성·자산 배정·스케줄 초안).

2켜 구조(§9.5.1): 기능 켜 = 5축 수치 + herd/rumor(게임이 읽음, 높음=취약 §9.5.2),
표현 켜 = style 한 줄(LLM/템플릿이 말투 재료로 씀). 스프라이트·초상은
environment/frontend_server/static_dirs/assets/characters/ 기존 자산 리스킨.
"""

from __future__ import annotations

# --- §9.5.3 매매 에이전트 8종 (맵 등장, 1:1 교류 대상) ------------------- #
# sched: {슬롯(1~8): 장소}. 장소는 카페/일터/광장/운동만(집_차트=클론 홈 제외).
# stim_trap: 1:1 시 클론에 자극하는 주 함정(기존 _NPC_STIM_TRAP 의미). None=도움형.
TRADER_PERSONAS: list[dict] = [
    {
        "id": "panic_ant", "name": "동수", "role": "패닉셀 개미",
        "style": "충동·공포, 군중 추종 — 떨어지면 던지고 나서 후회한다",
        "fear": 85, "greed": 15, "confidence": 25, "excitement": 72, "trust": 35,
        "herd": 0.9, "rumor": 0.8,
        "stim_trap": "F1",
        "sprite": "Eddy_Lin", "portrait": "Eddy_Lin",
        "sched": {1: "카페", 4: "광장"},
    },
    {
        "id": "fomo_scalper", "name": "재훈", "role": "FOMO 단타러",
        "style": "추세 추종, 놓침 공포 — 남이 벌면 조급해진다",
        "fear": 20, "greed": 90, "confidence": 72, "excitement": 85, "trust": 45,
        "herd": 0.85, "rumor": 0.6,
        "stim_trap": "M1",
        "sprite": "Ryan_Park", "portrait": "Ryan_Park",
        "sched": {2: "카페", 6: "광장"},
    },
    {
        "id": "conspiracy_influencer", "name": "만식", "role": "음모론 인플루언서",
        "style": "선동·드라마, 루머 — '이건 세력이 만든 판'",
        "fear": 40, "greed": 65, "confidence": 64, "excitement": 82, "trust": 12,
        "herd": 0.5, "rumor": 0.95,
        "stim_trap": "M2",
        "sprite": "Klaus_Mueller", "portrait": "Klaus_Mueller",
        # T-241 — 저녁 뒷담화 스팟은 펍(루머 전파자에게 어울리는 자리).
        "sched": {3: "광장", 7: "펍"},
    },
    {
        "id": "value_investor", "name": "정호", "role": "가치투자자",
        "style": "차분·분석·회의 — 소음과 신호를 구분하려 한다",
        "fear": 30, "greed": 40, "confidence": 72, "excitement": 24, "trust": 72,
        "herd": 0.2, "rumor": 0.2,
        "stim_trap": None,
        "sprite": "Adam_Smith", "portrait": "Adam_Smith",
        # T-50b — 도서관 배치(가치투자자=차분히 복기하는 자리). 마켓·도서관 동선 편입 대응.
        "sched": {2: "일터", 5: "카페", 8: "도서관"},
    },
    {
        "id": "quant_trader", "name": "유리", "role": "퀀트 트레이더",
        "style": "무감정·데이터 기반 — 감정은 변수, 규칙이 상수",
        "fear": 45, "greed": 55, "confidence": 75, "excitement": 20, "trust": 66,
        "herd": 0.3, "rumor": 0.3,
        "stim_trap": None,
        "sprite": "Yuriko_Yamamoto", "portrait": "Yuriko_Yamamoto",
        "sched": {1: "일터", 6: "운동"},
    },
    {
        "id": "macro_whale", "name": "태산", "role": "매크로 고래",
        "style": "역발상·대범, 공포에 산다 — '피가 흐를 때가 기회'",
        "fear": 10, "greed": 70, "confidence": 86, "excitement": 20, "trust": 70,
        "herd": 0.1, "rumor": 0.2,
        "stim_trap": None,
        "sprite": "Wolfgang_Schulz", "portrait": "Wolfgang_Schulz",
        # 운동·광장은 실주소가 같은 공원(map 브릿지) — 둘만 돌면 화면상 정지해 보여서 카페 포함.
        "sched": {4: "운동", 7: "카페"},
    },
    {
        "id": "contrarian", "name": "미나", "role": "역발상 투자자",
        "style": "군중을 거스름·독립 — 다들 사면 판다",
        "fear": 25, "greed": 60, "confidence": 70, "excitement": 46, "trust": 30,
        "herd": 0.05, "rumor": 0.3,
        "stim_trap": None,
        "sprite": "Carmen_Ortiz", "portrait": "Carmen_Ortiz",
        # 위와 같은 이유(운동=광장=공원)로 일터 포함. T-50b — 마켓 배치(역발상=현실 소비 자리).
        "sched": {2: "일터", 5: "광장", 8: "마켓"},
    },
    {
        "id": "jackpot_gambler", "name": "도철", "role": "한탕 도박꾼",
        "style": "수익 인증하며 '더 가즈아' — 과신과 욕심으로 꼬드긴다",
        "fear": 15, "greed": 92, "confidence": 85, "excitement": 55, "trust": 30,
        "herd": 0.4, "rumor": 0.5,
        "stim_trap": "G2",
        "sprite": "Carlos_Gomez", "portrait": "Carlos_Gomez",
        # T-241 — 도박꾼의 "더 가즈아"는 펍에서(슬롯6 — 클론 기본 일과와 겹쳐 만남 발생).
        "sched": {4: "카페", 6: "펍"},
    },
]

# --- §9.5.4 게시판 전용 관중 8종 (맵 미등장·매매 안 함·가격 무영향) ------- #
# mood: 게시판 피드에서 이 관중이 미는 분위기(트리거별 선정 규칙이 소비).
SNS_PERSONAS: list[dict] = [
    {
        "id": "bull_hoper", "name": "해나", "role": "불장기원 개미",
        "style": "초록 캔들마다 환호하는 retail", "mood": "낙관·FOMO 증폭",
        "fear": 20, "greed": 80, "confidence": 60, "excitement": 90, "trust": 50,
        "herd": 0.9, "rumor": 0.6,
        "portrait": "Hailey_Johnson",
    },
    {
        "id": "troll", "name": "광수", "role": "주식방 악플러",
        "style": "틀린 콜을 조롱하는 트롤", "mood": "선동·공격",
        "fear": 30, "greed": 50, "confidence": 75, "excitement": 70, "trust": 20,
        "herd": 0.3, "rumor": 0.7,
        "portrait": "Tom_Moreno",
    },
    {
        "id": "newbie", "name": "소은", "role": "코린이 뉴비",
        "style": "불안한 초보, 순진한 질문", "mood": "불안 확산",
        "fear": 75, "greed": 60, "confidence": 20, "excitement": 65, "trust": 60,
        "herd": 0.95, "rumor": 0.8,
        "portrait": "Maria_Lopez",
    },
    {
        "id": "anon_veteran", "name": "성찬", "role": "익명 고수",
        "style": "거들먹거리는 베테랑, 한 줄 평", "mood": "압박·자기회의 유발",
        "fear": 25, "greed": 45, "confidence": 90, "excitement": 30, "trust": 40,
        "herd": 0.1, "rumor": 0.3,
        "portrait": "Giorgio_Rossi",
    },
    {
        "id": "cheerleader", "name": "라온", "role": "치어리더",
        "style": "무조건 응원하는 낙관론자", "mood": "낙관 증폭",
        "fear": 15, "greed": 70, "confidence": 70, "excitement": 85, "trust": 70,
        "herd": 0.8, "rumor": 0.5,
        "portrait": "Latoya_Williams",
    },
    {
        "id": "doomposter", "name": "무경", "role": "공포팔이",
        "style": "어디서나 폭락을 보는 둠포스터", "mood": "공포 전파",
        "fear": 90, "greed": 20, "confidence": 70, "excitement": 60, "trust": 15,
        "herd": 0.4, "rumor": 0.9,
        "portrait": "Arthur_Burton",
    },
    {
        "id": "chart_zealot", "name": "태식", "role": "지표충",
        "style": "RSI/MACD 들이대는 기술파", "mood": "사이비 분석 자극",
        "fear": 40, "greed": 55, "confidence": 80, "excitement": 45, "trust": 35,
        "herd": 0.2, "rumor": 0.6,
        "portrait": "Rajiv_Patel",
    },
    {
        "id": "contrarian_fan", "name": "아리", "role": "청개구리",
        "style": "무리를 거스르는 청개구리", "mood": "역발상 자극",
        "fear": 30, "greed": 55, "confidence": 65, "excitement": 50, "trust": 25,
        "herd": 0.05, "rumor": 0.4,
        "portrait": "Ayesha_Khan",
    },
]


# --- T-273 마을 분위기 프리셋 (🤖 council 2026-07-05) --------------------- #
# 인원 구성은 불변(8종 전원 — 6함정 커버리지 코어 보존), favored 그룹에 고정
# 슬롯 +1씩만 부여해 노출 빈도를 기울인다. 순수 파생·RNG 없음(결정론), 기존
# 슬롯과 비충돌, 장소는 기존 사용 장소(카페/일터/광장/운동/펍) 안에서만.
VILLAGE_PRESETS: dict[str, dict[str, dict[int, str]]] = {
    "balanced": {},
    "aggressive": {   # 함정 자극 4종이 마을에 더 자주 나온다
        "panic_ant": {7: "펍"}, "fomo_scalper": {4: "카페"},
        "conspiracy_influencer": {5: "광장"}, "jackpot_gambler": {8: "펍"},
    },
    "conservative": {  # 도움형 4종이 더 자주 나온다
        "value_investor": {7: "일터"}, "quant_trader": {3: "일터"},
        "macro_whale": {1: "운동"}, "contrarian": {6: "운동"},
    },
}


# --- game_run 계약용 헬퍼 (_NPC_SCHEDS / _NPC_STIM_TRAP 대체) ------------- #
def npc_scheds(village: str = "balanced") -> dict[str, dict[int, str]]:
    """{npc_id: {슬롯: 장소}} — 회차 불변 고정 일과(§9.2.1).

    T-273 — village 프리셋이 favored NPC에 슬롯 +1. 기본값은 기존과 동일.
    """
    extra = VILLAGE_PRESETS.get(village) or {}
    out: dict[str, dict[int, str]] = {}
    for p in TRADER_PERSONAS:
        sched = dict(p["sched"])
        sched.update(extra.get(p["id"], {}))
        out[p["id"]] = sched
    return out


def npc_stim_traps() -> dict[str, str | None]:
    """{npc_id: 자극 함정 or None} — §9.2.1b 끌림 판정·persuade가 소비."""
    return {p["id"]: p["stim_trap"] for p in TRADER_PERSONAS}


def trader_by_id(npc_id: str) -> dict | None:
    for p in TRADER_PERSONAS:
        if p["id"] == npc_id:
            return p
    return None
