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


# --- 트리거 판정 (D2 개정 — 공개 이벤트만: 시장 급변동 or 고강도 뉴스) ------ #
def test_trigger_none_on_calm_day():
    assert social.board_trigger(0.0, [_MED]) is None
    assert social.board_trigger(3.0, []) is None


def test_trigger_market_crash_and_surge():
    assert social.board_trigger(-12.0, []) == "fear"
    assert social.board_trigger(15.0, [_MED]) == "fomo"


def test_trigger_high_news_opens_board():
    assert social.board_trigger(0.0, [_MED, _HIGH_FEAR]) == "fear"
    assert social.board_trigger(0.0, [_HIGH_OPT]) == "fomo"
    assert social.board_trigger(0.0, [_HIGH_UNC]) == "unrest"


def test_trigger_market_move_takes_precedence_over_news():
    assert social.board_trigger(-12.0, [_HIGH_OPT]) == "fear"


def test_trigger_never_sees_clone_traps():
    # D2 개정 핵심 — 시그니처에 함정이 아예 없다(위기 누설 구조적 차단).
    import inspect
    params = list(inspect.signature(social.board_trigger).parameters)
    assert "trap" not in params


# --- 피드 생성 (D8·D9 개정) ------------------------------------------------- #
_SHAKEN_STATS = {"급락패닉저항": 20.0, "추격매수저항": 20.0,
                 "과대베팅제어": 20.0, "멘탈마모저항": 20.0}
_STEADY_STATS = {"급락패닉저항": 80.0, "추격매수저항": 80.0,
                 "과대베팅제어": 80.0, "멘탈마모저항": 80.0}


def test_board_event_contract_and_determinism():
    a = social.board_event("fear", _SHAKEN_STATS, rng=random.Random(7))
    b = social.board_event("fear", _SHAKEN_STATS, rng=random.Random(7))
    assert a == b                                   # 같은 시드 = 같은 피드
    assert len(a["posts"]) >= 3                     # 관중 여럿 + 클론
    for p in a["posts"]:
        assert p["author"] and p["text"]
        assert p["author_kind"] in ("sns", "clone")
        assert isinstance(p["comments"], list)
    assert any(len(p["comments"]) > 0 for p in a["posts"])   # 댓글 상호작용
    # T-250 — 델타는 부호를 갖는다(FGI 의미론): fear/unrest는 공포로(-),
    # greed/fomo는 과열로(+). 0이면 게시판이 군중에 아무 흔적도 못 남긴 것.
    assert a["crowd_mood_delta"] != 0
    _SIGN = {"fear": -1, "unrest": -1, "greed": 1, "fomo": 1}
    assert a["crowd_mood_delta"] * _SIGN[a["context"]] > 0


def test_board_event_clone_reacts_by_relevant_stat():
    # D9 개정 — 클론은 매 게시판 참여, 문구는 이벤트 반응(관련 스탯 낮음=동요/높음=침착).
    pool = social._load_board_pool(str(social.BOARD_POOL_PATH))
    shaken = social.board_event("fear", _SHAKEN_STATS, rng=random.Random(1))
    steady = social.board_event("fear", _STEADY_STATS, rng=random.Random(1))
    sh_post = next(p for p in shaken["posts"] if p["author_kind"] == "clone")
    st_post = next(p for p in steady["posts"] if p["author_kind"] == "clone")
    assert sh_post["text"] in pool["clone"]["fear"]["shaken"]
    assert st_post["text"] in pool["clone"]["fear"]["steady"]


def test_board_event_clone_participates_in_every_context():
    for ctx in ("fear", "greed", "fomo", "unrest"):
        out = social.board_event(ctx, _STEADY_STATS, rng=random.Random(2))
        assert any(p["author_kind"] == "clone" for p in out["posts"]), ctx


def test_board_event_offline_needs_no_llm():
    # 키/네트워크 없이도(기본 use_llm=False) 항상 동작 — 예외 없이 텍스트 생성.
    out = social.board_event("greed", _STEADY_STATS, rng=random.Random(3))
    assert all(p["text"] for p in out["posts"])


def test_board_event_llm_optin_rewrites_via_fake(monkeypatch):
    # ⚠️ 실 키가 OS에 있어 진짜 LLMClient는 과금 호출 — FakeLLM로 격리(실호출 0).
    from sim import llm as llmmod
    fake = llmmod.FakeLLM(response="다듬어진 문장")
    monkeypatch.setattr(llmmod, "LLMClient", lambda *a, **kw: fake)
    out = social.board_event("fear", _SHAKEN_STATS, rng=random.Random(5), use_llm=True)
    assert any(p["text"] == "다듬어진 문장" for p in out["posts"])


