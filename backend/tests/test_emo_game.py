"""T-7: 미연시 턴 루프 본체(EmoGameRun) — 신규 모듈.

시장이벤트 → 게시판 강제노출(감정 델타 1회) → 선택지 → 결과반영 → 다음 날.
기존 game_run.py(구 게임, 라이브)는 건드리지 않고 새 상태머신으로 구현한다.
구 6함정 확률판정 없이 플레이어 선택으로 결과가 결정된다.

핵심 불변식: 노출 델타는 하루 1회만(board() GET 멱등, PLAN-READY 4d).
"""

import pytest

from sim.emo_game import CASH, PORTFOLIO_CATEGORIES, START_VALUE, EmoGameRun
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


# --- v3 §B: 게시판 {coin} 플레이스홀더 — 오늘 |변동률| 최대 카테고리 심볼 --- #
def test_board_substitutes_coin_with_biggest_move_category_symbol():
    # meme(DOGE)만 크게 흔들리게, 나머지는 0으로 고정 → meme이 항상 최대.
    returns = {"large_stable": [0.0], "mid_alt": [0.0], "meme": [-0.5], "stable": [0.0]}
    r = EmoGameRun.new(ANSWERS, ["market_crash"], returns, seed=1)
    board = r.board()
    assert "{coin}" not in board["scenario"]["text"]
    assert "DOGE" in board["scenario"]["text"]


def test_board_coin_symbol_picks_largest_absolute_move_deterministically():
    returns = {"large_stable": [0.01], "mid_alt": [0.5], "meme": [-0.05], "stable": [0.0]}
    r = EmoGameRun.new(ANSWERS, ["market_crash"], returns, seed=1)
    assert r._biggest_move_symbol() == "XRP"   # mid_alt = XRP, |0.5| 최대


def test_exposure_delta_applied_once_on_entering_day():
    # 급락 진입 → 초기 대비 fear 상승(노출 델타 1회 적용).
    r = _run()
    initial = build_initial_emotion(ANSWERS)
    assert isinstance(r.emotion, PlayerEmotionState)
    assert r.emotion.fear > initial.fear


def test_choose_applies_delta_logs_and_advances():
    r = _run()
    fear_before = r.emotion.fear
    r.choose("sell", coin_target="meme")   # 급락 매도 → 공포를 소모(감소)
    assert r.day == 1
    # T-53: 매도는 공포를 consume_fraction만큼 소모 → 스냅샷 공포가 감소한다
    # (스냅샷은 소모 직후·다음 날 노출 전 상태).
    assert r.emotion_log.snapshots[0].state.fear < fear_before
    # 하루 완료마다 스냅샷 1개.
    assert len(r.emotion_log.snapshots) == 1


def test_choose_rejects_unknown_choice():
    r = _run()
    with pytest.raises(ValueError):
        r.choose("nope")


def test_full_playthrough_terminates():
    r = _run()
    r.choose("sell", coin_target="meme")   # day0 급락 매도
    r.choose("buy", coin_target="meme")    # day1 급등 매수
    r.choose("hold")                        # day2 변동 유지
    assert r.is_over
    assert len(r.emotion_log.snapshots) == 3


def test_choose_after_over_raises():
    r = _run()
    for _ in range(3):
        r.choose("hold")
    with pytest.raises(RuntimeError):
        r.choose("hold")


def test_ending_inputs_has_verdict_and_wealth():
    r = _run()
    r.choose("buy", coin_target="meme")   # 급락에 매수
    r.choose("buy", coin_target="meme")
    r.choose("buy", coin_target="meme")
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
    assert set(r.holdings) == set(PORTFOLIO_CATEGORIES)   # T-30: 시장4 + 현금
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
    seller.choose("sell", coin_target="mid_alt")   # day0 급락에 매도 → 위험자산 현금화(반등 놓침)
    holder.choose("hold")                           # day0 유지 → 위험자산 유지(반등 탐)
    seller.choose("hold"); holder.choose("hold")
    # 유지한 쪽이 반등을 더 많이 타서 재산이 더 크다.
    assert holder.portfolio_value > seller.portfolio_value


