"""T-223 · 게시판(SNS형 FGI) 콘텐츠 생성 엔진 — 부속 PRD(PRD_SOCIAL_NPC_BOARD) §3.2.

트리거(D2): 위기 발동 OR 고강도 뉴스. 콘텐츠(D8·D9): 관중 선정·템플릿은 규칙,
표현은 LLM opt-in(오프라인 기본). 클론도 게시(합리화 언어 재사용). 결정론:
같은 날 재호출 = 같은 결과(캐시), crowd_mood는 하루 1회만 이동.
"""

from __future__ import annotations

import random

import market_live_server as mls
from sim import clone_spec as CS
from sim import social
from sim.game_run import GameRun

CLONE = CS.build_clone_spec({"q_panic": 0.9})

_HIGH_FEAR = {"id": "n1", "tone": "fear", "intensity": "high"}
_HIGH_OPT = {"id": "n2", "tone": "optimism", "intensity": "high"}
_HIGH_UNC = {"id": "n3", "tone": "uncertain", "intensity": "high"}
_MED = {"id": "n4", "tone": "fear", "intensity": "medium"}


# --- 트리거 판정 (D2) ------------------------------------------------------ #
def test_trigger_none_on_calm_day_without_high_news():
    assert social.board_trigger(None, [_MED]) is None
    assert social.board_trigger(None, []) is None


def test_trigger_trap_maps_to_context():
    assert social.board_trigger("F1", []) == "fear"
    assert social.board_trigger("G2", [_MED]) == "greed"
    assert social.board_trigger("M1", []) == "fomo"


def test_trigger_high_news_opens_board_even_without_crisis():
    assert social.board_trigger(None, [_MED, _HIGH_FEAR]) == "fear"
    assert social.board_trigger(None, [_HIGH_OPT]) == "fomo"
    assert social.board_trigger(None, [_HIGH_UNC]) == "unrest"


def test_trigger_crisis_takes_precedence_over_news():
    assert social.board_trigger("G1", [_HIGH_FEAR]) == "greed"


# --- 피드 생성 (D8·D9) ----------------------------------------------------- #
def test_board_event_contract_and_determinism():
    a = social.board_event("fear", CLONE, trap="F1", rng=random.Random(7))
    b = social.board_event("fear", CLONE, trap="F1", rng=random.Random(7))
    assert a == b                                   # 같은 시드 = 같은 피드
    assert len(a["posts"]) >= 3                     # 관중 여럿 + 클론
    for p in a["posts"]:
        assert p["author"] and p["text"]
        assert p["author_kind"] in ("sns", "clone")
        assert isinstance(p["comments"], list)
    assert any(len(p["comments"]) > 0 for p in a["posts"])   # 댓글 상호작용
    assert a["crowd_mood_delta"] > 0                # 이벤트 날은 들끓는다


def test_board_event_clone_post_uses_rationalization_when_trapped():
    out = social.board_event("fear", CLONE, trap="F1", rng=random.Random(1))
    clone_posts = [p for p in out["posts"] if p["author_kind"] == "clone"]
    assert len(clone_posts) == 1
    assert clone_posts[0]["text"] in CLONE.rationalization["F1"]


def test_board_event_no_clone_post_without_trap():
    out = social.board_event("fear", CLONE, trap=None, rng=random.Random(1))
    assert all(p["author_kind"] != "clone" for p in out["posts"])


def test_board_event_offline_needs_no_llm():
    # 키/네트워크 없이도(기본 use_llm=False) 항상 동작 — 예외 없이 텍스트 생성.
    out = social.board_event("greed", CLONE, trap="G2", rng=random.Random(3))
    assert all(p["text"] for p in out["posts"])


def test_board_event_llm_optin_rewrites_via_fake(monkeypatch):
    # ⚠️ 실 키가 OS에 있어 진짜 LLMClient는 과금 호출 — FakeLLM로 격리(실호출 0).
    from sim import llm as llmmod
    fake = llmmod.FakeLLM(response="다듬어진 문장")
    monkeypatch.setattr(llmmod, "LLMClient", lambda *a, **kw: fake)
    out = social.board_event("fear", CLONE, trap="F1", rng=random.Random(5), use_llm=True)
    assert any(p["text"] == "다듬어진 문장" for p in out["posts"])


