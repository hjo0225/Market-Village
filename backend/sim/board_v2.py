"""게시판 v2 — 에이전트 대화 시뮬 기반 피드 (T-251~253, 🤖 council 설계).

플레이테스트 리포트 ③⑩⑪: 게시판은 "그날 뉴스로 가격이 오를까 내릴까"를 논의한
**대화**여야 하고(일반론 금지), 글마다 댓글 수가 다르며, 클론은 혼잣말 결론이
아니라 대화 참여자다. 과열도 델타도 고정값이 아니라 대화 결과 기반.

구조(council F1·F2):
- 대화 1건 = conversation dict(스키마 아래) — LLM 1콜(safe_json) 또는 오프라인
  결정론 폴백(offline_conversation)이 **같은 스키마**를 채운다. 소비자는 LLM
  여부를 모른다.
- 생성 결과는 GameRun.board_archive에 (day, news_id) 키로 **박제**된다 — 같은
  게임의 다른 회차가 같은 날 같은 뉴스를 만나면 그대로 재사용(공개 이벤트 트랙
  = 회차 무관 동일, 결정론·거울 비교 보호).

conversation 스키마:
{
  "verdict": "up"|"down"|"split",          # 대화의 다수 결론
  "threads": [                              # 게시글 1개 = thread 1개 (2개 이상)
    {"author_id", "stance": "up"|"down"|"split", "text",
     "comments": [{"author_id", "stance", "text"}, ...]},   # 0~N 가변
  ],
  "agent_deltas": {aid: {axis: float}},     # 참여자 감정 이동(±8 클램프)
  "crowd_delta": float,                     # 부호 있음(±6 클램프, T-250)
}
"""

from __future__ import annotations

import random

from . import personas as _personas
from . import social as _social
from . import tuning as T

_SNS_IDS = {p["id"] for p in _personas.SNS_PERSONAS}
_TRADER_IDS = {p["id"] for p in _personas.TRADER_PERSONAS}
_ALL_CAST = _SNS_IDS | _TRADER_IDS
_NAME = {p["id"]: p["name"] for p in _personas.SNS_PERSONAS + _personas.TRADER_PERSONAS}
_ROLE = {p["id"]: p["role"] for p in _personas.SNS_PERSONAS + _personas.TRADER_PERSONAS}
_PORTRAIT = {p["id"]: p.get("portrait") for p in
             _personas.SNS_PERSONAS + _personas.TRADER_PERSONAS}
_STYLE = {p["id"]: p.get("style", "") for p in
          _personas.SNS_PERSONAS + _personas.TRADER_PERSONAS}

AGENT_DELTA_CLAMP = 8.0     # 이벤트당 축 이동 상한(council F4)

# 컨텍스트 → 발언 스탠스 기본값(오프라인 폴백): 공포 수다는 '내린다' 우세.
_CONTEXT_STANCE = {"fear": "down", "unrest": "down", "greed": "up", "fomo": "up"}
# 관중 성향 → 스탠스 뒤집기(청개구리·역발상은 다수 반대편에 선다).
_CONTRARIAN = {"contrarian_fan", "anon_veteran", "doomposter"}
# 페르소나 주축(오프라인 agent_deltas 규칙표) — §9.5.2 수치는 높을수록 취약.
_MAIN_AXIS = {"doomposter": "fear", "newbie": "fear", "bull_hoper": "excitement",
              "cheerleader": "excitement", "chart_zealot": "confidence",
              "troll": "excitement", "anon_veteran": "confidence",
              "contrarian_fan": "confidence"}


def _news_line(drawn_news: list[dict]) -> tuple[str, str]:
    """(news_id, 사람이 읽는 한 줄) — 대화의 주제. 고강도 우선, 없으면 시장 급변동."""
    for n in drawn_news:
        if n.get("intensity") in ("high", "extreme"):
            return n.get("id", "news"), n.get("headline", n.get("title", ""))
    return "mkt", ""


def _intensity_scale(drawn_news: list[dict]) -> float:
    """⑪ — 델타가 이벤트 급에 따라 달라진다: extreme 1.6 · high 1.2 · 시장만 1.0."""
    levels = {n.get("intensity") for n in drawn_news}
    if "extreme" in levels:
        return 1.6
    if "high" in levels:
        return 1.2
    return 1.0


