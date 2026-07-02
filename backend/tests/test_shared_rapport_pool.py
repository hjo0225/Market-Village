"""사용자 피드백(2026-07-01) · "1:1대화가 제대로 진행이 안돼" — 실제 원인:
`control_game_advance`가 항상 프론트가 보낸 고정 rapport로 새 Intervention을
만들어버려서, 1:1 대화(social/persuade)로 실제로 쌓인 GameRun.rapport(§11.4.4
위기개입과 공유하는 래포 풀)를 완전히 무시하고 있었다.

GameRun.advance_day 자체는 이미 "strategy만 넘기면 self.rapport 자동 사용"
계약을 지원한다(game_run.py 독스트링) — 문제는 엔드포인트가 그 경로를 안 타고
매번 명시적 Intervention(고정 rapport)을 만들어 그 계약을 우회하던 것.
advance_day를 스파이해 실제로 어떤 인자로 호출되는지 검증한다.
"""

import market_live_server as mls


def _advance_to_crisis_day(gid, n=21):
    mls.control_game_start(mls.GameStartBody(
        game_id=gid, answers={"q_panic": 1.0, "q_fomo": 1.0}, symbol="DOGE"))
    for _ in range(n):
        mls.control_game_advance(mls.GameAdvanceBody(game_id=gid))


def test_advance_without_explicit_rapport_lets_gamerun_use_shared_pool(monkeypatch):
    gid = "rapport_pool_spy"
    _advance_to_crisis_day(gid)
    g = mls._get_game(gid)

    captured = {}
    original = g.advance_day

    def spy(*args, **kwargs):
        captured.update(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(g, "advance_day", spy)

    r = mls.control_game_advance(mls.GameAdvanceBody(game_id=gid, strategy="B_함정직시", roll=1.0))
    assert r["status"] == "ok"
    # rapport를 명시 안 했으니 intervention 오버라이드가 아니라 strategy 경로를
    # 타야 한다 — GameRun이 자기 self.rapport(공유 풀)를 자동으로 쓴다.
    assert captured.get("intervention") is None
    assert captured.get("strategy") == "B_함정직시"


def test_explicit_rapport_still_builds_intervention_override(monkeypatch):
    """기존 배치/테스트 용도(명시적 rapport 오버라이드)는 계속 지원돼야 한다."""
    gid = "rapport_pool_override_spy"
    _advance_to_crisis_day(gid)
    g = mls._get_game(gid)

    captured = {}
    original = g.advance_day

    def spy(*args, **kwargs):
        captured.update(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(g, "advance_day", spy)

    r = mls.control_game_advance(mls.GameAdvanceBody(
        game_id=gid, strategy="B_함정직시", rapport=100.0, roll=0.0))
    assert r["status"] == "ok"
    assert captured.get("intervention") is not None
    assert captured["intervention"].rapport == 100.0


def test_persuade_raised_rapport_is_visible_to_gamerun_state():
    gid = "rapport_pool_visible"
    mls.control_game_start(mls.GameStartBody(game_id=gid, answers={}, symbol="DOGE"))
    before = mls._get_game(gid).rapport
    mls.control_game_persuade(mls.GamePersuadeBody(
        game_id=gid, npc_id="value_investor", direction="calm", roll=0.0))
    after = mls._get_game(gid).rapport
    assert after > before
