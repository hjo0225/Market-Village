#!/usr/bin/env python3
"""
upbit_stream.py  —  universe.json 종목들의
 (1) REST 현재가 스냅샷 1회 출력
 (2) WebSocket 현재가(ticker) 실시간 스트림 + 섹터별 cap-weighted 등락률 롤업

deps:  pip install requests websockets
사용:  python upbit_stream.py            # 스냅샷 후 스트림
       python upbit_stream.py --snapshot # 스냅샷만

주의: 브라우저(Origin 헤더)에서 직접 붙으면 WS가 초당 5회로 throttle 됨.
      이 스크립트는 백엔드(Origin 없음)에서 도는 걸 전제로 한다. 프론트엔는
      이 서버가 받은 데이터를 자체 WS/SSE 로 fan-out 하는 구조 권장.
"""

import os
import sys
import json
import time
import uuid
import asyncio
from collections import defaultdict

import requests

# websockets 는 (2) WS 실시간 스트림에서만 쓰는 post-MVP 옵션 의존성이다.
# MVP 경로(REST 스냅샷 / universe 로더 / listup import)가 이 패키지 없이도
# 돌도록 모듈 최상단이 아니라 stream() 안에서 지연 import 한다.

UPBIT_REST = "https://api.upbit.com/v1"
UPBIT_WS = "wss://api.upbit.com/websocket/v1"

HERE = os.path.dirname(os.path.abspath(__file__))
UNIVERSE_PATH = os.path.join(HERE, "universe.json")


def load_universe():
    with open(UNIVERSE_PATH, encoding="utf-8") as f:
        u = json.load(f)
    markets = u["markets"]
    code2sector, code2weight = {}, {}
    for sector, items in u["sectors"].items():
        for it in items:
            code2sector[it["market"]] = sector
            code2weight[it["market"]] = it["weight"]
    return markets, code2sector, code2weight


# ───────────────────────── REST 스냅샷 ─────────────────────────
def snapshot(markets, code2sector):
    """GET /v1/ticker — 현재 시세 한 번에."""
    r = requests.get(f"{UPBIT_REST}/ticker",
                     params={"markets": ",".join(markets)}, timeout=10)
    r.raise_for_status()
    rows = {d["market"]: d for d in r.json()}

    print(f"\n{'섹터':14s} {'종목':10s} {'현재가':>16s} {'전일대비':>9s} {'24h거래대금':>16s}")
    print("-" * 72)
    by_sector = defaultdict(list)
    for mk in markets:
        by_sector[code2sector.get(mk, "?")].append(mk)
    for sector in sorted(by_sector):
        for mk in by_sector[sector]:
            d = rows.get(mk)
            if not d:
                continue
            price = d["trade_price"]
            chg = d["signed_change_rate"] * 100
            vol = d["acc_trade_price_24h"] / 1e8  # 억원
            print(f"{sector:14s} {mk.split('-')[1]:10s} "
                  f"{price:>16,.4g} {chg:>+8.2f}% {vol:>14,.0f}억")
    return rows


# ───────────────────────── WS 스트림 ─────────────────────────
def build_subscribe(markets):
    """업비트 WS 요청 메세지: [{ticket}, {type:ticker, codes:[...]}, {format}]"""
    return json.dumps([
        {"ticket": str(uuid.uuid4())},
        {"type": "ticker", "codes": markets},  # 코드는 대문자여야 함
        {"format": "DEFAULT"},
    ])


def sector_rollup(latest, code2sector, code2weight):
    """섹터별 cap-weighted 등락률 + breadth, 그리고 BTC 대비 상대강도."""
    agg = defaultdict(lambda: {"wret": 0.0, "wsum": 0.0, "up": 0, "n": 0})
    for code, scr in latest.items():
        s = code2sector.get(code)
        if s is None:
            continue
        w = code2weight.get(code, 0.0)
        a = agg[s]
        a["wret"] += w * scr
        a["wsum"] += w
        a["up"] += 1 if scr > 0 else 0
        a["n"] += 1
    out = {}
    for s, a in agg.items():
        capw = (a["wret"] / a["wsum"]) if a["wsum"] else 0.0
        out[s] = {"capw": capw, "breadth": a["up"] / a["n"] if a["n"] else 0.0, "n": a["n"]}
    btc = latest.get("KRW-BTC", 0.0)  # 시장 베타 프록시(간이). 정밀히는 히스토리로 β 추정.
    for s in out:
        out[s]["vs_btc"] = out[s]["capw"] - btc
    return out


async def stream(markets, code2sector, code2weight, print_every=2.0):
    import websockets  # post-MVP 옵션: WS 스트림 쓸 때만 필요

    latest = {}  # code -> signed_change_rate
    last_print = 0.0
    sub = build_subscribe(markets)

    print(f"\nWS 연결 → {len(markets)}종목 구독 (Ctrl+C 종료)\n")
    async for ws in websockets.connect(UPBIT_WS, ping_interval=60, ping_timeout=30,
                                       max_size=2 ** 22):
        try:
            await ws.send(sub)
            async for raw in ws:
                msg = json.loads(raw)  # 업비트는 바이너리 프레임으로 보냄(json.loads ok)
                if msg.get("type") != "ticker":
                    continue
                latest[msg["code"]] = msg["signed_change_rate"]

                now = time.monotonic()
                if now - last_print >= print_every:
                    last_print = now
                    roll = sector_rollup(latest, code2sector, code2weight)
                    print(f"\n[{time.strftime('%H:%M:%S')}] 섹터 동향 "
                          f"(cap-weighted 등락 / breadth / BTC대비)")
                    for s in sorted(roll, key=lambda x: roll[x]["capw"], reverse=True):
                        v = roll[s]
                        print(f"  {s:14s} {v['capw']*100:>+6.2f}%  "
                              f"breadth {v['breadth']*100:>3.0f}%  "
                              f"vsBTC {v['vs_btc']*100:>+5.2f}%  (n={v['n']})")
        except websockets.ConnectionClosed:
            print("[reconnect] WS 재연결 …", file=sys.stderr)
            continue


def main():
    markets, code2sector, code2weight = load_universe()
    print(f"universe.json 로드: {len(markets)}종목")
    snapshot(markets, code2sector)
    if "--snapshot" in sys.argv:
        return
    try:
        asyncio.run(stream(markets, code2sector, code2weight))
    except KeyboardInterrupt:
        print("\n종료.")


if __name__ == "__main__":
    main()