def test_board_event_llm_failure_falls_back_to_template(monkeypatch):
    from sim import llm as llmmod

    def _boom(*a, **kw):
        raise RuntimeError("no key")

    monkeypatch.setattr(llmmod, "LLMClient", _boom)
    out = social.board_event("fear", _SHAKEN_STATS, rng=random.Random(5), use_llm=True)
    assert all(p["text"] for p in out["posts"])     # 폴백으로 항상 채워짐


# --- GameRun 배선 (D1·D3 + 캐시·직렬화) ------------------------------------ #
def _g(run_id="board_g"):
    return GameRun(CLONE, category="meme", start_price=100.0, run_id=run_id)


def test_board_today_closed_on_calm_day():
    # 조용한 날(비첫날)은 닫힘 — day0은 T-257 강제 오픈이라 day1로 검증.
    g = _g()
    g.advance_day()
    out = g.board_today([_MED])
    assert out["open"] is False and out["posts"] == []


def test_board_today_opens_on_market_crash_without_news():
    # D2 개정 — 뉴스가 조용해도 시장이 급락하면 마을이 수군댄다(가짜 운명선).
    from sim.fate_line import FateLine
    fl = FateLine({"days": 3, "categories": {"meme": {
        "ohlc": [[100, 100, 100, 100], [100, 100, 60, 70], [70, 70, 70, 70]]}}})
    g = GameRun(CLONE, category="meme", start_price=100.0, run_id="crashday",
                fate_line=fl, other_categories=())
    g.advance_day()                                  # day0 → day1 (전일비 -30%)
    out = g.board_today([_MED])
    assert out["open"] is True and out["context"] == "fear"


def test_board_today_is_pure_observation_and_caches_same_day():
    # D11(/review 수정) — 관찰 GET은 crowd_mood를 변이하지 않는다(레이스·이중적용·
    # 네트워크 유실 차단). 여파는 advance_day 밤 정산에서 1회.
    g = _g()
    mood0 = g.crowd_mood
    first = g.board_today([_HIGH_FEAR])
    assert first["open"] is True and len(first["posts"]) >= 3
    assert g.crowd_mood == mood0                    # 관찰은 무변이
    second = g.board_today([_HIGH_FEAR])
    assert second == first                          # 같은 날 재호출 = 캐시
    g.advance_day()
    mood_after = g.crowd_mood
    # T-250 — 밤 정산에서 델타가 그 부호 방향으로 반영된다(회귀 포함).
    delta = first["crowd_mood_delta"]
    assert (mood_after - mood0) * delta > 0 or delta == 0
    g.advance_day()                                 # 다음 날 게시판 없이 진행
    # 재적용 없음 — 중립(50)으로 감쇠만(부호 무관: 편차 절대값이 줄어든다).
    assert abs(g.crowd_mood - 50.0) < abs(mood_after - 50.0)


# --- T-260 매매 에이전트도 게시판에서 발화한다 ------------------------------- #
# 사용자 리포트(2026-07-03): 마을에 사는 매매 에이전트 8종이 게시판에 안 나타남
# — 마을 구성원이면 이벤트 수다에 참여해야 한다(댓글 캐스트 합류).

def test_trader_agents_appear_in_board_comments():
    from sim import personas
    trader_ids = {p["id"] for p in personas.TRADER_PERSONAS}
    for ctx in ("fear", "greed", "fomo", "unrest"):
        seen = set()
        for seed in range(30):
            out = social.board_event(ctx, _STEADY_STATS, rng=random.Random(seed))
            for p in out["posts"]:
                seen |= {c["author_id"] for c in p["comments"]}
        assert seen & trader_ids, f"{ctx}: 매매 에이전트 댓글 0 (30시드)"


def test_trader_comment_authors_have_real_names():
    # 이름 테이블 미통합이면 KeyError나 id 노출 — 사람 이름으로 렌더돼야 한다.
    from sim import personas
    trader_ids = {p["id"] for p in personas.TRADER_PERSONAS}
    trader_names = {p["name"] for p in personas.TRADER_PERSONAS}
    found = False
    for ctx in ("fear", "greed", "fomo", "unrest"):
        for seed in range(30):
            out = social.board_event(ctx, _STEADY_STATS, rng=random.Random(seed))
            for p in out["posts"]:
                for c in p["comments"]:
                    if c["author_id"] in trader_ids:
                        assert c["author"] in trader_names
                        found = True
    assert found


# --- T-257 첫인상 보장 + 발견성 --------------------------------------------- #
def test_board_day0_always_opens_even_without_trigger():
    # 사용자 리포트 3차(2026-07-03) — 첫 세션에서 게시판을 못 보면 "없는 기능"이
    # 된다. 플레이어가 실제로 처음 플레이하는 날은 day 0(/review 정정 — day 1로
    # 걸면 보장이 두 번째 날에 발동): day 0은 트리거 무관 강제 오픈.
    g = _g("first_day")
    out = g.board_today([_MED])                     # medium 뉴스뿐, 시장도 잠잠
    assert out["open"] is True
    assert out["context"] == "fear"                 # _MED의 톤(fear)로 수다


