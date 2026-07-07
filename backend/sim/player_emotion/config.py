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

# T-10: 게시판 전체 톤이 노출 델타에 얹는 최대 가중(축별, 평균 톤 1.0 기준).
BOARD_TONE_SCALE: float = 6.0
