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


def emotion_controlled(verdict: str) -> bool:
    """감정축 2단계: 중립(균형)만 감정+(통제됨). 과열·위축은 감정−."""
    return verdict == "중립"


def grade_2x2(verdict: str, wealth_level: str) -> str:
    """회차 비교용 2×2 등급(엔딩 종류와 무관하게 병기)."""
    return _GRADE[(emotion_controlled(verdict), wealth_level == "high")]


def decide_ending(verdict: str, wealth_level: str, special_count: int) -> dict:
    """엔딩 결정(문서 §4.2). 특수이벤트 N회 이상이면 히든 E5, 아니면 4분기."""
    good = emotion_controlled(verdict)
    hi = wealth_level == "high"
    if special_count >= SPECIAL_EVENT_ENDING_N:
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
    return {
        "id": ending_id,
        "title": data["title"],
        "grade": grade_2x2(verdict, wealth_level),
        "epilogue": list(data["epilogue"]),
    }
