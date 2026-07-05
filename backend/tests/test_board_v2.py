"""T-251~254 · 게시판 v2 — 대화 스키마·아카이브 박제·LLM 1콜·파생 감정/기억.

플레이테스트 리포트 ③(대화를 게시글+댓글로 분할, 댓글 수 가변, 클론은 참여자)
⑥(에이전트별 감정 변화·이전 FGI 기억) ⑩(뉴스에 대한 가격 논의) ⑪(델타 가변) 봉인.
"""

from __future__ import annotations

import random

from sim import agent_state, board_v2, personas
from sim import clone_spec as CS
from sim.game_run import GameRun
from sim.llm import FakeLLM

CLONE = CS.build_clone_spec({"q_panic": 0.5})
_HIGH_FEAR = {"id": "n_reg", "headline": "규제 전격 발표", "tone": "fear",
              "intensity": "high"}
_EXTREME = {"id": "n_x", "headline": "거래소 파산", "tone": "fear",
            "intensity": "extreme"}


def _conv(news=(_HIGH_FEAR,), seed=7):
    return board_v2.offline_conversation(
        "fear", {"급락패닉저항": 30.0}, list(news), random.Random(seed))


# --- T-251 스키마·오프라인 어댑터 ---------------------------------------- #

def test_offline_conversation_schema_and_determinism():
    a, b = _conv(), _conv()
    assert a == b                                    # 같은 rng = 같은 대화
    assert a["verdict"] in ("up", "down", "split")
    assert len(a["threads"]) >= 2                    # 게시글 2개 이상
    for th in a["threads"]:
        assert th["author_id"] != "clone"            # 아카이브에 클론 없음(F2)
        assert th["stance"] in ("up", "down", "split")


def test_comment_counts_vary_across_threads():
    # 리포트 ③ — "댓글 없는 게시물도 있고 있어도 1개" 금지: 글마다 개수가 달라야.
    counts = set()
    for seed in range(12):
        counts |= {len(th["comments"]) for th in _conv(seed=seed)["threads"]}
    assert len(counts) >= 3                          # 0·1·2·3개가 섞여 나온다


def test_crowd_delta_scales_with_intensity():
    # 리포트 ⑪ — 델타가 이벤트 급에 따라 다르다(고정 +3.5 금지).
    high = _conv(news=(_HIGH_FEAR,))["crowd_delta"]
    extreme = _conv(news=(_EXTREME,))["crowd_delta"]
    assert abs(extreme) > abs(high)
    assert high < 0                                  # fear는 공포 방향(T-250)


def test_inject_clone_participates_as_comment():
    conv = _conv()
    out = board_v2.inject_clone(conv, "fear", {"급락패닉저항": 30.0},
                                random.Random(1))
    clone_comments = [c for th in out["threads"] for c in th["comments"]
                      if c["author_id"] == "clone"]
    assert len(clone_comments) == 1                  # 혼잣말 게시글이 아니라 답글
    assert all(th["author_id"] != "clone" for th in out["threads"])
    assert conv != out and all(
        c["author_id"] != "clone"
        for th in conv["threads"] for c in th["comments"])   # 원본(아카이브) 불변


# --- T-280 클론 답글은 반응형(독백 금지) — 사용자 피드백(2026-07-05) ---------- #
# "다른 사람들 의견에 대한 자신의 의견처럼": 답글 대상 글쓴이 이름을 부르고,
# 스탠스가 같으면 동조·다르면 반박 리드인으로 시작한다.

def _clone_comment(out):
    for th in out["threads"]:
        for c in th["comments"]:
            if c["author_id"] == "clone":
                return th, c
    raise AssertionError("clone comment missing")


def _leadins(kind: str, author: str) -> list[str]:
    pool = board_v2._social._load_board_pool(str(board_v2._social.BOARD_POOL_PATH))
    return [t.format(author=author) for t in pool["clone_leadin"][kind]]


def test_clone_comment_references_thread_author():
    out = board_v2.inject_clone(_conv(), "fear", {"급락패닉저항": 30.0},
                                random.Random(1))
    th, c = _clone_comment(out)
    name = board_v2._NAME.get(th["author_id"], th["author_id"])
    assert name in c["text"]                         # 그 글쓴이에 대한 반응


