"use client";

import { TrendingUp, TrendingDown, Minus, Clock } from "lucide-react";
import { TickerRow } from "@/lib/emoApi";
import Term from "@/components/Term";

// v3 §B — 헤더 아래 얇은 시세 현황판. 코인 심볼 + 오늘 % (상승 rose / 하락 sky,
// 기존 델타 색상 컨벤션과 동일). ticker가 없으면(구버전 폴백) 렌더 안 함(I6, 호출부 가드).
// §2.1 — "지수"는 여기 한 번만 용어 설명(각 행마다 반복하지 않음, 밑줄 범벅 금지).
// preOpen(첫날·정산 전): 블라인드 마켓 원칙(P2 미래 누출 금지)상 오늘 시세를 선택 전엔 안
// 흘려서 %가 전부 0이다. 그 0.0%가 "데이터 없음"처럼 보이는 오해를 막으려 '개장 전'으로 표시
// (첫 장은 정산에 공개). day 2부턴 정상 %.
export default function TickerBar({ ticker, preOpen = false, className = "" }: { ticker: TickerRow[]; preOpen?: boolean; className?: string }) {
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
            {preOpen ? (
              <span className="inline-flex items-center gap-0.5 text-pixel-muted">
                <Clock className="w-3 h-3" />개장 전
              </span>
            ) : (
              <span className={`inline-flex items-center gap-0.5 tabular-nums ${up ? "text-rose-600" : down ? "text-sky-600" : "text-pixel-muted"}`}>
                {up ? <TrendingUp className="w-3 h-3" /> : down ? <TrendingDown className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
                {up ? "+" : ""}{row.day_pct.toFixed(1)}%
              </span>
            )}
          </span>
        );
      })}
      {preOpen && (
        <span className="text-[10px] text-pixel-muted shrink-0 italic">첫 장은 오늘 밤 정산에 공개돼요</span>
      )}
    </div>
  );
}
