"""T-13: 엔딩 5종 (문서 §4 「마켓 빌리지의 10일」).

감정(2단계)×재산(2단계) 4분기 + 특수이벤트 누적 N회 이상 히든(E5).
verdict(과열/위축/중립, T-4)를 감정축 2단계로 접는다: 중립=감정+, 그 외=감정−.
2×2 등급(고수/벼락부자형/강철멘탈형/호구)은 회차 비교용으로 병기 유지.

에필로그는 문서 §4.3 전문(3컷: ①마지막 아침 ②마을 한 장면 ③남는 문장).
기존 result_card.py(라이브 구게임)는 건드리지 않는 신규 레이어.
"""

from __future__ import annotations

# 🙋 튜닝 잠정치(플레이테스트로 확정 — 문서 §8) — E5 히든 엔딩 기준 횟수.
SPECIAL_EVENT_ENDING_N = 6

# 3일 압축 모드(emo_api.COMPACT_DAYS_MAX) 전용 E5 기준. 특수이벤트는 하루 최대
# 1건이라 3일 최대 누적은 3 — 체인 확률 상향(chain.SPECIAL_EVENT_PROB_COMPACT=0.95)
# 상태에서 기준을 3 이하로 두면 거의 모든 압축 회차가 E5로 수렴해, 플레이에 따라
# 갈리는 2×2 엔딩(수익률×감정통제 — 제품 테제)이 가려진다. 도달 불가한 4로 두어
# 히든 엔딩은 10일 정식판의 보상으로 남긴다.
SPECIAL_EVENT_ENDING_N_COMPACT = 4

_GRADE = {
    (True, True): "고수",
    (False, True): "벼락부자형",
    (True, False): "강철멘탈형",
    (False, False): "호구",
}

# id → (title, grade, 3컷 에필로그). 문서 §4.3 전문.
_ENDINGS: dict[str, dict] = {
    "E1": {
        "title": "맑음, 가끔 산들바람",
        "epilogue": [
            "열흘째 아침, 클론은 알람보다 먼저 깼다. 차트는 켜지 않고 창문부터 열었다.",
            "카페에서 동수가 손을 들었다. \"너는 안 흔들리더라.\" 클론은 웃었다. \"흔들렸는데, 안 넘어졌을 뿐이야.\"",
            "통장 숫자보다 오래 남은 건, 그 열흘의 잠자리가 편했다는 사실이었다.",
        ],
    },
    "E2": {
        "title": "불꽃놀이 뒤의 빈 광장",
        "epilogue": [
            "클론은 이겼다. 숫자는 분명히 그렇게 말했다.",
            "축하하러 간 펍에서 도철이 어깨동무를 했다. \"거봐, 한 방이라니까!\" 클론은 같이 웃었지만, 웃음이 얼굴에서 자꾸 미끄러졌다.",
            "불꽃놀이는 끝났고, 광장은 비었다. 다음에도 이길 수 있다고, 아무도 장담해주지 않았다.",
        ],
    },
    "E3": {
        "title": "비 온 뒤의 저녁 산책",
        "epilogue": [
            "열흘 내내 비가 왔다. 클론의 우산은 자주 뒤집혔지만, 한 번도 내던져지지 않았다.",
            "미나가 꽃집 앞에서 젖은 화분을 내놓았다. \"비 맞은 애들이 뿌리는 더 깊어요.\" 클론은 그 말을 두 번 곱씹었다.",
            "잃은 숫자는 장부에 남고, 지킨 원칙은 사람에 남는다. 클론은 저녁 산책을 오래 했다.",
        ],
    },
    "E4": {
        "title": "긴 겨울, 그리고 첫눈",
        "epilogue": [
            "마지막 아침, 클론은 이불 속에서 폰을 쥔 채 한참을 있었다.",
            "광장을 지나는데 태산이 국밥집 문을 열어줬다. \"밥은 먹고 다니냐.\" 클론은 처음으로, 시장 얘기 말고 다른 얘기를 했다.",
            "열흘은 겨울이었다. 그래도 겨울에만 보이는 것이 있었다 — 다음 회차의 클론은, 오늘의 클론이 어디서 미끄러졌는지 안다.",
        ],
    },
    "E5": {
        "title": "마을의 일원",
        "epilogue": [
            "마지막 아침, 클론의 폰이 평소보다 시끄러웠다. 동수의 \"커피 사놨다\", 유리의 \"오늘 러닝 쉼\", 만식의 \"…비밀인데 너한테만\".",
            "펍에 여덟 명이 다 모였다. 수익 얘기는 아무도 먼저 꺼내지 않았다. 도철이 첫 잔을 샀고, 정호가 마지막 잔을 샀다.",
            "계좌는 열흘의 성적표지만, 마을은 열흘의 증거였다. 클론은 이 마을에서, 시장보다 오래가는 걸 하나 만들었다.",
        ],
    },
}


