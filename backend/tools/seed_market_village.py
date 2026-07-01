"""§6.1.1 운명선 시드 생성기 — 로컬에서 1회 박제.

두 경로:
  build --offline   결정론 합성 운명선(네트워크 무의존). 자율/CI용 폴백.
  build (실데이터)   업비트 일봉 API `GET /v1/candles/days`로 실제 30일 OHLC 박제.
                     api.upbit.com이 차단된 빌드 환경에서는 못 돌린다(로컬 전용).

산출물: `sim/data/market_seed.json` — 4카테고리×30일 OHLC, 지수정규화(첫날 종가=100),
실종목·시기는 `_meta_*`에만. 이 운명선이 곧 고정 통제 변인(기둥3).

오프라인 합성은 카테고리 성격을 SEED_GUIDE대로 빚는다:
  stable(횡보) < large_stable(완만+얕은딥) < mid_alt(급등후되돌림 G1) < meme(폭등후폭락 M1+F1)
6함정 시험을 위해 meme에 단일봉 +22%(M1)·−18%(F1)를 명시 주입한다.
"""

from __future__ import annotations

import argparse
import json
import random
import urllib.parse
import urllib.request
from pathlib import Path

OUT_PATH = Path(__file__).resolve().parent.parent / "sim" / "data" / "market_seed.json"
DAYS = 30
SEED = 42
# 실데이터 기본 조회 종료 시점(블라인드용 — "지금"이 아닌 과거 한 시점으로 고정해
# 재실행해도 결정론). 카테고리 성격에 맞는 실제 역사적 급등락 구간을 골랐다(임의의
# 최근 한 달은 변동성이 너무 잔잔해 함정 임계값 ±15~20%가 안 터짐 — 실측 후 교체).
DEFAULT_TO = "2024-07-01 00:00:00"
_MARKET_FOR_CATEGORY = {
    "large_stable": ("KRW-BTC", "2024-07-01 00:00:00"),   # 완만한 표류+얕은 조정
    "mid_alt": ("KRW-XRP", "2023-07-14 00:00:00"),        # 2023 SEC 판결 펌프(+68.6%)→되돌림, G1
    "meme": ("KRW-DOGE", "2021-04-20 00:00:00"),          # 2021 급등 전조(+104.8%)+급락(−23%), F1/M1
    "stable": ("KRW-USDT", "2025-12-23 00:00:00"),        # 실측 최저변동 30일(스왑1.3%), 피난처
}


def _closes_from_returns(returns: list[float]) -> list[float]:
    """일간 수익률 → 종가(첫날 100 정규화)."""
    closes = [100.0]
    for r in returns[1:]:
        closes.append(closes[-1] * (1.0 + r))
    # 첫날 종가를 정확히 100으로 (정규화 불변식 §6.1)
    scale = 100.0 / closes[0]
    return [round(c * scale, 4) for c in closes]


def _category_returns(cat: str, rng: random.Random) -> list[float]:
    """카테고리별 성격을 빚는 결정론 일간 수익률(첫날 0)."""
    r = [0.0] * DAYS
    if cat == "stable":
        for d in range(1, DAYS):
            r[d] = rng.gauss(0.0, 0.001)          # 거의 횡보(피난처)
    elif cat == "large_stable":
        for d in range(1, DAYS):
            r[d] = rng.gauss(0.0008, 0.010)        # 완만한 표류
        r[14] -= 0.06                              # 얕은 조정(닻)
    elif cat == "mid_alt":
        for d in range(1, DAYS):
            if d <= 12:
                r[d] = 0.022 + rng.gauss(0.0, 0.010)   # 급등 구간
            elif d <= 22:
                r[d] = -0.017 + rng.gauss(0.0, 0.010)  # 되돌림(익절거부 G1 유혹)
            else:
                r[d] = rng.gauss(0.0, 0.008)
    elif cat == "meme":
        for d in range(1, DAYS):
            r[d] = rng.gauss(0.006, 0.030)          # 군중심리 변동
        r[6] = 0.22                                 # 단일봉 폭등 → M1 추격
        r[20] = -0.18                               # 단일봉 폭락 → F1 패닉
    else:
        raise ValueError(f"unknown category: {cat}")
    return r


def _ohlc_from_closes(closes: list[float], rng: random.Random) -> list[list[float]]:
    """종가 시계열 → 일별 OHLC. 불변식 low ≤ open/close ≤ high."""
    rows: list[list[float]] = []
    for d, c in enumerate(closes):
        o = closes[d - 1] if d > 0 else c
        hi_base = max(o, c)
        lo_base = min(o, c)
        intraday = abs(rng.gauss(0.0, 0.01)) + 0.002   # 양수 일중 변동폭
        h = round(hi_base * (1.0 + intraday), 4)
        l = round(lo_base * (1.0 - intraday), 4)
        rows.append([round(o, 4), h, l, round(c, 4)])
    # 첫날 종가는 정확히 100
    rows[0][3] = 100.0
    rows[0][0] = 100.0
    if rows[0][1] < 100.0:
        rows[0][1] = 100.0
    if rows[0][2] > 100.0:
        rows[0][2] = 100.0
    return rows