def test_board_day0_forced_context_falls_back_to_unrest():
    g = _g("first_day2")
    out = g.board_today([])
    assert out["open"] is True and out["context"] == "unrest"


def test_board_day1_respects_trigger():
    # 강제 오픈은 첫날(day 0)만 — 이후 조용한 날은 닫힘(트리거 계약 유지).
    g = _g("day1_calm")
    g.advance_day()                                 # day0 → day1
    assert g.board_today([_MED])["open"] is False


def test_board_closed_day_carries_recent_archive():
    # 닫힌 날 핸드폰 게시판 탭용 — 가장 최근 박제 대화를 읽기 전용으로 제공.
    g = _g("recent_arch")
    first = g.board_today([_HIGH_FEAR])             # day0 열림 → 아카이브 박제
    assert first["open"] is True
    g.advance_day()                                 # day1 (조용하면 닫힘)
    out = g.board_today([_MED])
    assert out["open"] is False
    assert out["recent"]["day"] == 0
    assert out["recent"]["posts"]                   # 지난 수다가 보인다
    assert all(p["author_kind"] == "sns" for p in out["recent"]["posts"])  # 클론 미주입(공개 트랙)


def test_board_today_verdict_matches_rendered_posts():
    # T-259 — 여론 라벨은 클론 주입 댓글까지 포함한 "화면 그대로"의 다수결.
    for run_id in ("vv1", "vv2", "vv3"):
        g = _g(run_id)
        out = g.board_today([_HIGH_FEAR])
        votes = [p.get("stance") for p in out["posts"]]
        votes += [c.get("stance") for p in out["posts"] for c in p["comments"]]
        ups, downs = votes.count("up"), votes.count("down")
        expect = "up" if ups > downs else "down" if downs > ups else "split"
        assert out["verdict"] == expect, run_id


def test_board_closed_day_recent_is_none_without_history():
    g = _g("no_hist")
    g.advance_day()                                 # day0 게시판 미조회 → 아카이브 없음
    out = g.board_today([_MED])                     # day1 조용한 날 → 닫힘
    assert out["open"] is False and out["recent"] is None


def test_board_survives_serialization_without_reapplying_mood():
    g = _g()
    g.board_today([_HIGH_FEAR])
    g.advance_day()                                 # 여파 반영 + mood_applied 기록
    mood = g.crowd_mood
    restored = GameRun.from_doc(g.to_doc())
    assert restored.crowd_mood == mood
    assert restored._board.get("mood_applied") is True   # 재적용 안 됨(직렬화 보존)


# --- §9.3 폭주 방지 — crowd_mood 밤사이 회귀 (T-225 검증에서 발견한 결함) --- #
def test_crowd_mood_reverts_toward_neutral_overnight():
    # 게시판(+3.5/일)만 있고 감쇠가 없으면 crowd_mood가 단조 증가 →
    # M2(막차불안, crowd_mood 프록시 T-210b)가 영구 발동하는 폭주 고리.
    g = _g("mood_rev")
    g.crowd_mood = 90.0
    g.advance_day()
    assert g.crowd_mood < 90.0                    # 밤사이 중립으로 일부 회귀


def test_daily_boards_do_not_push_crowd_mood_past_m2_threshold():
    # M2는 "그날 스텝이 읽는 값"(advance 직전 crowd_mood)으로 판정 — 그 값을 검사
    # (/review 지적: 야간 회귀 후 값만 재면 낮에 임계를 넘어도 통과해버린다).
    from sim import tuning as T
    g = _g("mood_loop")
    for _ in range(15):
        g.board_today([_HIGH_FEAR])               # 매일 게시판이 열리는 최악 케이스
        assert g.crowd_mood < T.M2_FGI, g.day     # M2가 읽는 낮 값이 임계 아래
        g.advance_day()
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


def test_crowd_mood_equilibrium_stays_below_m2():
    """T-250(R8/4b) — 최악 지속(+클램프 상한 매일)에도 평형이 M2 임계 아래.

    M2는 평형으로는 상시 발동 불가 — 탐욕 이벤트 연속일에만 일시 돌파(의도).
    """
    from sim import tuning as T
    mood = 50.0
    for _ in range(60):
        mood = T.clamp(mood + T.CROWD_DELTA_CLAMP, 0.0, 100.0)
        mood = 50.0 + (mood - 50.0) * (1.0 - T.CROWD_MOOD_REVERT)
    assert mood < T.M2_FGI
