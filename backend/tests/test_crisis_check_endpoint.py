import market_live_server as mls


def _advance_to_crisis_day(gid, n=21):
    mls.control_game_start(mls.GameStartBody(
        game_id=gid, answers={"q_panic": 1.0, "q_fomo": 1.0}, symbol="DOGE"))
    for _ in range(n):
        mls.control_game_advance(mls.GameAdvanceBody(game_id=gid))


def test_crisis_check_no_trap_on_calm_day():
    gid = "cc_calm"
    mls.control_game_start(mls.GameStartBody(game_id=gid, answers={}, symbol="DOGE"))
    r = mls.control_game_crisis_check(game_id=gid)
    assert r["status"] == "ok"
    assert r["trap"] is None


def test_crisis_check_reports_trap_without_advancing_day():
    gid = "cc_trap"
    _advance_to_crisis_day(gid)
    before_day = mls.control_game_state(game_id=gid)["state"]["day"]
    r = mls.control_game_crisis_check(game_id=gid)
    assert r["status"] == "ok"
    assert r["trap"] == "G1"
    assert r["trap_name"] == "익절 거부"
    after_day = mls.control_game_state(game_id=gid)["state"]["day"]
    assert before_day == after_day   # 부작용 없음 — day 안 늘어남


def test_crisis_check_missing_game():
    assert mls.control_game_crisis_check(game_id="nope")["status"] == "error"
