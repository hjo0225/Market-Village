"""§9.2.2/§9.2.3 교류 — 1:1 권유 + FGI 단톡방 개입 (순수/결정론).

1:1 권유(§9.2.2): 위기 개입(§11.4)과 **같은 문법**(래포+격앙, roll<성공률→성공) —
단 전략 A/B/C 대신 격화/안정 방향 하나만(가볍고 빈번한 평소 관리). 위기 개입과
**같은 래포 풀**을 공유한다(§11.4.4) — 여기서도 `resistance.update_rapport`를
그대로 쓴다.

FGI 단톡방(§9.2.3): 익명 참여자로 글을 얹는 것이라 **래포가 안 통한다**(그래서
`fgi_post`는 rapport를 받지 않는다). 톤-감정 적합으로만 먹히고, 약하고 불확실
(묻힐 수 있음), 군중 자체가 이미 극단이면 흡수되어 아예 안 먹힌다(§9.3 폭주방지
정합).
"""

from __future__ import annotations

import json
import random
from functools import lru_cache
from pathlib import Path

from . import personas as _personas
from . import resistance as RES
from . import tuning as T

# --------------------------------------------------------------------------- #
# 1:1 권유 (§9.2.2)
# --------------------------------------------------------------------------- #
DIRECTION_CALM = "calm"
DIRECTION_ESCALATE = "escalate"


def persuade_success(rapport: float, escalation: float = 0.0) -> float:
    """§9.2.2 — 위기개입과 같은 문법(§11.5.3), 전략적합 항만 뺌(구조 단순화).

    base 50 + (래포−50)×0.4 − 격앙×0.5, clamp(0, 95) — 대화 권유는 결코 100%
    먹히지 않는다(가볍지만 확실하진 않음).
    """
    raw = T.RESIST_BASE + (rapport - T.RAPPORT_MID) * T.RAPPORT_SCALE - escalation * T.ESCALATION_SCALE
    return T.clamp(raw, 0.0, 95.0)


def apply_persuasion(
    direction: str, stat_name: str, stats: dict[str, float],
    rapport: float, roll: float = 100.0, escalation: float = 0.0,
) -> dict:
    """권유 1건 적용 — 성공하면 방향대로 관련 스탯 ±(§11.5.4 대화권유 보정 3),
    실패해도 성공해도 래포는 갱신된다(같은 풀, §11.4.4). roll<성공률 → 성공.
    """
    prob = persuade_success(rapport, escalation)
    accepted = roll < prob
    new_stats = dict(stats)
    if accepted and stat_name in new_stats:
        delta = T.PERSUASION_BONUS if direction == DIRECTION_CALM else -T.PERSUASION_BONUS
        new_stats[stat_name] = T.clamp(new_stats[stat_name] + delta, T.STAT_MIN, T.STAT_MAX)
    new_rapport = RES.update_rapport(rapport, accepted)
    return {"accepted": accepted, "success_prob": prob, "stats": new_stats, "rapport": new_rapport}


# --------------------------------------------------------------------------- #
# FGI 단톡방 (§9.2.3) — 익명 참여자, 래포 무관, 약하고 불확실
# --------------------------------------------------------------------------- #
# PRD §11.5엔 FGI 전용 수치가 없음 — 1:1(±3)보다 확실히 작게 잡은 튜닝 출발점.
_FGI_MAGNITUDE = 2.0
_FGI_APPLY_CHANCE = 40.0     # 0~100 스케일. 여러 목소리 중 하나라 안 먹힐 수 있음.
_FGI_ABSORB_THRESHOLD = 90.0  # 이미 만렙으로 들끓는 방이면 플레이어 글이 묻힘.

_TONE_DIRECTION = {"calm": -1, "clarify": -1, "fear_join": 1}