def validate(conv: dict | None, extra_cast: set[str] | None = None) -> dict | None:
    """LLM 출력 검증(신뢰 금지) — 화이트리스트 밖 발언 drop·델타 클램프·구조 강제."""
    if not isinstance(conv, dict):
        return None
    cast = _ALL_CAST | {"clone"} | (extra_cast or set())
    threads = []
    for th in conv.get("threads", []):
        if not isinstance(th, dict) or th.get("author_id") not in cast:
            continue
        if not (th.get("text") or "").strip():
            continue
        comments = [c for c in th.get("comments", [])
                    if isinstance(c, dict) and c.get("author_id") in cast
                    and (c.get("text") or "").strip()]
        threads.append({"author_id": th["author_id"],
                        "stance": th.get("stance") or "split",
                        "text": str(th["text"]).strip(),
                        "comments": [{"author_id": c["author_id"],
                                      "stance": c.get("stance") or "split",
                                      "text": str(c["text"]).strip()}
                                     for c in comments]})
    if len(threads) < 2:
        return None
    deltas = {}
    for aid, axes in (conv.get("agent_deltas") or {}).items():
        if aid not in cast or not isinstance(axes, dict):
            continue
        deltas[aid] = {str(k): T.clamp(float(v), -AGENT_DELTA_CLAMP, AGENT_DELTA_CLAMP)
                       for k, v in axes.items()
                       if isinstance(v, (int, float))}
    try:
        crowd = T.clamp(float(conv.get("crowd_delta", 0.0)),
                        -T.CROWD_DELTA_CLAMP, T.CROWD_DELTA_CLAMP)
    except (TypeError, ValueError):
        crowd = 0.0
    verdict = conv.get("verdict")
    if verdict not in ("up", "down", "split"):
        verdict = "split"
    return {"verdict": verdict, "threads": threads,
            "agent_deltas": deltas, "crowd_delta": crowd}


def offline_conversation(
    context: str, clone_stats: dict[str, float], drawn_news: list[dict],
    rng: random.Random,
) -> dict:
    """오프라인 결정론 폴백 — 기존 board_pool 문구를 대화 스키마로 조립.

    글 2~3개·글마다 댓글 0~3개 가변(리포트 ③), 스탠스는 컨텍스트+성향 규칙,
    agent_deltas는 규칙표(작성자 주축 ±4·댓글자 ±2), crowd_delta는 부호(T-250)
    × 뉴스 강도 스케일(⑪).
    """
    base = _social.board_event(context, clone_stats, rng, use_llm=False)
    majority = _CONTEXT_STANCE.get(context, "split")
    _ = clone_stats  # 클론 발언은 아카이브에 넣지 않는다 — inject_clone이 회차별 주입
    flip = {"up": "down", "down": "up"}.get(majority, "split")

    threads = []
    for post in base["posts"]:
        aid = post["author_id"]
        if aid == "clone":
            continue    # 클론은 inject_clone에서 회차별로
        stance = flip if aid in _CONTRARIAN else majority
        comments = [{"author_id": c["author_id"],
                     "stance": flip if c["author_id"] in _CONTRARIAN else majority,
                     "text": c["text"]} for c in post.get("comments", [])]
        threads.append({"author_id": aid, "stance": stance,
                        "text": post["text"], "comments": comments})

    # 댓글 풍부화(리포트 ③ — "댓글 없는 게시물, 있어도 1개"): 관중 코멘트 풀에서
    # 글마다 0~3개를 추가로 붙인다(결정론 rng — 글마다 개수가 다름).
    pool = _social._load_board_pool(str(_social.BOARD_POOL_PATH))
    cast = _social._BOARD_CAST[context]
    for th in threads:
        for _ in range(rng.randrange(4)):                       # 0~3
            pid = cast["comments"][rng.randrange(len(cast["comments"]))]
            variants = pool.get("comments", {}).get(pid, {}).get(context)
            if not variants:
                continue
            th["comments"].append({
                "author_id": pid,
                "stance": flip if pid in _CONTRARIAN else majority,
                "text": rng.choice(variants)})

    deltas: dict[str, dict[str, float]] = {}
    for th in threads:
        axis = _MAIN_AXIS.get(th["author_id"], "excitement")
        deltas.setdefault(th["author_id"], {})[axis] = 4.0
        for c in th["comments"]:
            if c["author_id"] == "clone":
                continue
            axis = _MAIN_AXIS.get(c["author_id"], "excitement")
            d = deltas.setdefault(c["author_id"], {})
            d[axis] = min(AGENT_DELTA_CLAMP, d.get(axis, 0.0) + 2.0)

    crowd = T.clamp(base["crowd_mood_delta"] * _intensity_scale(drawn_news),
                    -T.CROWD_DELTA_CLAMP, T.CROWD_DELTA_CLAMP)
    votes = [th["stance"] for th in threads]
    verdict = ("up" if votes.count("up") > votes.count("down")
               else "down" if votes.count("down") > votes.count("up") else "split")
    return {"verdict": verdict, "threads": threads,
            "agent_deltas": deltas, "crowd_delta": round(crowd, 2)}


