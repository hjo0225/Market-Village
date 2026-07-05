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
# 관중 성향 → 스탠스(문구와 스탠스 배지가 어긋나지 않게 — 라이브 검증에서 발견):
# 낙관파는 항상 '오른다', 공포팔이는 항상 '내린다', 청개구리·익명고수는 다수 반대.
_ALWAYS_UP = {"bull_hoper", "cheerleader"}
_ALWAYS_DOWN = {"doomposter"}
# T-260 — 매매 에이전트 중 '이성의 목소리'(가치·퀀트·거시)와 청개구리는 다수 반대:
# 문구가 경고/역발상 톤이라 스탠스 배지도 반대여야 정합(RETRO 2026-07-03 스탠스 규칙).
_CONTRARIAN = {"contrarian_fan", "anon_veteran",
               "contrarian", "value_investor", "quant_trader", "macro_whale"}


def _stance_for(aid: str, majority: str, flip: str) -> str:
    if aid in _ALWAYS_UP:
        return "up"
    if aid in _ALWAYS_DOWN:
        return "down"
    if aid in _CONTRARIAN:
        return flip
    return majority
# 페르소나 주축(오프라인 agent_deltas 규칙표) — §9.5.2 수치는 높을수록 취약.
_MAIN_AXIS = {"doomposter": "fear", "newbie": "fear", "bull_hoper": "excitement",
              "cheerleader": "excitement", "chart_zealot": "confidence",
              "troll": "excitement", "anon_veteran": "confidence",
              "contrarian_fan": "confidence",
              # T-260 — 매매 에이전트(§9.5.2 성향 주축)
              "panic_ant": "fear", "fomo_scalper": "excitement",
              "conspiracy_influencer": "trust", "value_investor": "confidence",
              "quant_trader": "confidence", "macro_whale": "confidence",
              "contrarian": "confidence", "jackpot_gambler": "greed"}


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


def validate(conv: dict | None, extra_cast: set[str] | None = None,
             context: str | None = None) -> dict | None:
    """LLM 출력 검증(신뢰 금지) — 화이트리스트 밖 발언 drop·델타 클램프·구조 강제.

    T-230 — context가 주어지면 crowd_delta의 **부호**도 컨텍스트와 대조해 클램프
    (공포 게시판에 +6을 줘도 소비 값은 ≤0 — 방향축 의미론을 LLM이 못 깨게).
    """
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
    # T-230 — 부호 가드: 공포/뒤숭숭은 음수만, 탐욕/포모는 양수만.
    if context in ("fear", "unrest"):
        crowd = min(crowd, 0.0)
    elif context in ("greed", "fomo"):
        crowd = max(crowd, 0.0)
    # T-259 — LLM이 준 verdict를 신뢰하지 않고 노출 발화 다수결로 정정
    # (여론 라벨과 화면 인상이 어긋나는 걸 구조적으로 차단).
    return {"verdict": verdict_from_speech(threads), "threads": threads,
            "agent_deltas": deltas, "crowd_delta": crowd}


def verdict_from_speech(threads: list[dict]) -> str:
    """T-259 — 여론 = 화면에 보이는 발화 전체(글+댓글)의 up/down 다수결.

    글만 세면 댓글이 더 많은 화면에서 체감 다수와 라벨이 어긋난다(사용자 리포트).
    """
    votes = [th.get("stance") for th in threads]
    votes += [c.get("stance") for th in threads for c in th.get("comments", [])]
    ups, downs = votes.count("up"), votes.count("down")
    return "up" if ups > downs else "down" if downs > ups else "split"


