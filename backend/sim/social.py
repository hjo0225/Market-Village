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
from .clone_spec import CloneSpec

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

# 트리거 컨텍스트 매핑(D2): 함정이 우선, 없으면 고강도 뉴스의 톤.
_TRAP_CONTEXT = {"F1": "fear", "F2": "fear", "G1": "greed", "G2": "greed",
                 "M1": "fomo", "M2": "fomo"}
_TONE_CONTEXT = {"fear": "fear", "optimism": "fomo", "uncertain": "unrest"}

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
_BOARD_MOOD_DELTA = {"fear": 3.5, "greed": 2.5, "fomo": 3.5, "unrest": 1.5}

_SNS_NAME = {p["id"]: p["name"] for p in _personas.SNS_PERSONAS}
_SNS_PORTRAIT = {p["id"]: p["portrait"] for p in _personas.SNS_PERSONAS}


@lru_cache(maxsize=2)
def _load_board_pool(path_str: str) -> dict:
    with open(path_str, encoding="utf-8") as f:
        return json.load(f)


def board_trigger(trap: str | None, drawn_news: list[dict]) -> str | None:
    """D2 — 오늘 게시판이 열리는가. 열리면 컨텍스트(fear/greed/fomo/unrest).

    위기 발동(trap)이 우선. 아니면 그날 뽑힌 뉴스 3개 중 intensity high/extreme이
    있을 때 그 톤으로 연다(위기로 안 이어졌어도 마을은 시끄럽다).
    """
    if trap:
        return _TRAP_CONTEXT.get(trap, "fear")
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
    context: str, clone_spec: CloneSpec, trap: str | None,
    rng: random.Random, use_llm: bool = False,
) -> dict:
    """이벤트 날 게시판 피드 1회분 생성(D8·D9 — 구성은 규칙, 표현은 opt-in LLM).

    반환: {"context", "posts": [{author, author_id, author_kind, portrait, text,
    comments: [{author, text}]}], "crowd_mood_delta"} — 적용(캐시·crowd_mood 이동)은
    호출자(GameRun.board_today)의 몫. 순수함수(같은 rng 시드 = 같은 피드).
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
        posts.append({"author": _SNS_NAME[pid], "author_id": pid, "author_kind": "sns",
                      "portrait": _SNS_PORTRAIT[pid], "text": text, "comments": []})

    # 댓글 1~2개 — 반대 성향 관중이 임의 글에 답글(상호작용, 결정론 규칙).
    if posts:
        n_comments = 1 + rng.randrange(2)
        commenters = [pid for pid in cast["comments"] if pick_text("comments", pid)]
        for pid in commenters[:n_comments]:
            target = posts[rng.randrange(len(posts))]
            target["comments"].append(
                {"author": _SNS_NAME[pid], "author_id": pid,
                 "text": pick_text("comments", pid)})

    # D9 — 클론 게시: 함정을 겪은 날이면 합리화 언어(§12.0 narrate와 같은 소스).
    if trap and clone_spec.rationalization.get(trap):
        text = rng.choice(clone_spec.rationalization[trap])
        posts.append({"author": "내 클론", "author_id": "clone", "author_kind": "clone",
                      "portrait": None, "text": text, "comments": []})

    return {"context": context, "posts": posts,
            "crowd_mood_delta": _BOARD_MOOD_DELTA[context]}