def test_day_schedule_expands_place_to_8_slots():
    # T-22 맵 브릿지: 그날 장소 1개를 8슬롯(아침 집→장소→저녁 귀가)으로.
    r = _run()   # T-50a 셔플로 day0 장소는 seed 의존(단언은 clone_route 상대참조)
    sched = r.day_schedule()
    assert set(sched.keys()) == {1, 2, 3, 4, 5, 6, 7, 8}
    assert sched[1] == "집_차트" and sched[8] == "집_차트"   # 아침 집·저녁 귀가
    assert sched[4] == r.clone_route[0]                     # 낮엔 그날 장소


def test_day_schedule_visits_multiple_daytime_places():
    # 하루가 한 장소로 접히지 않고(단조·긴 이동=순간이동 원인 방지) 낮에 여러 곳을 돈다.
    r = _run()   # T-50a 셔플로 day0 장소는 seed 의존(단언은 clone_route 상대참조)
    sched = r.day_schedule()
    assert sched[1] == "집_차트" and sched[8] == "집_차트"     # 아침 집·저녁 귀가
    daytime = {sched[s] for s in (2, 3, 4, 5, 6, 7)}
    assert "집_차트" not in daytime                           # 낮엔 집에 머무르지 않음
    assert len(daytime) >= 2                                  # 서로 다른 장소 ≥2 (단조 아님)
    # 오후(슬롯5·6)는 오늘의 장소 = 동행이 만나는 곳(_emo_meetings 오후 밴드)
    assert sched[5] == r.clone_route[0] and sched[6] == r.clone_route[0]


# ── T-50 일과 가짓수 (A 랜덤화 · B 5→7곳 · C 방문수 가변) ────────────────
def test_route_shuffle_varies_by_seed_deterministically():
    # T-50a — 회차(seed)마다 동선 순서가 다르되, 같은 seed는 결정론 재생.
    from sim.emo_game import _default_route
    assert _default_route(7, seed=1) == _default_route(7, seed=1)   # 결정론 재생
    assert _default_route(7, seed=1) != _default_route(7, seed=2)   # 회차 변화


def test_route_cycle_includes_market_and_library():
    # T-50b — 마켓·도서관 편입(5→7곳).
    from sim.emo_game import _ROUTE_CYCLE
    assert "마켓" in _ROUTE_CYCLE and "도서관" in _ROUTE_CYCLE
    assert len(_ROUTE_CYCLE) == 7


def test_library_market_have_npc_candidates():
    # T-50b — 새 장소에 NPC 배치(정호=도서관, 미나=마켓) → companion 후보 존재.
    from sim.companion import daily_candidates
    from sim.personas import npc_scheds
    sch = npc_scheds()
    assert "value_investor" in daily_candidates("도서관", sch)
    assert "contrarian" in daily_candidates("마켓", sch)


def test_daytime_visits_vary_3_to_4():
    # T-50c — 낮 방문 장소 수가 날마다 3~4로 가변(오후 5·6=P 불변).
    r = EmoGameRun.new(ANSWERS, ["market_volatile"] * 6, _cat([0.0] * 6), seed=42)
    counts = set()
    for d in range(6):
        r.day = d
        sched = r.day_schedule()
        assert sched[5] == sched[6] == r.clone_route[d]   # 오후=P 불변
        daytime = {sched[s] for s in (2, 3, 4, 5, 6, 7)}
        counts.add(len(daytime))
    assert 3 in counts and 4 in counts   # 3곳 날·4곳 날 둘 다 등장


