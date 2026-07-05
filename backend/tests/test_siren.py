"""T-271 · 긴급 속보 사이렌 — 유저 트리거 외란(심리 전용, 가격·운명선 불가침).

🤖 council(2026-07-05): 효과는 심리에만(악재=급락패닉저항·crowd −5 / 호재=추격매수
저항 −5·crowd +5 / 넘어가기=효과 0의 진짜 절제), 발생은 game_id 시드 결정론
15%/일(회차 무관 — §13.6 거울 성립), 멱등성은 "그날의 사이렌 1개" 싱글턴(4c ①),
동시성은 기존 _advance_lock 재사용(4c ②). 새 누적 게이지 없음(4b 비해당).
"""

from __future__ import annotations

import threading

import pytest

import market_live_server as mls
from sim import clone_spec as CS
from sim import tuning as T
from sim.clone_stats import F1_RES, M1_RES
from sim.game_run import GameRun

CLONE = CS.build_clone_spec({"q_panic": 0.5})


def _g(run_id="siren"):
    return GameRun(CLONE, category="meme", start_price=100.0, run_id=run_id)


def _siren_gid(active: bool, day: int = 0) -> str:
    """day에 사이렌이 (안) 뜨는 game_id를 결정론적으로 찾는다."""
    return next(f"sg{i}" for i in range(500)
                if mls._siren_today(f"sg{i}", day) is active)


def test_siren_schedule_deterministic_and_sane():
    a = [mls._siren_today("gid1", d) for d in range(30)]
    b = [mls._siren_today("gid1", d) for d in range(30)]
    assert a == b                                   # 같은 입력 → 같은 판정
    counts = [sum(mls._siren_today(f"g{i}", d) for d in range(30)) for i in range(20)]
    assert all(0 <= c <= 12 for c in counts)        # 15%/일 새니티(기대 4.5회)
    assert sum(counts) > 0


def test_siren_bad_applies_stat_and_crowd():
    g = _g()
    s0, c0 = g.stats[F1_RES], g.crowd_mood
    eff = g.siren_choice(0, "bad")
    assert eff["applied"] is True
    assert g.stats[F1_RES] == s0 + T.SIREN_STAT_DELTA     # −5
    assert g.crowd_mood == c0 - T.SIREN_CROWD_DELTA       # 공포 방향


def test_siren_good_hits_fomo_axis():
    g = _g()
    s0, c0 = g.stats[M1_RES], g.crowd_mood
    g.siren_choice(0, "good")
    assert g.stats[M1_RES] == s0 + T.SIREN_STAT_DELTA
    assert g.crowd_mood == c0 + T.SIREN_CROWD_DELTA       # 탐욕 방향


def test_siren_duplicate_no_double_apply():
    g = _g()
    g.siren_choice(0, "bad")
    s1, c1 = g.stats[F1_RES], g.crowd_mood
    eff = g.siren_choice(0, "good")                        # 재선택 시도
    assert eff["applied"] is False and eff["duplicate"] is True
    assert eff["kind"] == "bad"                            # 기록된 원 선택 반환
    assert g.stats[F1_RES] == s1 and g.crowd_mood == c1    # 불변


def test_siren_skip_consumes_without_effect():
    g = _g()
    s0, c0 = dict(g.stats), g.crowd_mood
    g.siren_choice(0, "skip")
    assert g.stats == s0 and g.crowd_mood == c0            # 절제 = 효과 0
    assert g.siren_choice(0, "bad")["applied"] is False    # 하지만 소비됨


def test_siren_stale_day_rejected():
    g = _g()
    g.advance_day()
    with pytest.raises(ValueError):
        g.siren_choice(0, "bad")                           # 지난 날 늦은 POST


def test_siren_log_roundtrip():
    g = _g()
    g.siren_choice(0, "skip")
    g2 = GameRun.from_doc(g.to_doc(), fate_line=g.fl)
    assert g2.siren_choice(0, "bad")["applied"] is False   # 재시작에도 중복 차단


def test_siren_endpoint_flow():
    gid = _siren_gid(active=True)
    mls.control_game_start(mls.GameStartBody(
        game_id=gid, answers={}, symbol="DOGE", start_price=100.0))
    r = mls.control_game_siren(game_id=gid)
    assert r["status"] == "ok" and r["active"] is True and r["used"] is False
    r2 = mls.control_game_siren_choose(mls.GameSirenBody(game_id=gid, day=0, choice="good"))
    assert r2["status"] == "ok" and r2["applied"] is True
    r3 = mls.control_game_siren_choose(mls.GameSirenBody(game_id=gid, day=0, choice="good"))
    assert r3["status"] == "ok" and r3["applied"] is False  # 자연 멱등
    assert mls.control_game_siren(game_id=gid)["used"] is True


def test_siren_non_siren_day_rejected():
    gid = _siren_gid(active=False)
    mls.control_game_start(mls.GameStartBody(
        game_id=gid, answers={}, symbol="DOGE", start_price=100.0))
    r = mls.control_game_siren_choose(mls.GameSirenBody(game_id=gid, day=0, choice="bad"))
    assert r["status"] == "error"


def test_siren_concurrent_posts_apply_once():
    gid = _siren_gid(active=True) + "_race"
    while not mls._siren_today(gid, 0):
        gid += "x"
    mls.control_game_start(mls.GameStartBody(
        game_id=gid, answers={}, symbol="DOGE", start_price=100.0))
    g = mls._get_game(gid)
    s0 = g.stats[F1_RES]
    results = []
    def post():
        results.append(mls.control_game_siren_choose(
            mls.GameSirenBody(game_id=gid, day=0, choice="bad")))
    ts = [threading.Thread(target=post) for _ in range(4)]
    for t in ts: t.start()
    for t in ts: t.join()
    assert sum(1 for r in results if r.get("applied")) == 1  # 정확히 1회 적용
    assert g.stats[F1_RES] == s0 + T.SIREN_STAT_DELTA
