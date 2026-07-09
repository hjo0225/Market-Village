"""§6.1/6.3 고정 운명선 (블라인드 과거 데이터) 로더.

운명선 = 30일 OHLC 시계열, 지수정규화(첫날 종가=100). 종목명·시기는 `_meta_*`에만
보관(플레이어 비공개). 4카테고리(대형안정/중견알트/밈/스테이블). 회차가 바뀌어도
동일(기둥3 통제변인 — "같은 시험지").

가격(A, §6.4)은 운명선 90%고정 + 2층 출렁임 10%(§6.3). `apply_wobble`이 에이전트
매매압력을 ±10%로 클램프해 90% 고정을 보장한다. 클론 포트폴리오(B)는 별개다.

시드는 로컬에서 1회 박제(`tools/seed_market_village.py`). 빌드 환경에선 api.upbit.com
차단 → 오프라인 합성 시드(`--offline`)를 커밋해 자율 루프가 막히지 않게 한다.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

SEED_PATH = Path(__file__).resolve().parent / "data" / "market_seed.json"

CATEGORIES = ("large_stable", "mid_alt", "meme", "stable")


class FateLine:
    """로드된 운명선에 대한 읽기 전용 뷰."""

    def __init__(self, data: dict) -> None:
        self._data = data
        self.days: int = int(data.get("days", 0))

    def _series(self, cat: str) -> dict | None:
        return self._data.get("categories", {}).get(cat)

    def categories(self) -> list[str]:
        return list(self._data.get("categories", {}).keys())

    def day_ohlc(self, cat: str, day: int) -> tuple[float, float, float, float] | None:
        s = self._series(cat)
        if not s:
            return None
        ohlc = s.get("ohlc", [])
        if day < 0 or day >= len(ohlc):
            return None
        o, h, l, c = ohlc[day]
        return (float(o), float(h), float(l), float(c))

    def change_rate(self, cat: str, day: int) -> float:
        """전일 종가 대비 변화율(%). 첫날·미스는 0.0."""
        if day <= 0:
            return 0.0
        prev = self.day_ohlc(cat, day - 1)
        cur = self.day_ohlc(cat, day)
        if prev is None or cur is None:
            return 0.0
        prev_close = prev[3]
        if prev_close == 0:
            return 0.0
        return (cur[3] - prev_close) / prev_close * 100.0

    def swing(self, cat: str) -> float:
        """종가 최대−최소 (카테고리 변동성 프록시)."""
        s = self._series(cat)
        if not s:
            return 0.0
        closes = [row[3] for row in s.get("ohlc", [])]
        return (max(closes) - min(closes)) if closes else 0.0

    def reveal(self) -> list[dict]:
        """T-49c/v3 §B — 엔딩 후 블라인드 해제: 각 카테고리의 실제 종목·시기
        (`_meta_origin`). 플레이 중엔 절대 노출 금지(관찰 오염) — 게임 종료
        리포트에서만 호출한다. `_meta_origin` = "upbit:KRW-DOGE:2021-04-20 00:00:00".

        v3 §B — 설계 전환: 종목명은 카탈로그(coins.py)로 이미 플레이 중 공개돼
        있으므로, 엔딩 리빌의 핵심은 **"언제였는지"**(period)다. symbol/name도
        계속 포함하지만(프론트가 재구성할 수 있게), `period`("20XX년 X월")를
        센터피스로 추가한다."""
        _coin = {"BTC": "비트코인", "XRP": "리플", "DOGE": "도지코인",
                 "USDT": "테더", "ETH": "이더리움"}
        out: list[dict] = []
        for cat, info in self._data.get("categories", {}).items():
            parts = str(info.get("_meta_origin", "")).split(":")
            symbol = parts[1].replace("KRW-", "") if len(parts) > 1 else ""
            date = parts[2][:10] if len(parts) > 2 else ""
            period = ""
            if len(date) >= 7:   # "YYYY-MM-DD" → "YYYY년 M월"
                year, month = date[:4], date[5:7]
                period = f"{year}년 {int(month)}월"
            out.append({"category": cat, "symbol": symbol,
                        "name": _coin.get(symbol, symbol), "date": date,
                        "period": period})
        return out

    def public_view(self) -> dict[str, dict]:
        """플레이어에게 보이는 뷰 — `_meta_*` 제거(블라인드 §6.1)."""
        return {
            cat: {k: v for k, v in info.items() if not k.startswith("_meta")}
            for cat, info in self._data.get("categories", {}).items()
        }


@lru_cache(maxsize=2)
def _load_raw(path_str: str) -> dict:
    with open(path_str, encoding="utf-8") as f:
        return json.load(f)


def load_fate_line(path: Path | None = None) -> FateLine:
    return FateLine(_load_raw(str(path or SEED_PATH)))


def apply_wobble(base_price: float, agent_pressure: float) -> float:
    """§6.3 2층 — 운명선 위에 에이전트 매매의 얇은 출렁임. ±10% 하드클램프."""
    pressure = max(-0.10, min(0.10, agent_pressure))
    return base_price * (1.0 + pressure)


# 심볼 → 4카테고리(§6.2). universe 8섹터를 우리 4부류로 축약(SEED_GUIDE).
_SYMBOL_CATEGORY = {
    "BTC": "large_stable", "ETH": "large_stable",
    "SOL": "mid_alt", "ADA": "mid_alt", "LINK": "mid_alt",
    "DOT": "mid_alt", "ATOM": "mid_alt", "XRP": "mid_alt",
    "DOGE": "meme", "PEPE": "meme", "WIF": "meme", "BONK": "meme", "SHIB": "meme",
    "USDT": "stable", "USDC": "stable", "DAI": "stable",
}


def category_for_symbol(symbol: str) -> str:
    """심볼을 4카테고리로 매핑. 미지의 심볼은 중견 알트로 폴백."""
    return _SYMBOL_CATEGORY.get((symbol or "").upper(), "mid_alt")


def hybrid_price(start_price: float, fate_index: float, agent_pressure: float) -> float:
    """D-B 하이브리드 — 운명선 90% 고정(모양) + 출렁임 10%(질감).

    base = 시작가 × (운명선지수/100)  ← 운명선이 가격의 모양을 결정(고정).
    price = apply_wobble(base, 에이전트 압력)  ← ±10% 출렁임만 더함.
    가격은 음수가 되지 않는다.
    """
    base = start_price * fate_index / 100.0
    return max(0.0, apply_wobble(base, agent_pressure))
