"""§12.0/§8.6.3 표현 계층 — 엔진 결정을 연출명령 + 대사로 *서술*.

흐름은 단방향: `엔진(결정) → 표현(연기)`. 표현은 [1]~[4]에서 끝난 수치 결정을
바꾸지 않는다(§8.6.3). 맵은 연출명령(emote/trade/move)을 연기하고, 대사는 클론의
합리화 언어(§5.1 3층)에서 나와 가장 아픈 거울이 된다. 속마음(독백)은 결정적
순간(위기·씹힘·밤 회고)에만 열린다(§12.0b) — 희소해서 더 강렬.

기본은 **오프라인 결정론 템플릿**(키 없이 동작). LLM은 키 있을 때 표현만 교체
(opt-in `use_llm`, 수치 결정 무관). 자율 빌드는 LLM 실호출 안 함(과금 게이트).
"""

from __future__ import annotations

from .clone_spec import CloneSpec
from .runs import DailySnapshot
from .traps import get_trap

# 함정 그룹 → 클론 감정 연출(emote)
_GROUP_EMOTION = {"fear": "panic", "greed": "greedy", "fomo": "fomo"}
_NEUTRAL_LINE = "조용히 하루를 보낸다."
_RESIST_LINE = "...버텼다. 이번엔 안 흔들렸어."


def narrate(snap: DailySnapshot, clone_spec: CloneSpec, *, use_llm: bool = False) -> dict:
    """하루 결정(snap) → {commands, dialogue, monologue_open} (결정론 템플릿)."""
    trap = snap.trap
    swayed = bool(snap.swayed)
    monologue_open = bool(trap) or swayed   # 결정적 순간에만 속마음 개방(§12.0b)

    if swayed and trap and clone_spec.rationalization.get(trap):
        dialogue = clone_spec.rationalization[trap][0]   # 합리화 언어(거울)
    elif trap:
        dialogue = _RESIST_LINE
    else:
        dialogue = _NEUTRAL_LINE

    commands: list[dict] = []
    if trap:
        t = get_trap(trap)
        emotion = _GROUP_EMOTION.get(t.group, "tense") if t else "tense"
        commands.append({"emote": "clone", "emotion": emotion})
    else:
        commands.append({"emote": "clone", "emotion": "calm"})
    if swayed and snap.fund_flow:
        commands.append({"trade": "clone", "action": snap.fund_flow})
    # T-216 D4 — 번들(2개 이상 동시 트리거)이면 snap.fund_flow는 모호해서
    # 비워 둔다(단일값이 아니므로) — 번들 안 각 swayed 항목을 개별 연출한다.
    # 크기 1 번들은 이미 위에서 snap.fund_flow로 잡히므로 여기서 건너뛴다.
    if len(snap.bundle) > 1:
        for b in snap.bundle:
            if not b["resisted"] and b["fund_flow"]:
                commands.append({"trade": "clone", "action": b["fund_flow"], "category": b["category"]})

    if use_llm:
        dialogue = _llm_rewrite(dialogue, snap, clone_spec) or dialogue

    return {"commands": commands, "dialogue": dialogue, "monologue_open": monologue_open}


def _llm_rewrite(template: str, snap: DailySnapshot, clone_spec: CloneSpec) -> str | None:
    """(opt-in) LLM으로 대사 표현만 다듬는다 — 실패/키없음이면 None(템플릿 유지).

    §8.6.3: LLM은 표현만, 수치 결정 무관. 키는 .env의 OPENROUTER_API_KEY(또는 OS
    OPENAI_API_KEY). 과금 게이트라 호출자가 명시적으로 use_llm=True일 때만.
    """
    try:
        from .llm import LLMClient  # lazy: 키/네트워크 없어도 import OK
        client = LLMClient()
        prompt = (
            f"클론이 '{snap.trap}' 함정 상황에서 속으로 하는 한 마디를, 아래 합리화 "
            f"톤으로 한 문장 한국어로: \"{template}\". 따옴표·설명 없이 문장만."
        )
        out = client.chat(system="너는 게임 캐릭터의 속마음 한 문장만 출력한다.",
                          user=prompt)
        out = (out or "").strip()
        return out or None
    except Exception:
        return None
