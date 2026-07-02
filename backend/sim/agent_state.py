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
from .tuning import clamp

AXES = ("fear", "greed", "confidence", "excitement", "trust")
DECAY = 0.15          # 밤마다 편차의 15%가 baseline으로 회귀
BAND = 25.0           # baseline ± 밴드 클램프

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