def test_holdings_serialized_roundtrip():
    r = EmoGameRun.new(ANSWERS, EVENTS, _cat(RETURNS), seed=1)
    r.choose("sell", coin_target="meme")   # 지정 코인 → 현금 매도
    assert abs(sum(r.holdings.values()) - r.portfolio_value) < 0.01
    restored = EmoGameRun.from_doc(r.to_doc())
    assert restored.holdings == r.holdings
    assert restored.portfolio_value == r.portfolio_value


def test_ending_returns_e1_to_e5_after_playthrough():
    r = _run()
    r.choose("buy", coin_target="meme")
    r.choose("buy", coin_target="meme")
    r.choose("buy", coin_target="meme")
    e = r.ending()
    assert e["id"] in ("E1", "E2", "E3", "E4", "E5")
    assert e["grade"] in ("고수", "벼락부자형", "강철멘탈형", "호구")
    assert len(e["epilogue"]) == 3


def test_chain_events_resolve_during_playthrough():
    # 실제 24편 데이터가 로드된 상태에서, 발동한 체인을 해결하며 완주.
    r = EmoGameRun.new(ANSWERS, EVENTS * 3, _cat(RETURNS * 3), seed=7)
    triggered = 0
    for cid in ["hold"] * 9:   # 유지로 매일 진행(체인 발동/해결이 검증 대상)
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


# --- T-28: 클론 이름 ------------------------------------------------------- #
def test_clone_name_is_set_from_new():
    run = EmoGameRun.new(ANSWERS, EVENTS, _cat(RETURNS), seed=1, name="철수")
    assert run.clone_name == "철수"


def test_clone_name_defaults_when_empty_or_whitespace():
    assert EmoGameRun.new(ANSWERS, EVENTS, _cat(RETURNS), seed=1, name="  ").clone_name == "내 클론"
    assert EmoGameRun.new(ANSWERS, EVENTS, _cat(RETURNS), seed=1, name=None).clone_name == "내 클론"
    assert EmoGameRun.new(ANSWERS, EVENTS, _cat(RETURNS), seed=1).clone_name == "내 클론"


def test_clone_name_is_trimmed_and_length_capped():
    run = EmoGameRun.new(ANSWERS, EVENTS, _cat(RETURNS), seed=1, name="  " + "가" * 30 + "  ")
    assert run.clone_name == "가" * 12   # 앞뒤 공백 제거 + 12자 제한


def test_clone_name_survives_serialization_roundtrip():
    run = EmoGameRun.new(ANSWERS, EVENTS, _cat(RETURNS), seed=1, name="영희")
    restored = EmoGameRun.from_doc(run.to_doc())
    assert restored.clone_name == "영희"


def test_clone_name_defaults_on_legacy_doc_without_field():
    run = EmoGameRun.new(ANSWERS, EVENTS, _cat(RETURNS), seed=1, name="영희")
    doc = run.to_doc()
    del doc["clone_name"]   # 구 doc(필드 없음)
    assert EmoGameRun.from_doc(doc).clone_name == "내 클론"


# --- T-30: 현금(cash) / 스테이블(USDT) 분리 ------------------------------- #
def test_cash_is_a_separate_portfolio_category():
    assert CASH == "cash"
    assert CASH in PORTFOLIO_CATEGORIES and CASH not in CATEGORIES   # 시장 카테고리 아님
    r = _run()
    assert CASH in r.holdings


def test_cash_and_stable_are_allocated_separately():
    alloc = {"large_stable": 0.4, "mid_alt": 0.0, "meme": 0.0, "stable": 0.3, "cash": 0.3}
    r = EmoGameRun.new(ANSWERS, EVENTS, _cat([0.0, 0.0, 0.0]), seed=1, allocation=alloc)
    assert r.holdings["stable"] == START_VALUE * 0.3   # USDT
    assert r.holdings["cash"] == START_VALUE * 0.3      # KRW — 별도 보유
    assert abs(r.portfolio_value - START_VALUE) < 0.01


