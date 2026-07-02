"""§11.5 첫 빌드 초기 수치표 — 단일 진실 소스.

PRD §11.5: "이 값들은 정답이 아니다. 이 값으로 빌드가 돌아가고, 여기서부터
플레이 테스트로 튜닝한다는 출발점이다." 따라서 이 모듈은 PRD에 명시된 초기값을
한 곳에 모아 매직넘버 산재를 막는다. 새 PRD 시스템(traps/resistance/news/
day_loop/clone_stats)은 전부 여기서 상수를 읽는다.

표기(§11.5 주의): 우리 클론 표시용 스탯은 "내성/저항"(높을수록 강함), 코드 NPC는
"수치"(높을수록 취약, §9.5.2). 아래 감정 델타는 **클론 스탯(내성) 기준**.

NOTE: 기존 emotion.py(_DELTA_MIN/_MAX)·trade.py(임계)에 이미 일부 상수가 있으나
회귀 위험 때문에 그쪽을 재배선하지 않는다. 이 모듈은 새 시스템의 권위 소스이며,
겹치는 값은 주석으로 표시한다.
"""

from __future__ import annotations


def clamp(value: float, low: float, high: float) -> float:
    """[low, high] 하드클램프 (emotion.py._clamp과 동일 시맨틱, 공용)."""
    return max(low, min(high, value))


# --------------------------------------------------------------------------- #
# 1) 감정 스탯 증감 — 비대칭(나빠지긴 쉽게, 좋아지긴 어렵게) §11.5.1
# --------------------------------------------------------------------------- #
DELTA_TRAP = -8.0            # 함정에 빠짐(충동 매매 실행) → 크게 흔들림
DELTA_RESIST = 3.0          # 함정 견딤(저항 성공) → 회복은 더디게
DELTA_CALM = 1.0            # 평온한 날 통과 → 자연 회복 미미
CONTAGION_WORSEN_RANGE = (-6.0, -2.0)   # 양방향 전염으로 악화(강도 비례)
ASYM_BAD = 8                # 비대칭 비율 ≈ 나쁨:좋음 = 8:3
ASYM_GOOD = 3

# 감정 스탯 스케일(코드 emotion.py 호환): 0~100, per-call delta는 [-50,50] 하드클램프
STAT_MIN = 0.0
STAT_MAX = 100.0
DELTA_HARD_MIN = -50.0
DELTA_HARD_MAX = 50.0


# --------------------------------------------------------------------------- #
# 2) 함정 트리거 임계값 §11.5.2 / §8.2
# --------------------------------------------------------------------------- #
F1_CRASH_PCT = -15.0        # 단일 봉 −15% 이상 급락
F2_DIP_PCT_RANGE = (-5.0, -2.0)   # 소폭 하락 −2%~−5%
F2_DIP_DAYS = 4             # 누적 4일
F2_GAUGE = 70.0            # 마모 게이지 임계
F2_GAUGE_UP_ON_DROP = 20.0    # 하락일 게이지 +20
F2_GAUGE_DOWN_ON_RISE = -10.0  # 상승일 게이지 −10
G1_PROFIT_PCT = 30.0       # 보유 평가익 +30% 도달
G2_CONFIDENCE = 75.0       # confidence ≥ 75 AND 직전 매매 수익 실현
M1_SURGE_PCT = 20.0        # 미보유 종목 단일 봉 +20% 급등
M2_FGI = 75.0             # 시장 과열 FGI ≥ 75 AND 군중 매수 우세
# §9.3 폭주 방지 — crowd_mood는 밤사이 중립(50)으로 이만큼 회귀한다(T-225에서 발견:
# 게시판 +3.5/일에 감쇠가 없으면 M2가 영구 발동. 0.15면 매일 열려도 평형 ≈ 69.8 < 75).
CROWD_MOOD_REVERT = 0.15
# 게시판(D2 개정) — 마을이 수군댈 만한 시장 급변동 기준(전일 종가 대비 ±%). [TUNE]
BOARD_MARKET_MOVE_PCT = 8.0
# T-249 — 1:1 만남 감정 효과(밤 정산). 외란(±2~4)·대화 보정(±3)과 같은 급, 소폭. [TUNE]
MEETING_STIM_DELTA = 1.5   # 자극형 NPC와 어울린 날: 관련 저항 스탯 -1.5
MEETING_CALM_DELTA = 1.0   # 도움형 NPC와 어울린 날: 멘탈회복 +1.0
CONFIRMATION_BIAS_IGNORE_STREAK = 3   # 손실 포지션 중 비관 정보 3회 연속 무시