def test_clone_leadin_agree_or_counter_matches_stance():
    # steady(반대 스탠스)·shaken(다수 추종) 양쪽에서, 대상 글과 스탠스가 같으면
    # 동조 리드인·다르면 반박 리드인으로 시작해야 한다.
    for stats in ({"급락패닉저항": 80.0}, {"급락패닉저항": 30.0}):
        for seed in range(6):
            out = board_v2.inject_clone(_conv(), "fear", stats,
                                        random.Random(seed))
            th, c = _clone_comment(out)
            name = board_v2._NAME.get(th["author_id"], th["author_id"])
            kind = "agree" if th["stance"] == c["stance"] else "counter"
            assert any(c["text"].startswith(l) for l in _leadins(kind, name)), \
                f"{kind} 리드인 아님: {c['text']!r}"


def test_clone_reactive_comment_deterministic():
    a = board_v2.inject_clone(_conv(), "fear", {"급락패닉저항": 30.0},
                              random.Random(5))
    b = board_v2.inject_clone(_conv(), "fear", {"급락패닉저항": 30.0},
                              random.Random(5))
    assert a == b


def test_validate_drops_foreign_authors_and_clamps():
    conv = {"verdict": "up", "threads": [
        {"author_id": "hacker", "stance": "up", "text": "x", "comments": []},
        {"author_id": "doomposter", "stance": "down", "text": "a", "comments": [
            {"author_id": "npc_zzz", "stance": "up", "text": "y"}]},
        {"author_id": "newbie", "stance": "down", "text": "b", "comments": []},
    ], "agent_deltas": {"doomposter": {"fear": 99.0}, "hacker": {"fear": 5}},
        "crowd_delta": -55.0}
    out = board_v2.validate(conv)
    ids = {th["author_id"] for th in out["threads"]}
    assert ids == {"doomposter", "newbie"}           # 화이트리스트 밖 drop
    assert out["threads"][0]["comments"] == []
    assert out["agent_deltas"] == {"doomposter": {"fear": 8.0}}   # ±8 클램프
    assert out["crowd_delta"] == -6.0                # ±6 클램프(T-250)


def test_validate_rejects_thin_conversation():
    assert board_v2.validate({"threads": []}) is None
    assert board_v2.validate(None) is None


# --- T-259 여론 정합 — verdict는 노출 발화(글+댓글) 전체 다수결 ------------- #
# 사용자 리포트(2026-07-03): 댓글엔 "오른다"가 많은데 여론 라벨은 "내린다 우세".
# 원인: verdict가 글 스탠스만 집계 — 화면 인상(댓글 포함)과 어긋남.

def _visible_majority(conv):
    votes = [th["stance"] for th in conv["threads"]]
    votes += [c["stance"] for th in conv["threads"] for c in th.get("comments", [])]
    ups, downs = votes.count("up"), votes.count("down")
    return "up" if ups > downs else "down" if downs > ups else "split"


def test_verdict_matches_visible_speech_majority_offline():
    for ctx in ("fear", "greed", "fomo", "unrest"):
        for seed in range(8):
            conv = board_v2.offline_conversation(
                ctx, {}, [_HIGH_FEAR], random.Random(seed))
            assert conv["verdict"] == _visible_majority(conv), (ctx, seed)


def test_validate_recomputes_verdict_from_speech():
    # LLM이 verdict를 뭐라 주장하든, 노출 발화 다수결로 정정한다.
    conv = {"verdict": "up", "threads": [
        {"author_id": "doomposter", "stance": "down", "text": "a", "comments": [
            {"author_id": "newbie", "stance": "down", "text": "y"}]},
        {"author_id": "newbie", "stance": "up", "text": "b", "comments": []},
    ], "agent_deltas": {}, "crowd_delta": -1.0}
    out = board_v2.validate(conv)
    assert out["verdict"] == "down"


# --- T-252 아카이브 박제(회차 불변·재시작 안전) --------------------------- #

def _g(**kw):
    return GameRun(CLONE, category="meme", start_price=100.0, run_id="bv2", **kw)