def fgi_post(
    tone: str, crowd_mood: float, clone_stat_value: float, roll: float = 100.0,
) -> dict:
    """단톡방에 톤 하나를 얹는다. crowd_mood는 군중 과열도(높을수록 들끓음).

    이미 만렙(≥90)으로 들끓으면 흡수(안 먹힘, §9.3 폭주방지). 아니면 확률적으로
    (roll<40) 군중을 톤 방향으로, 클론은 그 절반만 반대(완화)로 살짝 민다.
    """
    if crowd_mood >= _FGI_ABSORB_THRESHOLD:
        return {"crowd_mood": crowd_mood, "clone_stat_value": clone_stat_value,
                "clone_delta_applied": 0.0, "absorbed": True}
    if roll >= _FGI_APPLY_CHANCE:
        return {"crowd_mood": crowd_mood, "clone_stat_value": clone_stat_value,
                "clone_delta_applied": 0.0, "absorbed": False}

    direction = _TONE_DIRECTION.get(tone, 0)
    new_crowd = T.clamp(crowd_mood + direction * _FGI_MAGNITUDE, 0.0, 100.0)
    clone_delta = -direction * _FGI_MAGNITUDE * 0.5   # 군중 진정 → 클론 내성 소폭↑
    new_clone = T.clamp(clone_stat_value + clone_delta, T.STAT_MIN, T.STAT_MAX)
    return {"crowd_mood": new_crowd, "clone_stat_value": new_clone,
            "clone_delta_applied": clone_delta, "absorbed": False}


# --------------------------------------------------------------------------- #
# 게시판(SNS형 FGI) — T-223, 부속 PRD(PRD_SOCIAL_NPC_BOARD) §3.2
# 관찰 이벤트(D6): 수동 개입(fgi_post)과 별개 경로. 기존 함수들은 무변경.
# --------------------------------------------------------------------------- #
_REPO_ROOT = Path(__file__).resolve().parents[2]
BOARD_POOL_PATH = _REPO_ROOT / "board_pool.seed.json"

# 트리거 컨텍스트 매핑(D2 개정): 시장 급변동이 우선, 없으면 고강도 뉴스의 톤.
# 클론 개인의 함정(위기)은 마을의 공개 이벤트가 아니므로 게시판과 무관하다
# (사용자 재정의 2026-07-02 — 함정 연동은 오늘 위기를 아침에 누설하는 부작용도 있었다).
_TONE_CONTEXT = {"fear": "fear", "optimism": "fomo", "uncertain": "unrest"}

# 컨텍스트 ↔ 클론 감정 반응 판정에 쓰는 관련 스탯(D9 개정 — 수치는 규칙, 문구는 표현).
_STAT_FOR_CONTEXT = {"fear": "급락패닉저항", "greed": "과대베팅제어",
                     "fomo": "추격매수저항", "unrest": "멘탈마모저항"}

# 컨텍스트별 출연진(§7.3) — 글 관중 / 댓글 관중(반박·부채질).
_BOARD_CAST = {
    "fear": {"posts": ["doomposter", "newbie", "troll"],
             "comments": ["cheerleader", "anon_veteran", "newbie"]},
    "greed": {"posts": ["bull_hoper", "cheerleader", "chart_zealot"],
              "comments": ["contrarian_fan", "anon_veteran", "troll"]},
    "fomo": {"posts": ["bull_hoper", "newbie", "chart_zealot"],
             "comments": ["doomposter", "contrarian_fan"]},
    "unrest": {"posts": ["chart_zealot", "newbie", "troll"],
               "comments": ["anon_veteran", "cheerleader", "newbie"]},
}
# 이벤트 날 군중은 들끓는다(관찰 이벤트라 §9.2.3 수동 개입보다 크게, §9.3 폭주는
# crowd_mood 상한이 이미 clamp).
# T-250(council F4) — crowd_mood를 FGI 그대로 해석(0=극공포, 100=극탐욕 — run_loop의
# fgi/crowd_buying 프록시와 정합). 공포 계열은 음수(공포로), 탐욕 계열은 양수(과열로).
_BOARD_MOOD_DELTA = {"fear": -3.5, "greed": 2.5, "fomo": 3.5, "unrest": -1.5}

_SNS_NAME = {p["id"]: p["name"] for p in _personas.SNS_PERSONAS}
_SNS_ROLE = {p["id"]: p["role"] for p in _personas.SNS_PERSONAS}   # T-246 부기 표기
_SNS_PORTRAIT = {p["id"]: p["portrait"] for p in _personas.SNS_PERSONAS}


@lru_cache(maxsize=2)
def _load_board_pool(path_str: str) -> dict:
    with open(path_str, encoding="utf-8") as f:
        return json.load(f)


