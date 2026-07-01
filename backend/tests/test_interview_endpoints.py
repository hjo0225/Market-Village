"""T-212 · 대화형 인터뷰 엔드포인트 — GameRun 시작 전 자유 텍스트 인터뷰 세션.

인터뷰는 게임 시작 전(game_id 없이) 독립 세션으로 진행되고, 완료 시 나온
answers dict를 그대로 기존 `/control/game/start`의 answers 필드에 넣으면 된다
(계약 호환, 슬라이더 방식과 병행 — 기존 흐름 무변경).
"""

from __future__ import annotations

import market_live_server as mls


def test_next_without_session_uses_fresh_flow():
    r = mls.control_interview_next(session_id="iv1")
    assert r["status"] == "ok" and r["done"] is False
    assert r["next"]["id"] == "q_experience"


def test_answer_then_next_advances():
    mls.control_interview_next(session_id="iv2")
    r = mls.control_interview_answer(mls.InterviewAnswerBody(
        session_id="iv2", qid="q_experience", text="네 투자 좀 해봤어요"))
    assert r["status"] == "ok"
    assert r["next"]["id"] != "q_experience"


def test_full_flow_completes_with_answers():
    sid = "iv3"
    texts = {"q_experience": "네 해봤어요", "q_panic": "바로 손절해요",
             "q_fomo": "추격매수 해요", "q_rumor": "많이 흔들려요",
             "q_check": "수시로 봐요"}
    last = None
    for _ in range(10):
        r = mls.control_interview_next(session_id=sid)
        if r["done"]:
            break
        qid = r["next"]["id"]
        last = mls.control_interview_answer(mls.InterviewAnswerBody(
            session_id=sid, qid=qid, text=texts.get(qid, "")))
    assert last["done"] is True
    assert "answers" in last
    assert set(last["answers"]) >= {"q_panic", "q_fomo", "q_rumor", "q_check"}


def test_answers_feed_directly_into_game_start():
    sid = "iv4"
    texts = {"q_experience": "네 해봤어요", "q_panic": "바로 손절해요",
             "q_fomo": "추격매수 해요", "q_rumor": "많이 흔들려요",
             "q_check": "수시로 봐요"}
    last = None
    for _ in range(10):
        r = mls.control_interview_next(session_id=sid)
        if r["done"]:
            break
        qid = r["next"]["id"]
        last = mls.control_interview_answer(mls.InterviewAnswerBody(
            session_id=sid, qid=qid, text=texts.get(qid, "")))
    start = mls.control_game_start(mls.GameStartBody(
        game_id="gs_from_iv", answers=last["answers"], symbol="DOGE"))
    assert start["status"] == "ok"


def test_unknown_qid_answer_rejected():
    mls.control_interview_next(session_id="iv5")
    r = mls.control_interview_answer(mls.InterviewAnswerBody(
        session_id="iv5", qid="q_bogus", text="아무말"))
    assert r["status"] == "error"