# T-37 — 평정(composure)이 이 이상이면 성향이 기울어도 '자기통제됨'으로 본다.
COMPOSURE_GOOD = 60.0


def emotion_controlled(verdict: str, composure: float = 50.0) -> bool:
    """감정 통제: 판정이 중립(균형)이거나, **평정(자기통제)이 높으면** 통제됨(감정+).
    평정은 원칙 있는 선택으로 쌓은 자기통제라, 성향이 과열/위축으로 기울어도
    스스로 다스렸다고 본다 — '돈은 못 벌어도 자신을 이긴' 좋은 엔딩의 근거."""
    return verdict == "중립" or composure >= COMPOSURE_GOOD


def grade_2x2(verdict: str, wealth_level: str, composure: float = 50.0) -> str:
    """회차 비교용 2×2 등급(엔딩 종류와 무관하게 병기)."""
    return _GRADE[(emotion_controlled(verdict, composure), wealth_level == "high")]


def days_word(n: int) -> str:
    """일수를 한국어 자연수사로. 3일 압축 모드·10일 기본 게임 전용 표기(그 외는
    "{n}일" 폴백) — 에필로그·블라인드 리빌 헤드라인 등 서사 문구가 실제 회차
    길이에 맞게 말하도록(하드코딩 "열흘" 치환의 단일 소스)."""
    return {3: "사흘", 10: "열흘"}.get(n, f"{n}일")


def decide_ending(verdict: str, wealth_level: str, special_count: int,
                  composure: float = 50.0, total_days: int | None = None) -> dict:
    """엔딩 결정(문서 §4.2). 특수이벤트 N회 이상이면 히든 E5, 아니면 4분기.
    평정이 높으면 감정 통제(good)로 쳐 E1/E3(좋은 엔딩) 쪽으로 간다(T-37).

    `total_days` — 3일 압축 모드(emo_api.COMPACT_DAYS_MAX) 여부 판정용(하위 호환:
    생략/None이면 기존 10일 기준·문구 그대로). 3일이면 E5 기준을 낮추고
    (SPECIAL_EVENT_ENDING_N_COMPACT), 에필로그의 "열흘"을 "사흘"로 치환한다."""
    compact = total_days is not None and total_days <= 3
    threshold = SPECIAL_EVENT_ENDING_N_COMPACT if compact else SPECIAL_EVENT_ENDING_N

    good = emotion_controlled(verdict, composure)
    hi = wealth_level == "high"
    if special_count >= threshold:
        ending_id = "E5"
    elif good and hi:
        ending_id = "E1"
    elif not good and hi:
        ending_id = "E2"
    elif good and not hi:
        ending_id = "E3"
    else:
        ending_id = "E4"

    data = _ENDINGS[ending_id]
    epilogue = list(data["epilogue"])
    if total_days == 3:
        # substring 치환이라 "열흘째"→"사흘째"도 함께 해결된다. 원본 리스트는
        # 불변(_ENDINGS는 모듈 전역 캐시라 변이하면 다른 회차가 오염된다).
        epilogue = [line.replace("열흘", days_word(3)) for line in epilogue]
    return {
        "id": ending_id,
        "title": data["title"],
        "grade": grade_2x2(verdict, wealth_level, composure),
        "epilogue": epilogue,
    }
