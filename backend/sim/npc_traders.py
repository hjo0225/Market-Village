"""§13.7/T-245 — NPC 가상 수익률(미니 리더보드). 무상태 순수 파생.

🤖 council M4/R10 (PRD_AGENT_MEMORY):
- 페르소나 **고정 규칙 × 운명선**의 순수함수 — 상태 저장 없이 day0부터 매번
  재계산한다(결정론·서버 재시작 안전·직렬화 불요).
- FateLine은 읽기 전용이므로 "NPC 매매가 가격에 영향 0"(§6.1)이 구조로 보장된다.
- 감정 상태 결합 없음 — 감정→매매는 에이전트 메모리 에픽 v2에서 R6/R8 통과 시.

규칙(§9.5.2 부호: 수치 높음=취약 — 취약할수록 충동 매매가 크고 잦다):
- 전일 대비 상승이 매수 임계(군중 동조 herd가 높을수록 낮음)를 넘으면
  현금의 일부(greed 비례)로 추격 매수.
- 하락이 매도 임계(fear가 높을수록 얕음)를 넘으면 보유의 일부(fear 비례) 투매.
- 그 외엔 관망. 시작은 현금 50 + 주식 50 상당(총 100), 수익률은 평가액 기준.
"""

from __future__ import annotations

from .fate_line import FateLine

_START_CASH = 50.0
_START_STOCK_VALUE = 50.0


def npc_action_on_day(persona: dict, fl: FateLine, category: str, day: int) -> str | None:
    """T-256 — 그날 이 NPC의 매매 판정("buy"/"sell"/None). 순수·결정론.

    npc_return_pct와 같은 규칙의 단일 소스 — 맵 매매 연출(💸)이 소비한다.
    """
    herd = float(persona["herd"])
    fear = float(persona["fear"])
    buy_threshold = 8.0 - 6.0 * herd            # herd .9→2.6%, .05→7.7%
    sell_threshold = -(14.0 - fear / 10.0)      # fear 85→-5.5%, 10→-13%
    chg = fl.change_rate(category, day)
    if chg >= buy_threshold:
        return "buy"
    if chg <= sell_threshold:
        return "sell"
    return None


def npc_return_pct(persona: dict, fl: FateLine, category: str, upto_day: int) -> float:
    """day0~upto_day까지 페르소나 규칙대로 산 결과 수익률(%). 순수·결정론."""
    first = fl.day_ohlc(category, 0)
    if first is None or upto_day <= 0:
        return 0.0
    price0 = first[3]
    cash = _START_CASH
    qty = _START_STOCK_VALUE / price0 if price0 else 0.0

    last_price = price0
    for day in range(1, upto_day + 1):
        ohlc = fl.day_ohlc(category, day)
        if ohlc is None:
            break
        price = ohlc[3]
        last_price = price
        action = npc_action_on_day(persona, fl, category, day)
        if action == "buy" and cash > 0:
            spend = cash * (float(persona["greed"]) / 200.0)   # greed 92 → 현금 46% 추격
            cash -= spend
            qty += spend / price if price else 0.0
        elif action == "sell" and qty > 0:
            sell = qty * (float(persona["fear"]) / 200.0)      # fear 85 → 보유 42.5% 투매
            qty -= sell
            cash += sell * price

    total = cash + qty * last_price
    initial = _START_CASH + _START_STOCK_VALUE
    return round((total - initial) / initial * 100.0, 2)
