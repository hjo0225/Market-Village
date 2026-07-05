# -*- coding: utf-8 -*-
"""T-281 · 만남 1:1 대화 생성 — 핸드폰 채팅 연출용(표현 전용).

사용자 반복 피드백(2026-07-05): 만남 대화는 맵 말풍선이 아니라 **핸드폰 채팅창**.
여기는 표현 계층만 — 대사는 (game_id, day, npc_id) 결정론이고 게임 수치에 영향을
주지 않는다(만남의 감정 효과는 기존 밤 정산 그대로, T-249).

구성: NPC 화두(페르소나 성향) → 클론 반응 → NPC 마무리.
- 자극형(stim_trap 有)의 화두는 그 함정을 찌르고, 클론 반응은 그 함정의 관련
  스탯 steady/shaken(≥50/<50)으로 갈린다 — 게시판 클론 발화(D9)와 같은 규칙.
- 도움형(stim_trap=None)의 화두는 조언이고, 클론은 수긍 반응.
"""
from __future__ import annotations

import random
from zlib import crc32

from .clone_stats import _TRAP_STAT
from . import personas as _personas

# 페르소나별 화두 — 표현만(§9.5.3 성격 그대로). id는 personas.TRADER_PERSONAS.
_OPENERS: dict[str, list[str]] = {
    "panic_ant": [
        "요즘 차트 봤어? 난 어제 다 던졌어. 너도 늦기 전에 정리해",
        "이거 진짜 무너지는 그림이야. 나 어제 손 떨려서 잠도 못 잤다",
    ],
    "fomo_scalper": [
        "옆 종목 오늘도 갔다? 이 버스 놓치면 다음은 없어",
        "지금이 단타 각이야. 고민하는 사이에 남들 다 탄다",
    ],
    "conspiracy_influencer": [
        "다들 모르는 얘기 하나 해줄까. 큰손들이 지금 몰래 모으고 있대",
        "이 분위기, 누가 일부러 만드는 거야. 곧 크게 한 번 온다",
    ],
    "value_investor": [
        "가격 말고 가치를 봐. 오늘 같은 날일수록 원칙이 중요해",
        "급할수록 한 템포 쉬어. 시장은 내일도 열려",
    ],
    "quant_trader": [
        "데이터로는 아직 아무 신호 없어. 감으로 움직이지 마",
        "변동성 커질 땐 포지션부터 줄이는 게 내 룰이야",
    ],
    "macro_whale": [
        "큰 흐름은 하루짜리 뉴스로 안 바뀌어. 멀리 봐",
        "이럴 때 흔들리는 계좌가 제일 먼저 깨지더라",
    ],
    "contrarian": [
        "다들 한쪽으로 몰릴 때가 제일 수상해. 난 반대편을 본다",
        "공포에 사고 환호에 팔라는 말, 오늘 같은 날 쓰라고 있는 거야",
    ],
    "jackpot_gambler": [
        "인생은 한 방이야. 이번 판에 크게 실어봐",
        "찔끔찔끔 벌어서 언제 부자 되냐. 몰빵이 답이다",
    ],
}
_OPENER_FALLBACK = ["오늘 시장 어떻게 보고 있어?"]

# 클론 반응 — 자극형: 관련 스탯 steady/shaken, 도움형: 수긍.
_CLONE_STEADY = [
    "…그 말 듣고도 마음이 안 움직이네. 내 계획대로 갈래",
    "일리는 있는데, 오늘은 내 원칙대로 할게",
]
_CLONE_SHAKEN = [
    "그 말 들으니까 나도 마음이 흔들리네…",
    "어… 진짜 그런가. 갑자기 불안해진다",
]
_CLONE_HELPED = [
    "듣고 보니 숨이 좀 쉬어진다. 고마워",
    "그 말 오늘 하루 부적처럼 갖고 있을게",
]

# NPC 마무리 — 자극형/도움형 공통 2종씩.
_CLOSERS_STIM = [
    "생각 바뀌면 연락해. 시간 얼마 없다?",
    "뭐, 네 돈이니까. 난 분명히 말했다",
]
_CLOSERS_HELP = [
    "언제든 흔들리면 찾아와",
    "내일 또 보자고. 오늘은 차트 그만 봐",
]


def dialogue(game_id: str, day: int, npc_id: str,
             clone_stats: dict[str, float]) -> list[dict]:
    """만남 채팅 대사 3턴(npc→clone→npc). 결정론 시드=(game_id, day, npc_id)."""
    rng = random.Random(crc32(f"{game_id}:{day}:{npc_id}".encode("utf-8")))
    p = _personas.trader_by_id(npc_id) or {}
    trap = p.get("stim_trap")
    opener = rng.choice(_OPENERS.get(npc_id) or _OPENER_FALLBACK)
    if trap:
        stat = _TRAP_STAT.get(trap, "멘탈마모저항")
        steady = clone_stats.get(stat, 50.0) >= 50.0
        reaction = rng.choice(_CLONE_STEADY if steady else _CLONE_SHAKEN)
        closer = rng.choice(_CLOSERS_STIM)
    else:
        reaction = rng.choice(_CLONE_HELPED)
        closer = rng.choice(_CLOSERS_HELP)
    return [
        {"who": "npc", "text": opener},
        {"who": "clone", "text": reaction},
        {"who": "npc", "text": closer},
    ]
