"""T-016 학습 로그·설문 Mongo 영속화 (로컬 dev mongo, 멱등)."""

from __future__ import annotations

import pytest

from backend import db

_UID = "__test_learning_uid__"


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    d = db._db()
    d.intervention_logs.delete_many({"uid": _UID})
    d.trade_logs.delete_many({"uid": _UID})
    d.surveys.delete_one({"_id": _UID})


def test_save_and_load_roundtrip():
    ilogs = [{"uid": _UID, "round": 1, "act": 1, "choice_tag": "공포_동조"}]
    tlogs = [{"uid": _UID, "round": 1, "act": 1, "agent_id": "c", "action": "SELL"}]
    db.save_intervention_logs(_UID, ilogs)
    db.save_trade_logs(_UID, tlogs)
    db.save_surveys(_UID, pre={"predicted_panic": 0.2}, post={"predicted_panic": 0.7})

    loaded = db.load_learning(_UID)
    assert len(loaded["intervention_logs"]) == 1
    assert loaded["intervention_logs"][0]["choice_tag"] == "공포_동조"
    assert len(loaded["trade_logs"]) == 1
    assert loaded["pre_survey"]["predicted_panic"] == 0.2
    assert loaded["post_survey"]["predicted_panic"] == 0.7


def test_save_is_idempotent():
    logs = [{"uid": _UID, "round": 1, "act": 1, "agent_id": "c", "action": "BUY"}]
    db.save_trade_logs(_UID, logs)
    db.save_trade_logs(_UID, logs)  # 두 번 저장해도 중복 없음
    loaded = db.load_learning(_UID)
    assert len(loaded["trade_logs"]) == 1


def test_load_empty_safe():
    loaded = db.load_learning("__nonexistent_uid__")
    assert loaded["intervention_logs"] == []
    assert loaded["trade_logs"] == []
    assert loaded["pre_survey"] is None and loaded["post_survey"] is None


def test_server_persist_and_reload_roundtrip():
    """라운드+개입 후 영속화 → 재구성 시 로그가 복원된다(resume 경로)."""
    import market_live_server as mls
    from sim.models import InterventionLog, TradeLog

    live = mls.Live("s", assets=None, seed=4)
    live.game.run_round("해킹 루머", is_rumor=True)
    live.game.log_intervention(choice_tag="공포_동조", resolved=True, market_situation="crash")
    live.pre_survey = {"predicted_panic": 0.3}
    try:
        mls._persist_learning(live, _UID)
        loaded = db.load_learning(_UID)
        assert loaded["trade_logs"], "매매 로그 영속화"
        assert loaded["intervention_logs"][0]["choice_tag"] == "공포_동조"
        assert loaded["pre_survey"]["predicted_panic"] == 0.3
        # resume 재구성: dict → 모델 복원이 깨지지 않는지
        rebuilt_i = [InterventionLog(**d) for d in loaded["intervention_logs"]]
        rebuilt_t = [TradeLog(**d) for d in loaded["trade_logs"]]
        assert rebuilt_i[0].choice_tag == "공포_동조"
        assert rebuilt_t[0].agent_id
    finally:
        db._db().intervention_logs.delete_many({"uid": _UID})
        db._db().trade_logs.delete_many({"uid": _UID})
        db._db().surveys.delete_one({"_id": _UID})
