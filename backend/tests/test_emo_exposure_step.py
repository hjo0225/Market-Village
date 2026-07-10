"""T-61 (1안) 통합 + T-62 (D): 성향 민감도가 _enter_day 노출에 반영되고,
밤 전이가 감쇠/노출 2스텝으로 분리돼 캐스케이드에 노출이 보인다.

핵심: 이 두 변경은 감정축(게임플레이)에만 닿고 리포트 actual_bias/self_awareness는
무접촉 — 같은 클릭 시퀀스면 성향이 달라도 actual_bias는 동일(순환 없음).
"""
from sim.emo_game import EmoGameRun
from sim.fate_line import CATEGORIES
from sim.player_emotion.state import PlayerEmotionState

ANSWERS = {"Q1": 2, "Q2": 2, "Q3": 2, "Q4": 2, "Q5": 2, "Q6": 2, "Q7": 2}


def _cat(returns):
    return {c: list(returns) for c in CATEGORIES}


def _fear_after_crash(dtype: str) -> float:
    run = EmoGameRun.new(ANSWERS, ["market_crash"], _cat([-0.1]), seed=1)
    run.emotion = PlayerEmotionState(fear=50, greed=50, anxiety=50, restlessness=50, composure=50)
    run.disposition = {"declared_type": dtype}
    run.day = 0
    run._enter_day()   # day 0 → 감쇠 없음, 성향 배율만 반영된 노출
    return run.emotion.fear


# --- T-61: 성향이 노출 감정 델타를 성향별로 증폭 ---------------------------- #
def test_enter_day_scales_exposure_by_disposition():
    # 급락(fear+): 안정형은 공포에 더 크게, 공격형은 덜 흔들린다.
    assert _fear_after_crash("안정형") > _fear_after_crash("위험중립형") > _fear_after_crash("공격투자형")


def test_neutral_disposition_matches_unscaled_baseline():
    # 위험중립형(×1.0) = 배율 없는 원본 노출 결과(회귀 기준선). crash fear delta ≈ +11.26.
    assert abs(_fear_after_crash("위험중립형") - (50 + 11.26)) < 0.5


# --- T-62: 밤 전이 감쇠/노출 분리 ------------------------------------------ #
def test_settlement_exposes_night_market_step():
    # day0 정산의 밤 전이(→day1 진입)에 source="exposure" 스텝이 캐스케이드에 존재.
    run = EmoGameRun.new(ANSWERS, ["market_crash"] * 3, _cat([-0.1, 0.05, 0.02]), seed=1)
    run.choose("hold", coin_target="meme")
    sources = [s["source"] for s in run.last_settlement["emotion_steps"]]
    assert "exposure" in sources


def test_cascade_invariant_holds_with_split_steps():
    # §5.1: emotion_before + Σsteps == emotion_after (감쇠/노출 분리 후에도 정확).
    run = EmoGameRun.new(ANSWERS, ["market_crash"] * 3, _cat([-0.1, 0.05, 0.02]), seed=1)
    run.choose("hold", coin_target="meme")
    st = run.last_settlement
    for axis in ("fear", "greed", "anxiety", "restlessness", "composure"):
        total = st["emotion_before"][axis] + sum(s["deltas"][axis] for s in st["emotion_steps"])
        assert abs(total - st["emotion_after"][axis]) < 0.01, axis


def test_disposition_does_not_leak_into_actual_bias():
    # 🔒 순환 없음: 같은 클릭 시퀀스면 성향이 달라도 actual_bias는 동일해야 한다.
    def actual_bias_for(dtype: str) -> dict:
        run = EmoGameRun.new(ANSWERS, ["market_crash"] * 3, _cat([-0.1, 0.05, 0.02]), seed=1)
        run.disposition = {**run.disposition, "declared_type": dtype}
        for _ in range(3):
            if run.is_over:
                break
            run.choose("buy", coin_target="meme")
        return run.actual_bias()

    assert actual_bias_for("안정형") == actual_bias_for("공격투자형")