def llm_conversation(
    context: str, drawn_news: list[dict], market_move_pct: float,
    memory_digests: dict[str, str],
    client=None,
) -> dict | None:
    """LLM 1콜 대화 생성(council F1) — 실패·키 없음·검증 탈락이면 None(폴백은 호출자).

    프롬프트는 "이 뉴스로 가격이 오를까 내릴까"를 명시(리포트 ⑩ — 일반론 금지).
    """
    try:
        from .llm import LLMClient, extract_json
        cli = client or LLMClient()
        if not cli.available:
            return None
        news_id, headline = _news_line(drawn_news)
        cast = list(_social._BOARD_CAST[context]["posts"]) + \
            list(_social._BOARD_CAST[context]["comments"])
        cast_lines = "\n".join(
            f"- {aid} ({_NAME[aid]}·{_ROLE[aid]}): {_STYLE[aid]}"
            + (f" | 기억: {memory_digests[aid]}" if memory_digests.get(aid) else "")
            for aid in dict.fromkeys(cast))
        user = f"""마을 투자 커뮤니티에서 오늘 사건을 두고 벌어진 대화를 JSON으로 생성해라.

오늘 사건: {'뉴스 "' + headline + '"' if headline else '시장 급변동'} (전일 대비 {market_move_pct:+.1f}%, 분위기: {context})
핵심 규칙: 발언은 반드시 "이 사건으로 가격이 오를까 내릴까"에 대한 각자의 전망·논쟁이어야 한다. 막연한 '오른다/내린다' 일반론 금지 — 사건 내용을 물고 늘어져라.
참여자(author_id는 이 목록에서만):
{cast_lines}
(클론 발언은 시스템이 따로 주입한다 — 위 목록의 관중들만 등장시켜라.)

출력(JSON만): {{"verdict": "up|down|split", "threads": [{{"author_id", "stance": "up|down|split", "text", "comments": [{{"author_id", "stance", "text"}}]}}], "agent_deltas": {{author_id: {{"fear|greed|confidence|excitement|trust": -8~8}}}}, "crowd_delta": -6~6}}
threads는 2~4개, 글마다 comments 0~4개(개수를 다르게), 한국어 커뮤니티 말투."""
        raw = cli.chat(user=user, system="투자 커뮤니티 대화 시뮬레이터. JSON만 출력.",
                       temperature=0.8)
        return validate(extract_json(raw))
    except Exception:
        return None


def to_posts(conv: dict) -> list[dict]:
    """conversation → 기존 프론트 계약(posts) 어댑터 — BoardEventModal 무수정 호환."""
    posts = []
    for th in conv["threads"]:
        aid = th["author_id"]
        posts.append({
            "author": _NAME.get(aid, "내 클론" if aid == "clone" else aid),
            "author_role": _ROLE.get(aid),
            "author_id": aid,
            "author_kind": "clone" if aid == "clone" else "sns",
            "portrait": _PORTRAIT.get(aid),
            "stance": th.get("stance"),
            "text": th["text"],
            "comments": [{
                "author": _NAME.get(c["author_id"],
                                    "내 클론" if c["author_id"] == "clone" else c["author_id"]),
                "author_role": _ROLE.get(c["author_id"]),
                "author_id": c["author_id"],
                "stance": c.get("stance"),
                "text": c["text"]} for c in th.get("comments", [])],
        })
    return posts


def inject_clone(
    conv: dict, context: str, clone_stats: dict[str, float], rng: random.Random,
) -> dict:
    """클론을 **댓글이 가장 많은 글의 답글**로 참여시킨다(대화 참여자, 리포트 ③).

    아카이브(공개 트랙)는 회차 불변이라 클론 발언을 담지 않는다(council F2) —
    이 함수가 회차별 클론 상태(D9: 관련 스탯 steady/shaken)로 매번 주입한다.
    원본 conv는 변경하지 않고 사본을 돌려준다.
    """
    import copy
    out = copy.deepcopy(conv)
    if not out.get("threads"):
        return out
    pool = _social._load_board_pool(str(_social.BOARD_POOL_PATH))
    stat = _social._STAT_FOR_CONTEXT.get(context, "멘탈마모저항")
    steady = clone_stats.get(stat, 50.0) >= 50.0
    variants = pool.get("clone", {}).get(context, {}).get(
        "steady" if steady else "shaken")
    if not variants:
        return out
    majority = _CONTEXT_STANCE.get(context, "split")
    flip = {"up": "down", "down": "up"}.get(majority, "split")
    target = max(out["threads"], key=lambda th: len(th["comments"]))
    target["comments"].append({
        "author_id": "clone",
        "stance": (flip if steady else majority),
        "text": rng.choice(variants)})
    return out
