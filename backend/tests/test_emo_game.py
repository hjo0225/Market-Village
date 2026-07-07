"""T-7: 미연시 턴 루프 본체(EmoGameRun) — 신규 모듈.

시장이벤트 → 게시판 강제노출(감정 델타 1회) → 선택지 → 결과반영 → 다음 날.
기존 game_run.py(구 게임, 라이브)는 건드리지 않고 새 상태머신으로 구현한다.
구 6함정 확률판정 없이 플레이어 선택으로 결과가 결정된다.

핵심 불변식: 노출 델타는 하루 1회만(board() GET 멱등, PLAN-READY 4d).
"""

import pytest

from sim.emo_game import START_VALUE, EmoGameRun
from sim.fate_line import CATEGORIES
from sim.interview import build_initial_emotion
from sim.player_emotion.state import PlayerEmotionState

# 3일치 시나리오: 급락 → 급등 → 변동. 각 날 시장 수익률.
EVENTS = ["market_crash", "market_surge", "market_volatile"]
RETURNS = [-0.2, 0.3, 0.05]
ANSWERS = {"q_panic": 0.5, "q_fomo": 0.5, "q_rumor": 0.5, "q_check": 0.5}


def _cat(returns):
    """스칼라 수익률 시퀀스를 전 카테고리 동일 적용(포트폴리오 무관 테스트 편의)."""
    return {c: list(returns) for c in CATEGORIES}


def _run():
    return EmoGameRun.new(ANSWERS, EVENTS, _cat(RETURNS), seed=42)


def test_starts_at_day0_not_over():
    r = _run()
    assert r.day == 0
    assert not r.is_over


def test_board_is_idempotent_get():
    # board()를 여러 번 불러도 같은 결과 + 감정 불변(4d — 리로드/리마운트 안전).
    r = _run()
    b1 = r.board()
    emo_after_first = r.emotion
    b2 = r.board()
    assert b1["threads"] == b2["threads"]
    assert b1["scenario"] == b2["scenario"]
    assert r.emotion == emo_after_first
    assert len(b1["scenario"]["choices"]) == 3


def test_exposure_delta_applied_once_on_entering_day():
    # 급락 진입 → 초기 대비 fear 상승(노출 델타 1회 적용).
    r = _run()
    initial = build_initial_emotion(ANSWERS)
    assert isinstance(r.emotion, PlayerEmotionState)
    assert r.emotion.fear > initial.fear


def test_choose_applies_delta_logs_and_advances():
    r = _run()
    fear_before = r.emotion.fear
    r.choose("cut")            # 급락 손절 → 그 날 fear 상승
    assert r.day == 1
    # 그 날 선택 효과는 스냅샷에 기록(다음 날 노출 전). live emotion은 이미 day1
    # 노출(양방향)까지 반영돼 방향이 달라질 수 있으므로 스냅샷으로 검증.
    assert r.emotion_log.snapshots[0].state.fear > fear_before
    # 하루 완료마다 스냅샷 1개.
    assert len(r.emotion_log.snapshots) == 1


def test_choose_rejects_unknown_choice():
    r = _run()
    with pytest.raises(ValueError):
        r.choose("nope")


def test_full_playthrough_terminates():
    r = _run()
    r.choose("hold")     # day0 급락
    r.choose("chase")    # day1 급등
    r.choose("stare")    # day2 변동
    assert r.is_over
    assert len(r.emotion_log.snapshots) == 3


def test_choose_after_over_raises():
    r = _run()
    for cid in ("hold", "watch", "step_away"):
        r.choose(cid)
    with pytest.raises(RuntimeError):
        r.choose("hold")


def test_ending_inputs_has_verdict_and_wealth():
    r = _run()
    r.choose("buy_dip")   # 급락에 매수
    r.choose("chase")
    r.choose("day_trade")
    ei = r.ending_inputs()
    assert ei["verdict"] in ("과열", "위축", "중립")
    assert ei["wealth_level"] in ("high", "low")


def test_allocation_splits_start_value_into_holdings():
    # setup 배분(분수)이 초기 holdings로 분배되고 합=START_VALUE.
    alloc = {"large_stable": 0.5, "mid_alt": 0.0, "meme": 0.0, "stable": 0.5}
    r = EmoGameRun.new(ANSWERS, EVENTS, _cat([0.0, 0.0, 0.0]), seed=1, allocation=alloc)
    assert r.holdings["large_stable"] == START_VALUE * 0.5
    assert r.holdings["stable"] == START_VALUE * 0.5
    assert abs(r.portfolio_value - START_VALUE) < 0.01


