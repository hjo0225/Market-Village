import React from "react";
import { TickerBar } from "market-village-frontend";

// 헤더 아래 얇은 시세 현황판 — 카테고리별 심볼 + 오늘 % (상승 rose / 하락 sky / 보합 회색).
// 심볼은 market_seed.json의 실제 블라인드 자산: BTC(대형 안정형)·XRP(중견 알트형)·
// DOGE(밈형)·USDT(스테이블). index는 시작=100 누적곱.

const row = (category: string, symbol: string, name: string, day_pct: number, index: number) => ({
  category,
  symbol,
  name,
  day_pct,
  index,
});

// 혼조 장세 — 밈만 급등, 중견 알트는 하락, 스테이블 보합.
export const MixedDay = () => (
  <div style={{ maxWidth: 560, padding: 16 }}>
    <TickerBar
      ticker={[
        row("large_stable", "BTC", "비트코인", 2.3, 104.2),
        row("mid_alt", "XRP", "리플", -1.4, 97.1),
        row("meme", "DOGE", "도지코인", 8.7, 131.8),
        row("stable", "USDT", "테더", 0.0, 100.0),
      ]}
    />
  </div>
);

// 급락일 — 전 카테고리 하락(스테이블만 소폭 방어).
export const CrashDay = () => (
  <div style={{ maxWidth: 560, padding: 16 }}>
    <TickerBar
      ticker={[
        row("large_stable", "BTC", "비트코인", -6.2, 88.4),
        row("mid_alt", "XRP", "리플", -9.8, 79.3),
        row("meme", "DOGE", "도지코인", -18.4, 64.1),
        row("stable", "USDT", "테더", 0.1, 100.1),
      ]}
    />
  </div>
);

// 첫날(Day 0) — 아직 정산 전이라 전부 0.0% 보합(Minus 아이콘).
export const DayZero = () => (
  <div style={{ maxWidth: 560, padding: 16 }}>
    <TickerBar
      ticker={[
        row("large_stable", "BTC", "비트코인", 0.0, 100.0),
        row("mid_alt", "XRP", "리플", 0.0, 100.0),
        row("meme", "DOGE", "도지코인", 0.0, 100.0),
        row("stable", "USDT", "테더", 0.0, 100.0),
      ]}
    />
  </div>
);