def board_trigger(market_move_pct: float, drawn_news: list[dict]) -> str | None:
    """D2 개정 — 오늘 게시판이 열리는가. 열리면 컨텍스트(fear/greed/fomo/unrest).

    게시판은 **마을의 공개 이벤트**에만 반응한다: ①시장 급변동(전일 대비 ±기준,
    급락→공포 수다·급등→불장 수다) ②그날 뽑힌 고강도 뉴스(그 톤으로). 클론
    개인의 함정은 여기서 보지 않는다(비공개 §12.4 — 게시판이 위기를 누설 금지).
    """
    if market_move_pct <= -T.BOARD_MARKET_MOVE_PCT:
        return "fear"
    if market_move_pct >= T.BOARD_MARKET_MOVE_PCT:
        return "fomo"
    for n in drawn_news:
        if n.get("intensity") in ("high", "extreme"):
            return _TONE_CONTEXT.get(n.get("tone", ""), "unrest")
    return None


def _board_llm_rewrite(text: str, author_name: str, style: str) -> str | None:
    """(opt-in) 표현만 리라이트 — 실패/키없음이면 None(템플릿 유지, §8.6.3)."""
    try:
        from .llm import LLMClient  # lazy: 키/네트워크 없어도 import OK
        client = LLMClient()
        out = client.chat(
            system="너는 투자 커뮤니티 게시글 한 문장만 출력한다. 따옴표·설명 없이.",
            user=(f"'{author_name}'({style}) 말투로, 아래 글을 같은 뜻의 다른 문장으로: "
                  f"\"{text}\""))
        out = (out or "").strip()
        return out or None
    except Exception:
        return None


def board_event(
    context: str, clone_stats: dict[str, float],
    rng: random.Random, use_llm: bool = False,
) -> dict:
    """이벤트 날 게시판 피드 1회분 생성(D8·D9 개정 — 구성은 규칙, 표현은 opt-in LLM).

    클론도 매 게시판에 참여하되(D9), 글 내용은 함정이 아니라 **이벤트에 대한 감정
    반응**이다: 컨텍스트 관련 스탯이 낮으면 동요(shaken), 높으면 침착(steady) 문구.
    반환: {"context", "posts": [...], "crowd_mood_delta"} — 적용(캐시·crowd_mood
    이동)은 호출자(GameRun)의 몫. 순수함수(같은 rng 시드 = 같은 피드).
    """
    pool = _load_board_pool(str(BOARD_POOL_PATH))
    cast = _BOARD_CAST[context]

    def pick_text(section: str, pid: str) -> str | None:
        variants = pool.get(section, {}).get(pid, {}).get(context)
        return rng.choice(variants) if variants else None

    posts: list[dict] = []
    for pid in cast["posts"]:
        text = pick_text("posts", pid)
        if text is None:
            continue
        if use_llm:
            style = next((p["style"] for p in _personas.SNS_PERSONAS if p["id"] == pid), "")
            text = _board_llm_rewrite(text, _SNS_NAME[pid], style) or text
        posts.append({"author": _SNS_NAME[pid], "author_role": _SNS_ROLE[pid],
                      "author_id": pid, "author_kind": "sns",
                      "portrait": _SNS_PORTRAIT[pid], "text": text, "comments": []})

    # 댓글 1~2개 — 반대 성향 관중이 임의 글에 답글(상호작용, 결정론 규칙).
    if posts:
        n_comments = 1 + rng.randrange(2)
        commenters = [pid for pid in cast["comments"] if pick_text("comments", pid)]
        for pid in commenters[:n_comments]:
            target = posts[rng.randrange(len(posts))]
            target["comments"].append(
                {"author": _SNS_NAME[pid], "author_role": _SNS_ROLE[pid],
                 "author_id": pid, "text": pick_text("comments", pid)})

    # D9 개정 — 클론도 이벤트에 대한 감정 반응으로 참여(함정·위기 무관, 누설 없음).
    stat_name = _STAT_FOR_CONTEXT.get(context, "멘탈마모저항")
    mood_key = "steady" if clone_stats.get(stat_name, 50.0) >= 50.0 else "shaken"
    clone_variants = pool.get("clone", {}).get(context, {}).get(mood_key)
    if clone_variants:
        text = rng.choice(clone_variants)
        if use_llm:
            text = _board_llm_rewrite(text, "내 클론", "이벤트에 반응하는 투자 초심자") or text
        posts.append({"author": "내 클론", "author_role": None,
                      "author_id": "clone", "author_kind": "clone",
                      "portrait": None, "text": text, "comments": []})

    return {"context": context, "posts": posts,
            "crowd_mood_delta": _BOARD_MOOD_DELTA[context]}
