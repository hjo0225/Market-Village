"use client";

import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { TickerRow } from "@/lib/emoApi";
import Term from "@/components/Term";

// v3 §B — 헤더 아래 얇은 시세 현황판. 코인 심볼 + 오늘 % (상승 rose / 하락 sky,
// 기존 델타 색상 컨벤션과 동일). ticker가 없으면(구버전 폴백) 렌더 안 함(I6, 호출부 가드).
// §2.1 — "지수"는 여기 한 번만 용어 설명(각 행마다 반복하지 않음, 밑줄 범벅 금지).
export default function TickerBar({ ticker, className = "" }: { ticker: TickerRow[]; className?: string }) {
  if (!ticker || ticker.length === 0) return null;
  return (
    <div className={`flex items-center gap-3 overflow-x-auto ${className}`}>
      <span className="text-[10px] text-pixel-muted shrink-0"><Term term="지수" /></span>
      {ticker.map((row) => {
        const up = row.day_pct > 0;
        const down = row.day_pct < 0;
        return (
          <span key={row.category} className="inline-flex items-center gap-1 text-[11px] font-bold shrink-0">
            <span className="text-pixel-muted">{row.symbol}</span>
            <span className={`inline-flex items-center gap-0.5 tabular-nums ${up ? "text-rose-600" : down ? "text-sky-600" : "text-pixel-muted"}`}>
              {up ? <TrendingUp className="w-3 h-3" /> : down ? <TrendingDown className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
              {up ? "+" : ""}{row.day_pct.toFixed(1)}%
            </span>
          </span>
        );
      })}
    </div>
  );
}
