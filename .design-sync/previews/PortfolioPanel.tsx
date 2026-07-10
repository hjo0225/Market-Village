import React from "react";
import { PortfolioPanel } from "market-village-frontend";

// T-11/T-30 — 포트폴리오 다자산 보유 패널. 카테고리별 보유액·비중 바 +
// (v3 §B) 종목별 티커 미니 현황판. 심볼은 실제 게임의 블라인드 자산 매핑
// (BTC/XRP/DOGE/USDT — backend/sim/coins.py)을 그대로 사용.

const wrap: React.CSSProperties = { width: 340 };

const tickerCalm = [
  { category: "large_stable", symbol: "BTC", name: "비트코인", day_pct: 2.4, index: 118 },
  { category: "mid_alt", symbol: "XRP", name: "리플", day_pct: -1.8, index: 94 },
  { category: "meme", symbol: "DOGE", name: "도지코인", day_pct: 0.6, index: 121 },
  { category: "stable", symbol: "USDT", name: "테더", day_pct: 0.0, index: 100 },
];

const tickerSurge = [
  { category: "large_stable", symbol: "BTC", name: "비트코인", day_pct: -0.8, index: 112 },
  { category: "mid_alt", symbol: "XRP", name: "리플", day_pct: 3.1, index: 104 },
  { category: "meme", symbol: "DOGE", name: "도지코인", day_pct: 14.2, index: 187 },
  { category: "stable", symbol: "USDT", name: "테더", day_pct: 0.0, index: 100 },
];

// 균형 잡힌 포트폴리오 — 대형 안정형 중심, 리스크 비중 66%. 티커 현황판 포함.
export const BalancedWithTicker = () => (
  <div style={wrap}>
    <PortfolioPanel
      holdings={{ large_stable: 420000, mid_alt: 180000, meme: 60000, stable: 190000, cash: 150000 }}
      ticker={tickerCalm}
    />
  </div>
);

// 밈코인 몰빵 국면 — DOGE +14.2% 급등일. 리스크 비중 88%의 공격적 배분.
export const MemeHeavySurge = () => (
  <div style={wrap}>
    <PortfolioPanel
      holdings={{ large_stable: 90000, mid_alt: 160000, meme: 520000, stable: 30000, cash: 80000 }}
      ticker={tickerSurge}
    />
  </div>
);

// ticker 없음(I6 폴백) — 종목 티커 행이 숨고 카테고리 바만 남는 구버전 표시.
export const LegacyNoTicker = () => (
  <div style={wrap}>
    <PortfolioPanel
      holdings={{ large_stable: 300000, mid_alt: 150000, meme: 50000, stable: 250000, cash: 250000 }}
    />
  </div>
);
