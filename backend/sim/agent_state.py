"""에이전트 감정·기억 — board_archive의 순수 파생 (T-254, 🤖 council F3).

사용자 요구(리포트 ⑥): "에이전트 세션을 열어놓고 메모리를 활용(이전 날들의 FGI
기억), 에이전트마다 감정 수치 변화가 다르게" — 을 **신규 가변 상태 0**으로 구현:
GameRun.board_archive(공개 트랙 박제)가 유일한 원본이고, 각 에이전트의 감정
현재값과 기억 다이제스트는 매번 여기서 fold로 파생한다(npc_traders M4 패턴 —
직렬화·회차 리셋·라운드트립·재시작 안전이 전부 공짜).

R6 3칸: 감쇠 15%/일 · 이벤트당 축 ±8(board_v2.validate) · 평형 = 페르소나
baseline, 밴드 클램프 ±25 (지속 최대 편차 8×0.85/0.15 ≈ 45 > 25라 밴드가 먼저
문다 — "공포팔이가 치어리더로 영구 변신" 구조적 차단).
"""

from __future__ import annotations

from . import personas as _personas
from . import tuning as _T
from .tuning import clamp

AXES = ("fear", "greed", "confidence", "excitement", "trust")
# T-a — 상수는 tuning이 단일 진실 소스(R6/R7 표준화), 여기서는 재수출만.
DECAY = _T.AGENT_EMOTION_DECAY   # 밤마다 편차의 15%가 baseline으로 회귀
BAND = _T.AGENT_EMOTION_BAND     # baseline ± 밴드 클램프

_BASELINE = {p["id"]: {a: float(p[a]) for a in AXES}
             for p in _personas.TRADER_PERSONAS + _personas.SNS_PERSONAS}


def _entries_by_day(archive: dict) -> list[tuple[int, dict]]:
    out = []
    for key, conv in archive.items():
        try:
            day = int(str(key).split(":", 1)[0])
        except ValueError:
            continue
        out.append((day, conv))
    return sorted(out, key=lambda x: x[0])


def agent_emotions(agent_id: str, archive: dict, upto_day: int) -> dict[str, float]:
    """그 에이전트의 '현재' 감정 5축 — archive 델타 fold + 일일 감쇠 + 밴드 클램프."""
    baseline = _BASELINE.get(agent_id)
    if baseline is None:
        return {}
    entries = _entries_by_day(archive)
    dev = {a: 0.0 for a in AXES}
    for day in range(0, upto_day + 1):
        for d, conv in entries:
            if d != day:
                continue
            for axis, v in (conv.get("agent_deltas", {}).get(agent_id) or {}).items():
                if axis in dev:
                    dev[axis] += float(v)
        for a in AXES:                          # 밤 감쇠(R6)
            dev[a] *= (1.0 - DECAY)
    return {a: clamp(baseline[a] + clamp(dev[a], -BAND, BAND), 0.0, 100.0)
            for a in AXES}


def _stance_of(agent_id: str, conv: dict) -> str | None:
    for th in conv.get("threads", []):
        if th.get("author_id") == agent_id:
            return th.get("stance")
        for c in th.get("comments", []):
            if c.get("author_id") == agent_id:
                return c.get("stance")
    return None


def memory_digests(archive: dict, upto_day: int, limit: int = 3) -> dict[str, str]:
    """참여자별 최근 이벤트 기억 한 줄(LLM 프롬프트 주입용, 토큰 상한 작게).

    이전 날들의 FGI(과열도 흐름)는 archive의 crowd_delta 누적 파생으로 요약 —
    플레이어 개입이 섞인 실측 crowd_mood를 쓰지 않는다(공개 트랙 오염 방지, R2).
    """
    entries = [(d, c) for d, c in _entries_by_day(archive) if d < upto_day]
    digests: dict[str, list[str]] = {}
    stance_ko = {"up": "오른다", "down": "내린다", "split": "반반"}
    for day, conv in entries:
        for aid in set(list(conv.get("agent_deltas", {}).keys())):
            st = _stance_of(aid, conv)
            if st is None:
                continue
            digests.setdefault(aid, []).append(
                f"D{day} 사건에 '{stance_ko.get(st, st)}' 전망"
                f"(마을 결론 {stance_ko.get(conv.get('verdict'), '반반')})")
    fgi_flow = sum(c.get("crowd_delta", 0.0) for _, c in entries[-limit:])
    fgi_line = (f" 최근 과열도 흐름 {fgi_flow:+.1f}" if entries else "")
    return {aid: "; ".join(lines[-limit:]) + fgi_line
            for aid, lines in digests.items()}


# --------------------------------------------------------------------------- #
# T-e 기억 발화 — 오프라인 게시판(공개 트랙)용 발화 향미. RNG 없음(결정론).
# --------------------------------------------------------------------------- #
EMO_SPEAK_DEV = 10.0   # 주축이 baseline에서 이만큼 벗어나면 감정 여운이 새어 나온다

# 기억 마커 — 지난 대화의 내 스탠스 vs 마을 결론(verdict) 3분기.
MEM_MATCHED = "지난번에도 내가 맞혔지. "
MEM_MISSED = "지난번엔 틀렸지만 이번엔 달라. "
MEM_SPLIT = "지난번처럼 또 갈리네. "

