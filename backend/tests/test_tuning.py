"""T-100 · §11.5 중앙 상수 모듈 검증.

PRD §11.5 "첫 빌드 초기 수치표"의 모든 상수를 한 모듈(sim.tuning)에 모은다.
값은 정답이 아니라 플레이 테스트 튜닝의 출발점(§11.5 주의). 여기선 PRD에
명시된 초기값과 구조적 불변식(비대칭·부호·범위)만 고정한다.
"""

from __future__ import annotations

from sim import tuning as T


# --- 1) 감정 스탯 증감 (§11.5.1) — 비대칭 8:3 ----------------------------- #
def test_emotion_deltas_asymmetric():
    assert T.DELTA_TRAP == -8.0          # 함정에 빠짐
    assert T.DELTA_RESIST == 3.0         # 견딤(회복은 더디게)
    assert T.DELTA_CALM == 1.0           # 평온한 날
    # 비대칭 핵심: 나쁨:좋음 = 8:3
    assert T.ASYM_BAD == 8 and T.ASYM_GOOD == 3
    assert abs(T.DELTA_TRAP) > T.DELTA_RESIST > T.DELTA_CALM
    lo, hi = T.CONTAGION_WORSEN_RANGE
    assert lo == -6.0 and hi == -2.0


# --- 2) 함정 트리거 임계값 (§11.5.2 / §8.2) ------------------------------ #
def test_trap_thresholds():
    assert T.F1_CRASH_PCT == -15.0
    assert T.F2_DIP_DAYS == 4
    assert T.F2_GAUGE == 70.0
    assert T.F2_GAUGE_UP_ON_DROP == 20.0    # 하락일 게이지 +20
    assert T.F2_GAUGE_DOWN_ON_RISE == -10.0  # 상승일 게이지 −10
    assert T.G1_PROFIT_PCT == 30.0
    assert T.G2_CONFIDENCE == 75.0
    assert T.M1_SURGE_PCT == 20.0
    assert T.M2_FGI == 75.0
    assert T.CONFIRMATION_BIAS_IGNORE_STREAK == 3
    # F1 급락은 음수, M1/G1 급등·익절은 양수 (부호 방향 불변식)
    assert T.F1_CRASH_PCT < 0 < T.M1_SURGE_PCT
    assert T.G1_PROFIT_PCT > 0


# --- 3) 저항 판정 4요소 계산식 상수 (§11.5.3) --------------------------- #
def test_resistance_formula_constants():
    assert T.RESIST_BASE == 50.0
    assert T.RAPPORT_MID == 50.0
    assert T.RAPPORT_SCALE == 0.4         # 최대 ±20%p
    assert T.STRATEGY_FIT_BONUS == 20.0
    assert T.STRATEGY_NEUTRAL == 0.0
    assert T.STRATEGY_BACKFIRE == -30.0
    assert T.ESCALATION_SCALE == 0.5      # 최대 −50%p
    assert T.TRAIT_FLOOR_WEAK == 70.0     # 약점 함정 상한 (항상 30% 무시)
    assert T.TRAIT_FLOOR_NORMAL == 95.0
    # 약점 함정은 비약점보다 성공 상한이 낮다 (§11.1 극복 100% 불가)
    assert T.TRAIT_FLOOR_WEAK < T.TRAIT_FLOOR_NORMAL
    assert T.trait_floor(weak=True) == 70.0
    assert T.trait_floor(weak=False) == 95.0


# --- 4) 교류 효과 & 전염 강도 (§11.5.4) -------------------------------- #
def test_contagion_strengths():
    assert T.CONTAGION_STABLE_NPC == 4.0
    assert T.CONTAGION_STIMULATING_NPC == -5.0
    assert T.PERSUASION_BONUS == 3.0          # 권유 성공 시 ±3
    assert T.CLONE_TO_NPC_RATIO == 0.30
    assert T.CLONE_TO_NPC_RATIO_EXTREME == 0.80
    assert T.CLONE_EXTREME_THRESHOLD == 15.0  # 내성 ≤ 15
    assert T.NPC_RECOVERY_PER_DAY == 3.0
    assert T.STRONG_EMOTION_GAP == 30.0
    assert T.STRONG_EMOTION_MULT == 1.5
    # 안정형은 올리고 자극형은 내린다 (부호)
    assert T.CONTAGION_STABLE_NPC > 0 > T.CONTAGION_STIMULATING_NPC
    # 극단 상태에서 클론→NPC 전염이 강해진다
    assert T.CLONE_TO_NPC_RATIO_EXTREME > T.CLONE_TO_NPC_RATIO


# --- 5) 확률 외란 & 뉴스 톤 반응 (§11.5.5) ----------------------------- #
def test_disturbance_and_news_tone():
    assert T.DISTURBANCE_PROB == 0.20
    assert T.DISTURBANCE_SIZE_RANGE == (2.0, 4.0)
    assert T.NEWS_TONE_DELTA == -6.0          # 민감 클론
    assert T.NEWS_TONE_REVERSE == 3.0         # 역행형(줍줍)
    assert T.NEWS_COEF_RANGE == (0.5, 1.5)
    assert T.SIGNATURE_MULT_RANGE == (2.0, 3.0)
    # 시그니처 드라마는 일반 뉴스보다 강하다
    lo, _ = T.SIGNATURE_MULT_RANGE
    assert lo >= 2.0


def test_clamp_helper():
    assert T.clamp(120, 0, 100) == 100
    assert T.clamp(-5, 0, 100) == 0
    assert T.clamp(50, 0, 100) == 50