# T-210 — 다자산 자금흐름(§8.3 to_hotter/concentrate 충동매매의 실제 이동 비율)
CHASE_FRACTION = 0.5        # M1/M2 충동: 보유 현금의 몇 %를 급등 종목에 새로 태우나
CONCENTRATE_FRACTION = 0.5  # G2 충동: 보유 현금의 몇 %를 기존 포지션에 더 넣나(몰빵)


# --------------------------------------------------------------------------- #
# 3) 저항 판정 4요소 계산식 (개입 성공 확률) §11.5.3
#   기본 50% + (래포−50)×0.4 + 전략적합(+20/0/−30) − 격앙×0.5
#   최종 = clamp(합, 0, 기질바닥 상한)
# --------------------------------------------------------------------------- #
RESIST_BASE = 50.0
RAPPORT_MID = 50.0
RAPPORT_SCALE = 0.4         # (래포 0~100 − 50) × 0.4 → 최대 ±20%p
STRATEGY_FIT_BONUS = 20.0   # 적합
STRATEGY_NEUTRAL = 0.0     # 무관
STRATEGY_BACKFIRE = -30.0   # 역효과(§11.4.2b 명확 조합만)
ESCALATION_SCALE = 0.5      # 격앙도(0~100) × 0.5 → 최대 −50%p
TRAIT_FLOOR_WEAK = 70.0     # 약점 함정 상한(=항상 30% 무시)
TRAIT_FLOOR_NORMAL = 95.0   # 비약점 상한
# 격앙도 = (100−관련내성)×0.6 + 당일자극×0.4
ESCALATION_RESILIENCE_W = 0.6
ESCALATION_STIMULUS_W = 0.4


def trait_floor(weak: bool) -> float:
    """약점 함정이면 70%, 아니면 95% 상한 (§11.1 극복 100% 불가)."""
    return TRAIT_FLOOR_WEAK if weak else TRAIT_FLOOR_NORMAL


# --------------------------------------------------------------------------- #
# 4) 교류 효과 & 전염 강도 (1:1 만남당) §11.5.4
# --------------------------------------------------------------------------- #
CONTAGION_STABLE_NPC = 4.0      # 안정형 NPC 1:1(거북이·퀀트 등) → 관련 내성 +4
CONTAGION_STIMULATING_NPC = -5.0  # 자극형 NPC 1:1(개구리·도박꾼 등) → −5
PERSUASION_BONUS = 3.0          # 대화 권유 성공 시 추가 보정 ±3
CLONE_TO_NPC_RATIO = 0.30       # 클론→NPC 전염 = NPC→클론의 30%
CLONE_TO_NPC_RATIO_EXTREME = 0.80  # 클론 극단 상태(내성 ≤ 15)면 80%
CLONE_EXTREME_THRESHOLD = 15.0
NPC_RECOVERY_PER_DAY = 3.0      # 차분한 NPC와 어울림 → 하루 +3
STRONG_EMOTION_GAP = 30.0       # 두 감정차 ≥ 30이면
STRONG_EMOTION_MULT = 1.5       # 강한 쪽 영향 ×1.5


# --------------------------------------------------------------------------- #
# 5) 확률 외란 & 뉴스 톤 반응 §11.5.5
# --------------------------------------------------------------------------- #
DISTURBANCE_PROB = 0.20             # 일과 중 확률 외란 발생 20%/일
DISTURBANCE_SIZE_RANGE = (2.0, 4.0)  # 크기 ±2~4 (작게)
NEWS_TONE_DELTA = -6.0             # 뉴스 톤 기본 자극(해당 톤 민감 클론) → 내성 −6
NEWS_TONE_REVERSE = 3.0            # 역행형 클론("줍줍") → 내성 +3
NEWS_COEF_RANGE = (0.5, 1.5)       # 뉴스 톤 반응 계수(인터뷰 산출) 곱 범위
SIGNATURE_MULT_RANGE = (2.0, 3.0)   # 시그니처 드라마 = 일반 뉴스의 2~3배 강도