def test_default_allocation_covers_all_categories():
    r = _run()
    assert set(r.holdings) == set(CATEGORIES)
    assert abs(r.portfolio_value - START_VALUE) < 0.01


def test_choice_rebalances_risk_to_cash_affects_wealth():
    # 하락→반등 시장에서 손절(위험자산→현금) vs 버티기 → 재산이 달라진다.
    events = ["market_crash", "market_surge"]
    cr = {  # 위험자산은 급락 후 반등, 현금(stable)은 평평.
        "large_stable": [-0.10, 0.10],
        "mid_alt": [-0.10, 0.10],
        "meme": [-0.10, 0.10],
        "stable": [0.0, 0.0],
    }
    alloc = {"large_stable": 0.4, "mid_alt": 0.4, "meme": 0.2, "stable": 0.0}
    seller = EmoGameRun.new(ANSWERS, events, cr, seed=1, allocation=alloc)
    holder = EmoGameRun.new(ANSWERS, events, cr, seed=1, allocation=alloc)
    seller.choose("cut")     # day0 급락에 손절 → 위험자산 대량 현금화(반등 놓침)
    holder.choose("hold")    # day0 버티기 → 위험자산 유지(반등 탐)
    seller.choose("watch"); holder.choose("watch")
    # 버틴 쪽이 반등을 더 많이 타서 재산이 더 크다.
    assert holder.portfolio_value > seller.portfolio_value


def test_day_schedule_expands_place_to_8_slots():
    # T-22 맵 브릿지: 그날 장소 1개를 8슬롯(아침 집→장소→저녁 귀가)으로.
    r = _run()   # day0 clone_route = "카페"
    sched = r.day_schedule()
    assert set(sched.keys()) == {1, 2, 3, 4, 5, 6, 7, 8}
    assert sched[1] == "집_차트" and sched[8] == "집_차트"   # 아침 집·저녁 귀가
    assert sched[4] == r.clone_route[0]                     # 낮엔 그날 장소


def test_holdings_serialized_roundtrip():
    r = EmoGameRun.new(ANSWERS, EVENTS, _cat(RETURNS), seed=1)
    r.choose("cut")          # 위험자산 → 현금 리밸런싱
    assert abs(sum(r.holdings.values()) - r.portfolio_value) < 0.01
    restored = EmoGameRun.from_doc(r.to_doc())
    assert restored.holdings == r.holdings
    assert restored.portfolio_value == r.portfolio_value


def test_ending_returns_e1_to_e5_after_playthrough():
    r = _run()
    r.choose("buy_dip")
    r.choose("chase")
    r.choose("day_trade")
    e = r.ending()
    assert e["id"] in ("E1", "E2", "E3", "E4", "E5")
    assert e["grade"] in ("고수", "벼락부자형", "강철멘탈형", "호구")
    assert len(e["epilogue"]) == 3


def test_chain_events_resolve_during_playthrough():
    # 실제 24편 데이터가 로드된 상태에서, 발동한 체인을 해결하며 완주.
    r = EmoGameRun.new(ANSWERS, EVENTS * 3, _cat(RETURNS * 3), seed=7)
    triggered = 0
    for cid in ["hold", "chase", "stare"] * 3:
        ev = r.chain_event()
        if ev is not None:
            assert ev["text"].strip() and len(ev["choices"]) == 2
            r.chain_choose(ev["choices"][0]["id"])
            triggered += 1
        r.choose(cid)
    assert r.is_over
    # 데이터가 로드됐으므로 최소 1회는 발동(prob 0.6 × 다수 일).
    assert triggered >= 1
    assert r.special_event_count == triggered


def test_serialization_roundtrip_does_not_reapply_exposure():
    r = _run()
    r.choose("hold")            # 이제 day1(급등) 진입, 노출 적용됨
    emo = r.emotion
    day = r.day
    doc = r.to_doc()
    restored = EmoGameRun.from_doc(doc)
    # 복원 시 노출을 재적용하지 않는다 — 감정·날짜 그대로.
    assert restored.emotion == emo
    assert restored.day == day
    assert len(restored.emotion_log.snapshots) == len(r.emotion_log.snapshots)
    # 복원 후 board()도 멱등.
    assert restored.board()["threads"] == r.board()["threads"]