def test_cash_has_zero_return_market_never_moves_it():
    # 현금은 시장 시리즈가 없어 수익률 0 — 시장이 어떻게 움직여도 불변.
    events = ["market_surge", "market_crash"]
    cr = {c: [0.5, -0.5] for c in CATEGORIES}   # 위험자산 급등락
    r = EmoGameRun.new(ANSWERS, events, cr, seed=1,
                       allocation={"cash": 1.0})   # 전액 현금
    start_cash = r.holdings["cash"]
    r.choose("hold")   # 유지(무매매) — 시장 실현(급등)돼도 현금은 그대로여야
    assert r.holdings["cash"] == start_cash


def test_cut_moves_risk_into_cash_not_stable():
    events = ["market_crash", "market_surge"]
    cr = {c: [-0.1, 0.1] for c in CATEGORIES}
    r = EmoGameRun.new(ANSWERS, events, cr, seed=1,
                       allocation={"large_stable": 0.5, "mid_alt": 0.5,
                                   "meme": 0.0, "stable": 0.0, "cash": 0.0})
    assert r.holdings["cash"] == 0.0
    r.choose("sell", coin_target="large_stable")   # 매도 → 위험자산이 현금(cash)으로 이동
    assert r.holdings["cash"] > 0.0        # 도피처는 현금
    assert r.holdings["stable"] == 0.0     # USDT는 손대지 않음


def test_cash_survives_serialization():
    r = EmoGameRun.new(ANSWERS, EVENTS, _cat([0.0, 0.0, 0.0]), seed=1,
                       allocation={"cash": 0.4, "large_stable": 0.6})
    restored = EmoGameRun.from_doc(r.to_doc())
    assert restored.holdings["cash"] == r.holdings["cash"]
    assert set(restored.holdings) == set(PORTFOLIO_CATEGORIES)


# --- T-30c: 캐시아웃 딜레마 ------------------------------------------------ #
def _big_gain_run():
    # T-53: 매수(buy)는 탐욕을 소모하므로 옛 chase 반복으로 탐욕 정점을 만들 수
    # 없다. 캐시아웃 딜레마는 '탐욕/공포 정점 + 위험 비중'에서 발동하므로, 며칠
    # 진행해 위험 비중을 유지한 중반 상태를 만든 뒤 감정 정점을 직접 세팅한다
    # (권위 테스트 패턴 r.emotion = PlayerEmotionState(...)와 동일).
    events = ["market_surge"] * 6
    cr = {c: ([0.25] * 6 if c != "stable" else [0.0] * 6) for c in CATEGORIES}
    r = EmoGameRun.new(ANSWERS, events, cr, seed=1,
                       allocation={"large_stable": 0.4, "mid_alt": 0.4, "meme": 0.2,
                                   "stable": 0.0, "cash": 0.0})
    for _ in range(4):          # day0..3 진행(유지 → 위험 비중 유지, 중반 진입)
        r.choose("hold")
    r.emotion = PlayerEmotionState(greed=85, fear=20, anxiety=40, restlessness=55, composure=45)
    return r


def test_cashout_dilemma_not_available_early_or_flat():
    r = EmoGameRun.new(ANSWERS, EVENTS, _cat([0.0, 0.0, 0.0]), seed=1)
    assert r.cashout_available() is False    # day0·무변동
    assert r.cashout_event() is None


def test_cashout_dilemma_available_after_big_swing():
    r = _big_gain_run()
    assert r.cashout_available() is True
    ev = r.cashout_event()
    assert ev and ev["gain"] is True
    assert {c["id"] for c in ev["choices"]} == {"cash_out", "stay"}


def test_cashout_moves_risk_to_cash_and_calms():
    r = _big_gain_run()
    fear_before = r.emotion.fear
    cash_before = r.holdings["cash"]
    risk_before = sum(r.holdings[c] for c in ("large_stable", "mid_alt", "meme"))
    r.cashout("cash_out")
    assert r.holdings["cash"] > cash_before                     # 현금으로 이동
    assert sum(r.holdings[c] for c in ("large_stable", "mid_alt", "meme")) < risk_before
    assert r.emotion.fear <= fear_before                        # 안심(위축 완화)
    assert r.cashout_available() is False                       # 1회만