def test_archive_reused_across_runs_same_day_same_news():
    g = _g()
    first = g.board_today([_HIGH_FEAR])
    assert first["open"] is True
    archived = dict(g.board_archive)
    g.new_run("run2")
    second = g.board_today([_HIGH_FEAR])
    assert g.board_archive == archived               # 회차가 바뀌어도 대화는 박제 그대로
    # 관중 대화(공개 트랙)는 동일 — 클론 발언만 회차 상태에 따라 달라질 수 있다.
    strip = lambda feed: [
        {**p, "comments": [c for c in p["comments"] if c["author_id"] != "clone"]}
        for p in feed["posts"] if p["author_id"] != "clone"]
    assert strip(first) == strip(second)


def test_archive_survives_serialization_roundtrip():
    g = _g()
    g.board_today([_HIGH_FEAR])
    doc = g.to_doc()
    g2 = GameRun.from_doc(doc, fate_line=g.fl)
    assert g2.board_archive == g.board_archive
    assert GameRun.from_doc({k: v for k, v in doc.items() if k != "archive"},
                            fate_line=g.fl).board_archive == {}   # 구 문서 하위호환


# --- T-253 LLM 1콜(FakeLLM) — 성공 시 사용, 실패 시 폴백 동치 -------------- #

_LLM_JSON = ('{"verdict": "down", "threads": ['
             '{"author_id": "doomposter", "stance": "down", "text": "규제면 끝났다",'
             ' "comments": [{"author_id": "cheerleader", "stance": "up",'
             ' "text": "눌림목"}]},'
             '{"author_id": "chart_zealot", "stance": "up", "text": "RSI 과매도",'
             ' "comments": []}],'
             '"agent_deltas": {"doomposter": {"fear": 6}}, "crowd_delta": -5}')


def test_llm_conversation_used_when_valid():
    fake = FakeLLM(handler=lambda user, system: _LLM_JSON)
    conv = board_v2.llm_conversation("fear", [_HIGH_FEAR], -9.0, {}, client=fake)
    # T-259 — LLM은 verdict를 "down"이라 주장하지만 노출 발화는 up 2:down 1 →
    # validate가 다수결로 정정한다(여론 라벨-화면 정합 계약).
    assert conv is not None and conv["verdict"] == "up"
    assert conv["crowd_delta"] == -5.0
    assert {th["author_id"] for th in conv["threads"]} == {"doomposter", "chart_zealot"}


def test_llm_failure_falls_back_to_none():
    fake = FakeLLM(handler=lambda user, system: "죄송해요 JSON이 아니에요")
    assert board_v2.llm_conversation("fear", [_HIGH_FEAR], -9.0, {},
                                     client=fake) is None


def test_llm_prompt_discusses_price_direction_of_news():
    # 리포트 ⑩ — 프롬프트가 "이 사건으로 가격이 오를까 내릴까"를 명시.
    seen = {}
    def handler(user, system):
        seen["user"] = user
        return _LLM_JSON
    board_v2.llm_conversation("fear", [_HIGH_FEAR], -9.0, {},
                              client=FakeLLM(handler=handler))
    assert "가격이 오를까 내릴까" in seen["user"]
    assert _HIGH_FEAR["headline"] in seen["user"]


# --- T-254 파생 감정·기억(아카이브 fold) ---------------------------------- #

def test_agent_emotions_move_and_decay():
    conv = _conv()
    aid = conv["threads"][0]["author_id"]
    axis, delta = next(iter(conv["agent_deltas"][aid].items()))
    baseline = next(float(p[axis]) for p in personas.SNS_PERSONAS if p["id"] == aid)
    archive = {"0:n_reg": conv}
    day0 = agent_state.agent_emotions(aid, archive, 0)
    moved = day0[axis] - baseline
    assert moved != 0                                 # 이벤트가 감정을 움직인다
    day5 = agent_state.agent_emotions(aid, archive, 5)
    assert abs(day5[axis] - baseline) < abs(moved)    # 감쇠로 baseline 회귀(R6)
    assert abs(day0[axis] - baseline) <= agent_state.BAND   # 밴드 클램프


def test_memory_digest_recalls_past_stances():
    conv = _conv()
    archive = {"0:n_reg": conv}
    digests = agent_state.memory_digests(archive, upto_day=3)
    aid = conv["threads"][0]["author_id"]
    assert aid in digests and "전망" in digests[aid]
    assert agent_state.memory_digests(archive, upto_day=0) == {}   # 미래 누설 없음