def offline_conversation(
    context: str, clone_stats: dict[str, float], drawn_news: list[dict],
    rng: random.Random, archive: dict | None = None, day: int = 0,
) -> dict:
    """오프라인 결정론 폴백 — 기존 board_pool 문구를 대화 스키마로 조립.

    글 2~3개·글마다 댓글 0~3개 가변(리포트 ③), 스탠스는 컨텍스트+성향 규칙,
    agent_deltas는 규칙표(작성자 주축 ±4·댓글자 ±2), crowd_delta는 부호(T-250)
    × 뉴스 강도 스케일(⑪).

    T-e — archive(공개 트랙 박제)를 주면 글 작성자에게 지난 대화 기억/감정
    여운 접두(speech_flavor)를 붙인다. rng 소비 이후의 순수 텍스트 가공이라
    결정론·기존 호출(archive 미지정) 계약은 불변.
    """
    # 리뷰 수정 — 아카이브(공개 트랙) 생성은 클론 스탯과 완전 무관해야 한다:
    # 스탯이 rng 소비량을 바꾸면 첫 조회 시점(권유 전/후)에 따라 다른 대화가 박제됨.
    # 중립 스탯(빈 dict → 전부 50)으로 생성하고 클론 발언은 버린다(inject_clone 몫).
    _ = clone_stats
    base = _social.board_event(context, {}, rng, use_llm=False)
    majority = _CONTEXT_STANCE.get(context, "split")
    flip = {"up": "down", "down": "up"}.get(majority, "split")

    threads = []
    for post in base["posts"]:
        aid = post["author_id"]
        if aid == "clone":
            continue    # 클론은 inject_clone에서 회차별로
        stance = _stance_for(aid, majority, flip)
        comments = [{"author_id": c["author_id"],
                     "stance": _stance_for(c["author_id"], majority, flip),
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
                "stance": _stance_for(pid, majority, flip),
                "text": rng.choice(variants)})

    # T-e 기억 발화 — 글 작성자만(댓글 제외), 발화당 향미 최대 1개.
    if archive:
        from . import agent_state as _agent_state   # 지연 import(순환 차단)
        for th in threads:
            flavor = _agent_state.speech_flavor(th["author_id"], archive, day)
            if flavor:
                th["text"] = flavor + th["text"]

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
    # T-259 — 글+댓글 전체 발화 다수결(글만 세면 화면 인상과 어긋남).
    return {"verdict": verdict_from_speech(threads), "threads": threads,
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

출력(JSON만): {{"verdict": "up|down|split", "threads": [{{"author_id", "stance": "up|down|split", "text", "comments": [{{"author_id", "stance", "text"}}]}}], "agent_deltas": {{author_id: {{"fear|greed|confidence|excitement|trust": -8~8}}}}, "crowd_delta": -6~6 (음수=공포 심화, 양수=탐욕 과열)}}
threads는 2~4개, 글마다 comments 0~4개(개수를 다르게), 한국어 커뮤니티 말투."""
        raw = cli.chat(user=user, system="투자 커뮤니티 대화 시뮬레이터. JSON만 출력.",
                       temperature=0.8)
        conv = validate(extract_json(raw), context=context)
        if conv is None:
            return None
        # 리뷰 수정(council F2) — LLM이 지시를 어기고 클론을 등장시켜도 아카이브
        # (회차 불변 공개 트랙)에 박제되지 않게 strip. 클론은 inject_clone이 회차별로.
        conv["threads"] = [
            {**th, "comments": [c for c in th["comments"]
                                if c["author_id"] != "clone"]}
            for th in conv["threads"] if th["author_id"] != "clone"]
        conv["agent_deltas"].pop("clone", None)
        return conv if len(conv["threads"]) >= 2 else None
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
    clone_stance = flip if steady else majority
    # T-280(사용자 피드백) — 독백 금지: 답글 대상 글쓴이를 부르고, 스탠스가
    # 같으면 동조·다르면 반박 리드인을 본문(감정 반응) 앞에 붙인다.
    author_name = _NAME.get(target["author_id"], target["author_id"])
    kind = "agree" if target.get("stance") == clone_stance else "counter"
    leadins = pool.get("clone_leadin", {}).get(kind) or []
    lead = rng.choice(leadins).format(author=author_name) if leadins else ""
    target["comments"].append({
        "author_id": "clone",
        "stance": clone_stance,
        "text": f"{lead} {rng.choice(variants)}".strip()})
    return out
