"""player_emotion 튜닝 상수 — 단일 소스.

축 범위(T-1)와 압축 판정 임계값(T-4)을 여기 분리해 둔다.
로직 코드는 이 상수만 참조하고 값 자체를 하드코딩하지 않는다.
"""

# T-1: 4축 공통 클램프 범위.
AXIS_MIN: float = 0
AXIS_MAX: float = 100

# T-4: 감정 압축 판정 임계값.
# verdict = (greed + restlessness) - (fear + anxiety)
OVERHEAT_THRESHOLD: float = 30
WITHDRAWAL_THRESHOLD: float = -30

# T-10: 게시판 톤의 방향성 세기(센터링된 편차 × 이 값). 순합 0이라 포화 없음.
BOARD_TONE_SCALE: float = 18.0

# T-27 (PLAN-READY 4b): 감정 평형·감쇠. 매일 밤(다음 날 진입) 각 축이 평형값으로
# 일부 회귀한다 — 한 방향 강제입력(예: 반복 매수→greed)이 클램프(AXIS_MAX)까지
# 램프업하는 것을 막는 안전장치. 3칸: 감쇠율·평형·클램프(클램프는 AXIS_MIN/MAX 재사용).
EQUILIBRIUM: float = 50.0         # 평형값(중립) — 회귀 목표점
DAILY_DECAY_RATE: float = 0.15    # 하루당 (평형 - 현재)의 이 비율만큼 회귀