def test_board_event_llm_failure_falls_back_to_template(monkeypatch):
    from sim import llm as llmmod

    def _boom(*a, **kw):
        raise RuntimeError("no key")

    monkeypatch.setattr(llmmod, "LLMClient", _boom)
    out = social.board_event("fear", CLONE, trap="F1", rng=random.Random(5), use_llm=True)
    assert all(p["text"] for p in out["posts"])     # 폴백으로 항상 채워짐


# --- GameRun 배선 (D1·D3 + 캐시·직렬화) ------------------------------------ #
def _g(run_id="board_g"):
    return GameRun(CLONE, category="meme", start_price=100.0, run_id=run_id)


def test_board_today_closed_on_calm_day():
    g = _g()
    out = g.board_today([_MED])
    assert out["open"] is False and out["posts"] == []


def test_board_today_opens_on_high_news_and_caches_same_day():
    g = _g()
    mood0 = g.crowd_mood
    first = g.board_today([_HIGH_FEAR])
    assert first["open"] is True and len(first["posts"]) >= 3
    mood1 = g.crowd_mood
    assert mood1 > mood0                            # 들끓음 1회 반영
    second = g.board_today([_HIGH_FEAR])
    assert second == first                          # 같은 날 재호출 = 캐시
    assert g.crowd_mood == mood1                    # 두 번 안 오른다


def test_board_survives_serialization_without_reapplying_mood():
    g = _g()
    g.board_today([_HIGH_FEAR])
    mood = g.crowd_mood
    restored = GameRun.from_doc(g.to_doc())
    out = restored.board_today([_HIGH_FEAR])
    assert out["open"] is True
    assert restored.crowd_mood == mood              # 재생성·재적용 없음


# --- §9.3 폭주 방지 — crowd_mood 밤사이 회귀 (T-225 검증에서 발견한 결함) --- #
def test_crowd_mood_reverts_toward_neutral_overnight():
    # 게시판(+3.5/일)만 있고 감쇠가 없으면 crowd_mood가 단조 증가 →
    # M2(막차불안, crowd_mood 프록시 T-210b)가 영구 발동하는 폭주 고리.
    g = _g("mood_rev")
    g.crowd_mood = 90.0
    g.advance_day()
    assert g.crowd_mood < 90.0                    # 밤사이 중립으로 일부 회귀


def test_daily_boards_do_not_push_crowd_mood_past_m2_threshold():
    from sim import tuning as T
    g = _g("mood_loop")
    for _ in range(15):
        g.board_today([_HIGH_FEAR])               # 매일 게시판이 열리는 최악 케이스
        g.advance_day()
        assert g.crowd_mood < T.M2_FGI, g.day     # 평형이 임계(75) 아래 유지
def test_board_endpoint_deterministic_same_day():
    mls.control_game_start(mls.GameStartBody(
        game_id="board_ep", answers={}, symbol="DOGE", start_price=100.0))
    a = mls.control_game_board(game_id="board_ep")
    b = mls.control_game_board(game_id="board_ep")
    assert a["status"] == "ok" and "open" in a
    assert a == b


def test_board_endpoint_missing_game():
    assert mls.control_game_board(game_id="nope")["status"] == "error"


# --- 뉴스 시드 파생 (동일 티켓 내 결함 수정 — 매일 같은 3개 버그) ----------- #
def test_news_endpoint_derives_seed_per_day():
    mls.control_game_start(mls.GameStartBody(
        game_id="news_seed", answers={}, symbol="DOGE", start_price=100.0))
    d0a = mls.control_game_news(game_id="news_seed")
    d0b = mls.control_game_news(game_id="news_seed")
    assert [n["id"] for n in d0a["news"]] == [n["id"] for n in d0b["news"]]  # 같은 날 안정
    mls.control_game_advance(mls.GameAdvanceBody(game_id="news_seed"))
    d1 = mls.control_game_news(game_id="news_seed")
    assert [n["id"] for n in d1["news"]] != [n["id"] for n in d0a["news"]]   # 날이 바뀌면 달라짐


def test_news_endpoint_explicit_seed_still_works():
    mls.control_game_start(mls.GameStartBody(
        game_id="news_seed2", answers={}, symbol="DOGE", start_price=100.0))
    a = mls.control_game_news(game_id="news_seed2", seed=7)
    b = mls.control_game_news(game_id="news_seed2", seed=7)
    assert [n["id"] for n in a["news"]] == [n["id"] for n in b["news"]]