def test_cashout_stay_keeps_risk_and_raises_greed():
    r = _big_gain_run()
    greed_before = r.emotion.greed
    risk_before = sum(r.holdings[c] for c in ("large_stable", "mid_alt", "meme"))
    r.cashout("stay")
    assert abs(sum(r.holdings[c] for c in ("large_stable", "mid_alt", "meme")) - risk_before) < 0.01
    assert r.emotion.greed >= greed_before
    assert r.cashout_available() is False


def test_cashout_flag_survives_serialization():
    r = _big_gain_run()
    r.cashout("stay")
    restored = EmoGameRun.from_doc(r.to_doc())
    assert restored.cashout_offered is True
    assert restored.cashout_available() is False


# --- T-37: 평정(composure) 긍정 축 ---------------------------------------- #
def test_composure_starts_neutral():
    r = _run()
    assert r.emotion.composure == 50   # 중립 시작


def test_hold_consumes_composure_sell_leaves_it():
    # T-53: 유지(hold)=평정을 consume_fraction만큼 소모(옛 '버티기=평정↑'의 반전),
    # 매도(sell)=공포 소모라 평정 불변. 스냅샷(선택 직후, 밤 회귀 전)으로 비교.
    events = ["market_crash", "market_crash"]
    cr = {c: [0.0, 0.0] for c in CATEGORIES}
    hold_run = EmoGameRun.new(ANSWERS, events, cr, seed=1)
    sell_run = EmoGameRun.new(ANSWERS, events, cr, seed=1)
    c0 = hold_run.emotion.composure
    hold_run.choose("hold")                       # 유지 → 평정 소모
    sell_run.choose("sell", coin_target="meme")   # 매도 → 공포 소모(평정 불변)
    assert hold_run.emotion_log.snapshots[0].state.composure < c0   # 평정 소모
    assert sell_run.emotion_log.snapshots[0].state.composure == c0   # 매도는 평정 불변


def test_composure_survives_serialization():
    r = _run()
    r.choose("hold")   # 평정 변화
    restored = EmoGameRun.from_doc(r.to_doc())
    assert restored.emotion.composure == r.emotion.composure


def test_legacy_doc_without_composure_defaults_neutral():
    r = _run()
    doc = r.to_doc()
    del doc["emotion"]["composure"]   # 구 doc(4축)
    assert EmoGameRun.from_doc(doc).emotion.composure == 50


def test_high_composure_yields_controlled_ending_even_if_leaning():
    from sim.ending import emotion_controlled
    # 과열이어도 평정이 높으면 통제됨(좋은 엔딩 쪽).
    assert emotion_controlled("과열", composure=70) is True
    assert emotion_controlled("과열", composure=40) is False
    assert emotion_controlled("중립", composure=40) is True   # 중립은 평정 무관 통제


# --- T-35: 오늘의 장(카테고리별 수익률) 리포트용 ------------------------- #
def test_last_market_records_day_returns_as_percent():
    events = ["market_surge", "market_surge"]
    cr = {"large_stable": [0.02, 0.0], "mid_alt": [0.05, 0.0],
          "meme": [0.40, 0.0], "stable": [0.0, 0.0]}
    r = EmoGameRun.new(ANSWERS, events, cr, seed=1)
    assert r.last_market == {}          # 정산 전엔 비어있음
    r.choose("hold")                     # day0 정산(무매매)
    assert r.last_market["meme"] == 40.0
    assert r.last_market["large_stable"] == 2.0
    assert r.last_market["stable"] == 0.0
    # 직렬화 왕복 보존.
    assert EmoGameRun.from_doc(r.to_doc()).last_market == r.last_market
