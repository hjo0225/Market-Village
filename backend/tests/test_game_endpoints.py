"""T-201 · GameRun 엔드포인트 — 슬라이스를 API로 하루씩 플레이.

핸들러 직접 호출(RETRO 규칙5). 인터뷰(answers)→start→하루×30 advance→카드→
new_run→회차 compare 까지 e2e. news/crisis/정산 로직은 advance_day가 이미 처리하고
이 티켓은 그걸 노출한다.
"""

from __future__ import annotations

import market_live_server as mls

ANSWERS = {"q_panic": 1.0, "q_fomo": 0.0}


def _start(gid="ep_g", **kw):
    body = dict(game_id=gid, answers=ANSWERS, symbol="DOGE", start_price=100.0,
                start_stats={"급락패닉저항": 25, "멘탈마모저항": 50, "익절거부제어": 50,
                            "과대베팅제어": 50, "추격매수저항": 50, "막차불안저항": 50,
                            "멘탈회복": 50})
    body.update(kw)
    return mls.control_game_start(mls.GameStartBody(**body))


def test_start_returns_day0_state():
    r = _start("ep_start")
    assert r["status"] == "ok"
    assert r["state"]["day"] == 0 and r["state"]["finished"] is False


def test_start_with_allocations_seeds_diversified_portfolio():
    # T-215 D1 — "분산해서 시작" 토글 켠 경로. 최대 비중 카테고리가 주력.
    r = _start("ep_alloc",
               allocations={"large_stable": 50, "mid_alt": 20, "meme": 20, "stable": 10})
    assert r["status"] == "ok"
    holdings = {h["category"]: h for h in r["state"]["portfolio"]["holdings"]}
    assert set(holdings) == {"large_stable", "mid_alt", "meme", "stable"}
    assert r["state"]["category"] == "large_stable"          # 최대 비중 = 주력
    total_value = sum(h["value"] for h in holdings.values())
    assert abs(total_value - 100.0) < 1.0                     # 총자산 100 그대로 분배


def test_start_without_allocations_stays_single_asset():
    # 토글 꺼짐(기본) — 회귀 없음 확인.
    r = _start("ep_no_alloc")
    holdings = r["state"]["portfolio"]["holdings"]
    assert len(holdings) == 1
    assert holdings[0]["category"] == "meme"


def test_news_three_distinct_tones():
    _start("ep_news")
    r = mls.control_game_news(game_id="ep_news", seed=7)
    assert r["status"] == "ok" and len(r["news"]) == 3
    assert len({n["tone"] for n in r["news"]}) == 3


def test_advance_to_completion_yields_card():
    _start("ep_play")
    last = None
    for _ in range(30):
        last = mls.control_game_advance(mls.GameAdvanceBody(game_id="ep_play"))
    assert last["state"]["finished"] is True
    assert "card" in last and last["card"]["grade"] in {"고수", "벼락부자형", "강철멘탈형", "호구"}


def test_advance_with_news_and_strategy():
    _start("ep_adv")
    r = mls.control_game_advance(mls.GameAdvanceBody(
        game_id="ep_adv", news_id="fear_war", strategy="B_함정직시", rapport=100.0, roll=0.0))
    assert r["status"] == "ok" and r["state"]["day"] == 1


def test_newrun_resets_and_compare_diverges():
    _start("ep_cmp")
    # 1회차: 개입 없음 → day27 패닉 매도(실 업비트 DOGE −21.6%)
    for _ in range(30):
        mls.control_game_advance(mls.GameAdvanceBody(game_id="ep_cmp"))
    # 2회차: 같은 운명선 다시, day27 개입
    mls.control_game_newrun(mls.GameNewRunBody(game_id="ep_cmp", run_id="run2"))
    for d in range(30):
        if d == 27:
            mls.control_game_advance(mls.GameAdvanceBody(
                game_id="ep_cmp", strategy="B_함정직시", rapport=100.0, roll=0.0))
        else:
            mls.control_game_advance(mls.GameAdvanceBody(game_id="ep_cmp"))
    cmp = mls.control_game_compare(game_id="ep_cmp", run_a="run1", run_b="run2", day=27)
    assert cmp["status"] == "ok"
    assert cmp["a"]["swayed"] is True and cmp["b"]["swayed"] is False


def test_missing_game_errors():
    assert mls.control_game_state(game_id="nope")["status"] == "error"
    assert mls.control_game_advance(mls.GameAdvanceBody(game_id="nope"))["status"] == "error"


# --- T-265 · /day/advance 멱등성 키 (게이트 4c — QA 스윕 Day12 침묵 실패에서) --- #
# 프록시 플레이크로 응답만 유실된 재시도가 하루를 2번 진행시키면 안 되고(중복
# 적용), 키가 있으면 클라이언트 재시도가 안전해야 한다(캐시 응답 반환).

def test_advance_same_idem_key_applies_once():
    _start("ep_idem")
    a = mls.control_game_advance(mls.GameAdvanceBody(
        game_id="ep_idem", idem_key="k-day0"))
    assert a["status"] == "ok" and a["state"]["day"] == 1
    b = mls.control_game_advance(mls.GameAdvanceBody(
        game_id="ep_idem", idem_key="k-day0"))       # 재전송(응답 유실 시나리오)
    assert b == a                                     # 캐시 응답 그대로
    assert mls.control_game_state("ep_idem")["state"]["day"] == 1   # 이중 적용 없음


def test_advance_new_idem_key_advances():
    _start("ep_idem2")
    mls.control_game_advance(mls.GameAdvanceBody(game_id="ep_idem2", idem_key="k0"))
    r = mls.control_game_advance(mls.GameAdvanceBody(game_id="ep_idem2", idem_key="k1"))
    assert r["state"]["day"] == 2


def test_advance_without_key_keeps_legacy_behavior():
    _start("ep_idem3")
    mls.control_game_advance(mls.GameAdvanceBody(game_id="ep_idem3"))
    r = mls.control_game_advance(mls.GameAdvanceBody(game_id="ep_idem3"))
    assert r["state"]["day"] == 2                     # 키 없으면 매 호출 적용(기존)


def test_advance_concurrent_same_key_single_apply():
    # /review — 체크-후-쓰기 레이스: 같은 키 동시 2건이 둘 다 캐시 미스로 통과해
    # 하루가 2번 가면 안 된다(게임별 락으로 직렬화).
    import threading
    _start("ep_race")
    results = []
    body = mls.GameAdvanceBody(game_id="ep_race", idem_key="k-race")
    threads = [threading.Thread(target=lambda: results.append(
        mls.control_game_advance(body))) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert mls.control_game_state("ep_race")["state"]["day"] == 1   # 정확히 1일
    assert all(r == results[0] for r in results)                    # 전부 같은 응답
