"""T-14: EmoGameRun 영속화 (인메모리 1차 + Mongo 보조).

로컬/인메모리 폴백 경로를 검증한다(Mongo 없이도 동작). 실제 프로덕션 Mongo
쓰기는 하드게이트(env MONGO_URI)라 여기선 db 계층을 가짜로 대체해 재시작 경로만
검증한다.
"""

from sim import emo_store
from sim.emo_game import EmoGameRun

from sim.fate_line import CATEGORIES

EVENTS = ["market_crash", "market_surge", "market_volatile"]
RETURNS = [-0.2, 0.3, 0.05]
ANSWERS = {"q_panic": 0.5, "q_fomo": 0.5, "q_rumor": 0.5, "q_check": 0.5}


def _run():
    cat_returns = {c: list(RETURNS) for c in CATEGORIES}
    return EmoGameRun.new(ANSWERS, EVENTS, cat_returns, seed=42)


def setup_function():
    emo_store._clear()


def test_save_then_load_from_memory():
    r = _run()
    r.choose("hold")
    emo_store.save_run("g1", r)
    loaded = emo_store.load_run("g1")
    assert loaded is not None
    assert loaded.day == r.day
    assert loaded.emotion == r.emotion


def test_load_unknown_is_none():
    assert emo_store.load_run("nope") is None


def test_restart_falls_back_to_db(monkeypatch):
    # 서버 재시작 시뮬레이션: 인메모리는 비우고, db 계층을 가짜로.
    fake = {}
    monkeypatch.setattr(emo_store.db, "save_game", lambda gid, doc: fake.__setitem__(gid, doc) or True)
    monkeypatch.setattr(emo_store.db, "load_game", lambda gid: fake.get(gid))

    r = _run()
    r.choose("hold")
    emo_store.save_run("g2", r)

    emo_store._clear()                     # 재시작 = 인메모리 소실
    loaded = emo_store.load_run("g2")      # db(가짜)에서 복원
    assert loaded is not None
    assert loaded.day == r.day
    assert loaded.emotion == r.emotion
    assert loaded.special_event_count == r.special_event_count


def test_every_turn_snapshot_persists():
    # 매 턴 저장 → 스냅샷 누적이 보존됨.
    r = _run()
    for cid in ["hold", "watch", "step_away"]:
        r.choose(cid)
        emo_store.save_run("g3", r)
    loaded = emo_store.load_run("g3")
    assert len(loaded.emotion_log.snapshots) == 3
