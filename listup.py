#!/usr/bin/env python3
"""
listup.py  —  Market Village "종목 분류 및 리스트업 + 업비트 api" 산출물

역할:
  빌드타임에 고정된 universe.json(8섹터/cap-weighted 유니버스)을 읽어,
  업비트에서 한글명 + 초기 시세(initial price)를 1회 받아 합쳐서
  프론트/백엔드가 그대로 쓰는 default_assets.json 을 만든다.

이건 시뮬레이션의 '입력'이다. FE 의 DEFAULT_ASSETS / Asset 자리를 실제 데이터로 채운다.
  - frontend/constants/agentProfiles.ts  →  DEFAULT_ASSETS = [{ symbol, name, price }]
  - frontend/mock_data/market.ts         →  Asset = { symbol, name, price, change24h, volume, priceHistory }

아키텍처(불변식):
  - freeze_universe.py = 빌드타임 1회 → universe.json. (런타임 호출 X, 여기서도 호출 안 함)
  - upbit_stream.py    = universe.json 읽기만. 검증된 함수/상수를 import 해서 재사용한다.
  - 섹터 멤버십·가중치는 universe.json 에 frozen. 여기서 재추출/재계산 안 한다.

MVP 범위: "initial price 실제 upbit 으로"(O) / "실시간 가격 API"(X).
  → 초기가는 REST 1회 스냅샷. 실시간 WS 스트림(upbit_stream)은 post-MVP 옵션.

사용:
  python freeze_universe.py   # universe.json 없으면 먼저(빌드타임 1회)
  python listup.py            # default_assets.json 생성 + 섹터별 요약 출력

BE/다른 모듈에서 import:
  from listup import get_assets        # 시세 포함 종목 리스트(파일 안 쓰고 반환)
  from listup import get_default_assets  # {symbol,name,price} 만 (FE DEFAULT_ASSETS 매핑)
"""

import os
import sys
import json
from datetime import datetime, timezone

import requests

import upbit_stream as us  # 검증된 상수/로더 재사용 (UPBIT_REST, UNIVERSE_PATH, load_universe)

HERE = os.path.dirname(os.path.abspath(__file__))
UNIVERSE_PATH = us.UNIVERSE_PATH
OUT_PATH = os.path.join(HERE, "default_assets.json")
UPBIT_REST = us.UPBIT_REST


def _load_universe_full():
    """universe.json 원본(섹터/가중치/심볼 포함)을 읽는다. 읽기 전용."""
    if not os.path.exists(UNIVERSE_PATH):
        raise SystemExit(
            "universe.json 이 없습니다. 먼저 빌드타임 1회 실행:\n    python freeze_universe.py"
        )
    with open(UNIVERSE_PATH, encoding="utf-8") as f:
        return json.load(f)


def fetch_korean_names(markets):
    """업비트 /market/all 에서 한글명 매핑. universe.json 엔 한글명이 없어 여기서 보강."""
    r = requests.get(f"{UPBIT_REST}/market/all",
                     params={"is_details": "false"}, timeout=10)
    r.raise_for_status()
    return {m["market"]: m.get("korean_name", "") for m in r.json()}


def fetch_initial_prices(markets):
    """업비트 /ticker 초기 시세 1회 스냅샷. {market: ticker_dict}.

    (upbit_stream.snapshot 과 동일한 REST 엔드포인트지만, 표 출력 없이 조용히 받는다.)
    IP당 초당 10/분당 600 제약 안에서 단발 호출.
    """
    r = requests.get(f"{UPBIT_REST}/ticker",
                     params={"markets": ",".join(markets)}, timeout=10)
    r.raise_for_status()
    return {d["market"]: d for d in r.json()}


def get_assets(with_prices=True):
    """섹터 분류 + 한글명 + (옵션)초기 시세를 합친 종목 리스트.

    반환 원소: {symbol, name, market, sector, weight, coingecko_id,
                price, change24h, volume}
    change24h 는 % (signed_change_rate 비율 × 100), volume 은 24h 누적 거래대금(KRW).
    """
    u = _load_universe_full()
    markets = u["markets"]
    names = fetch_korean_names(markets)
    rows = fetch_initial_prices(markets) if with_prices else {}

    # universe 종목이 업비트에서 사라지면(상장폐지 등) ticker 응답에서 빠진다.
    # 이때 price=None 이 FE(price: number) 계약을 깨므로, 조용히 넘기지 않고 경고한다.
    if with_prices:
        gone = [m for m in markets if m not in rows]
        if gone:
            print(f"[listup] 경고: 업비트 ticker 미응답 {len(gone)}종목 {gone} "
                  f"— 상장폐지 가능성. freeze_universe.py 재실행 검토.", file=sys.stderr)

    assets = []
    for sector, items in u["sectors"].items():
        for it in items:
            mk = it["market"]
            d = rows.get(mk, {})
            assets.append({
                "symbol": it["symbol"],
                "name": names.get(mk) or it["symbol"],
                "market": mk,
                "sector": sector,
                "weight": it["weight"],
                "coingecko_id": it.get("coingecko_id"),
                "price": d.get("trade_price"),
                "change24h": round(d.get("signed_change_rate", 0.0) * 100, 2),
                "volume": d.get("acc_trade_price_24h", 0.0),
            })
    return assets


def get_default_assets():
    """FE DEFAULT_ASSETS 매핑용 최소 형태: [{symbol, name, price}]."""
    return [{"symbol": a["symbol"], "name": a["name"], "price": a["price"]}
            for a in get_assets(with_prices=True)]


def build_artifact():
    """default_assets.json 산출물(메타 + 섹터목록 + 종목)을 만들어 반환."""
    u = _load_universe_full()
    assets = get_assets(with_prices=True)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "vs_currency": u.get("vs_currency", "krw"),
        "weighting": u.get("weighting"),
        "universe_generated_at": u.get("generated_at"),
        "count": len(assets),
        "sectors": list(u["sectors"].keys()),
        "assets": assets,
    }


def main():
    artifact = build_artifact()
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(artifact, f, ensure_ascii=False, indent=2)

    print(f"✓ {artifact['count']}종목 / {len(artifact['sectors'])}섹터 → {OUT_PATH}")
    by_sector = {}
    for a in artifact["assets"]:
        by_sector.setdefault(a["sector"], []).append(a)
    for sector, items in by_sector.items():
        head = ", ".join(
            f"{it['name']}({it['symbol']} {it['change24h']:+.2f}%)" for it in items
        )
        print(f"  {sector:13s}: {head}")


if __name__ == "__main__":
    main()