# 감정 여운 마커 — 축별 고정 문구(수치는 규칙·문구는 표현, D9 선례).
EMO_MARKER = {
    "fear": "…요즘 잠이 안 와. ",
    "excitement": "심장이 벌렁거린다. ",
    "confidence": "요즘따라 내 판단이 믿긴다. ",
    "greed": "자꾸 수익 생각만 난다. ",
    "trust": "누구 말을 믿어야 할지 모르겠다. ",
}


def speech_flavor(agent_id: str, archive: dict, upto_day: int) -> str | None:
    """발화 접두 향미 — 최대 1개(기억 우선, 없을 때만 감정 여운). 없으면 None.

    기억: 그 에이전트가 참여한 가장 최근 지난 이벤트(< upto_day)에서 내 스탠스와
    그 대화의 verdict를 대조. 감정: agent_emotions 주축(board_v2._MAIN_AXIS)이
    baseline에서 EMO_SPEAK_DEV 이상 벗어났을 때만.
    """
    entries = [(d, c) for d, c in _entries_by_day(archive) if d < upto_day]
    for _day, conv in reversed(entries):
        stance = _stance_of(agent_id, conv)
        if stance is None:
            continue                                 # 내가 안 낀 대화는 기억 아님
        verdict = conv.get("verdict")
        if verdict not in ("up", "down"):
            return MEM_SPLIT
        return MEM_MATCHED if stance == verdict else MEM_MISSED
    baseline = _BASELINE.get(agent_id)
    if baseline is None:
        return None
    from . import board_v2 as _board_v2   # 지연 import — 상호 참조 순환 차단
    axis = _board_v2._MAIN_AXIS.get(agent_id, "excitement")
    value = agent_emotions(agent_id, archive, upto_day)[axis]
    if abs(value - baseline[axis]) >= EMO_SPEAK_DEV:
        return EMO_MARKER[axis]
    return None


# --------------------------------------------------------------------------- #
# T-c 플레이어 트랙 — NPC별 래포+대화 기억. 입력은 GameRun._social_log만(R2:
# 공개 트랙 archive와 함수 시그니처로 분리). 전부 순수·결정론, 신규 직렬화 키 0.
# --------------------------------------------------------------------------- #
NPC_RAPPORT_STEP = 8.0    # 공유 풀과 같은 폭 — resistance._RAPPORT_STEP 미러
NPC_RAPPORT_DECAY = 0.10  # R6 3칸: 감쇠 0.10/일 · 클램프 [0,100] · 평형 50

# NPC 응답의 기억 접두 — 직전 기록(수락/거절)에 따라.
NPC_MEM_ACCEPTED = "저번에 네 말 듣길 잘했지. "
NPC_MEM_REJECTED = "또 너냐. "

# 래포 단계 × 수락/거절 응답 본문 — 페르소나 무관 공통 템플릿(표현 전용).
_REPLY_BODY = {
    ("cold", True): "…알았어. 이번만이다.",
    ("cold", False): "됐어. 네가 뭘 안다고.",
    ("mid", True): "그래, 일리 있네. 그렇게 해볼게.",
    ("mid", False): "글쎄, 이번엔 내 생각대로 갈래.",
    ("warm", True): "역시 너야. 네 말이면 믿지.",
    ("warm", False): "네 말이라 고민되긴 하는데… 이번엔 미안.",
}


def _npc_persuades(npc_id: str, social_log: list[dict], upto_day: int) -> list[dict]:
    return [e for e in social_log
            if e.get("kind") == "persuade" and e.get("npc_id") == npc_id
            and int(e.get("day", 0)) <= upto_day]


def npc_rapport(npc_id: str, social_log: list[dict], upto_day: int) -> float:
    """그 NPC와의 '현재' 개별 래포 — persuade 기록 fold(수락 +8/거절 −8)
    + 대화 없는 밤마다 50으로 10% 회귀 + 클램프 [0,100]. 빈 로그면 50."""
    v = 50.0
    prev_day: int | None = None
    for e in _npc_persuades(npc_id, social_log, upto_day):
        day = int(e.get("day", 0))
        if prev_day is not None and day > prev_day:
            v = 50.0 + (v - 50.0) * (1.0 - NPC_RAPPORT_DECAY) ** (day - prev_day)
        step = NPC_RAPPORT_STEP if e.get("accepted") else -NPC_RAPPORT_STEP
        v = clamp(v + step, 0.0, 100.0)
        prev_day = day
    if prev_day is not None and upto_day > prev_day:
        v = 50.0 + (v - 50.0) * (1.0 - NPC_RAPPORT_DECAY) ** (upto_day - prev_day)
    return v


def npc_chat_memory(npc_id: str, social_log: list[dict], upto_day: int,
                    limit: int = 3) -> list[dict]:
    """그 NPC와의 최근 권유 기록(day < upto_day+1) — 최신이 마지막."""
    return _npc_persuades(npc_id, social_log, upto_day)[-limit:]


def npc_reply_line(npc_id: str, direction: str, accepted: bool,
                   rapport_v: float, memory: list[dict]) -> str:
    """결정론 응답 템플릿 = 기억 접두(직전 기록) + 래포 단계 본문 × 수락/거절."""
    _ = (npc_id, direction)   # 페르소나별 변주는 v2(표현 확장 여지만 남김)
    prefix = ""
    if memory:
        prefix = NPC_MEM_ACCEPTED if memory[-1].get("accepted") else NPC_MEM_REJECTED
    tier = ("cold" if rapport_v < 35.0
            else "warm" if rapport_v > 65.0 else "mid")
    return prefix + _REPLY_BODY[(tier, bool(accepted))]