_LABELS = {
    "large_stable": "대형 안정형",
    "mid_alt": "중견 알트형",
    "meme": "밈형",
    "stable": "스테이블/현금성",
}
_META = {
    "large_stable": "offline-synthetic / 완만+얕은딥",
    "mid_alt": "offline-synthetic / 급등후되돌림(G1)",
    "meme": "offline-synthetic / 폭등(M1)후폭락(F1)",
    "stable": "offline-synthetic / 횡보(피난처)",
}


def build_offline(out: Path) -> dict:
    rng = random.Random(SEED)
    cats: dict[str, dict] = {}
    for cat in ("large_stable", "mid_alt", "meme", "stable"):
        returns = _category_returns(cat, rng)
        closes = _closes_from_returns(returns)
        ohlc = _ohlc_from_closes(closes, rng)
        cats[cat] = {
            "label": _LABELS[cat],
            "ohlc": ohlc,
            "_meta_origin": _META[cat],
            "_meta_blind": True,
        }
    data = {
        "schema": "market_village_market_seed/v1",
        "days": DAYS,
        "note": "오프라인 합성 운명선(지수정규화 day1=100, 블라인드). 실데이터 박제는 로컬에서 build(실API)로 교체.",
        "categories": cats,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def _fetch_candles(market: str, count: int, to: str) -> list[dict]:
    """업비트 일봉 API — 응답은 내림차순(최신 먼저)이라 오름차순으로 뒤집어 반환."""
    qs = urllib.parse.urlencode({"market": market, "count": count, "to": to})
    url = f"https://api.upbit.com/v1/candles/days?{qs}"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return list(reversed(data))


def _normalize_ohlc(candles: list[dict]) -> list[list[float]]:
    """실제 가격 캔들 → 지수정규화 OHLC(첫날 "종가"=100, §6.1 불변식 — open 아님)."""
    base = candles[0]["trade_price"]
    scale = 100.0 / base
    rows = [
        [round(c["opening_price"] * scale, 4), round(c["high_price"] * scale, 4),
         round(c["low_price"] * scale, 4), round(c["trade_price"] * scale, 4)]
        for c in candles
    ]
    rows[0][3] = 100.0
    if rows[0][1] < 100.0:
        rows[0][1] = 100.0
    if rows[0][2] > 100.0:
        rows[0][2] = 100.0
    return rows


def build_online(out: Path) -> dict:
    """실 업비트 일봉으로 운명선 박제(로컬 전용 — api.upbit.com 접근 필요).

    카테고리별로 실제 역사적 구간이 다르다(_MARKET_FOR_CATEGORY) — 임의의 최근
    한 달은 변동성이 잔잔해 함정 임계값이 거의 안 터지므로, 실측으로 확인한 실제
    급등락 구간(또는 stable은 최저변동 구간)을 쓴다.
    """
    cats: dict[str, dict] = {}
    for cat, (market, to) in _MARKET_FOR_CATEGORY.items():
        candles = _fetch_candles(market, DAYS, to)
        cats[cat] = {
            "label": _LABELS[cat],
            "ohlc": _normalize_ohlc(candles),
            "_meta_origin": f"upbit:{market}:{to}",
            "_meta_blind": True,
        }
    data = {
        "schema": "market_village_market_seed/v1",
        "days": DAYS,
        "note": "실 업비트 일봉 운명선(지수정규화 day1=100, 블라인드). 종목·시기는 _meta에만.",
        "categories": cats,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def main() -> None:
    ap = argparse.ArgumentParser(description="Market Village 운명선 시드 생성기")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="운명선 박제")
    b.add_argument("--offline", action="store_true", help="결정론 합성(네트워크 무의존)")
    b.add_argument("--out", default=str(OUT_PATH))
    args = ap.parse_args()

    if args.cmd == "build":
        data = build_online(Path(args.out)) if not args.offline else build_offline(Path(args.out))
        cats = data["categories"]
        print(f"운명선 박제 완료 → {args.out}")
        for cat, info in cats.items():
            closes = [row[3] for row in info["ohlc"]]
            sw = max(closes) - min(closes)
            print(f"  {cat:12s} swing={sw:7.2f}  day1_close={closes[0]:.1f}")


if __name__ == "__main__":
    main()
