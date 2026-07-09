"use client";

import { Building2, Coins, Flame, Banknote, Wallet, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { CATEGORIES, CATEGORY_LABEL, Category, TickerRow } from "@/lib/emoApi";
import PixelPanel from "@/components/pixel/PixelPanel";

// T-11/T-30 — 포트폴리오 다자산 보유 패널. 카테고리별 보유액·비중(스테이블·현금 분리).
const ICON: Record<Category, typeof Building2> = {
  large_stable: Building2, mid_alt: Coins, meme: Flame, stable: Banknote, cash: Wallet,
};
const COLOR: Record<Category, string> = {
  large_stable: "bg-sky-500", mid_alt: "bg-indigo-500", meme: "bg-rose-500",
  stable: "bg-emerald-500", cash: "bg-slate-500",
};
const TEXT: Record<Category, string> = {
  large_stable: "text-sky-600", mid_alt: "text-indigo-600", meme: "text-rose-600",
  stable: "text-emerald-600", cash: "text-slate-600",
};

export default function PortfolioPanel({
  holdings, ticker, className = "",
}: { holdings: Record<string, number>; ticker?: TickerRow[]; className?: string }) {
  const total = CATEGORIES.reduce((s, c) => s + (holdings[c] ?? 0), 0);
  // v3 §B — 카테고리 → ticker 행(있으면 종목별 index 미니 현황판 표시, 없으면 구버전 폴백·I6).
  const tickerByCat: Record<string, TickerRow> = {};
  (ticker ?? []).forEach((row) => { tickerByCat[row.category] = row; });
  return (
    <PixelPanel tone="cloud" className={`p-4 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-extrabold">포트폴리오</h2>
        <span className="text-[11px] font-bold">{Math.round(total).toLocaleString()}</span>
      </div>
      <div className="flex flex-col gap-2">
        {CATEGORIES.map((cat: Category) => {
          const v = holdings[cat] ?? 0;
          const pct = total > 0 ? (v / total) * 100 : 0;
          const Icon = ICON[cat];
          const row = tickerByCat[cat];
          return (
            <div key={cat} className="flex flex-col gap-1">
              <div className="flex items-center gap-2 text-[11px]">
                <Icon className={`w-4 h-4 shrink-0 ${TEXT[cat]}`} aria-hidden />
                <span className="w-16 shrink-0 text-pixel-muted">{CATEGORY_LABEL[cat]}</span>
                <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden border border-black/10">
                  <div className={`h-full ${COLOR[cat]} transition-all duration-500`} style={{ width: `${pct}%` }} />
                </div>
                <span className="w-9 text-right tabular-nums">{Math.round(pct)}%</span>
                <span className="w-14 text-right font-bold tabular-nums">{Math.round(v).toLocaleString()}</span>
              </div>
              {row && (
                <div className="flex items-center gap-1 pl-6 text-[10px] text-pixel-muted">
                  <span>{row.symbol}</span>
                  <span className="tabular-nums">지수 {Math.round(row.index)}</span>
                  <span className={`inline-flex items-center gap-0.5 font-bold tabular-nums ${row.day_pct > 0 ? "text-rose-600" : row.day_pct < 0 ? "text-sky-600" : "text-pixel-muted"}`}>
                    {row.day_pct > 0 ? <TrendingUp className="w-3 h-3" /> : row.day_pct < 0 ? <TrendingDown className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
                    {row.day_pct > 0 ? "+" : ""}{row.day_pct.toFixed(1)}%
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </PixelPanel>
  );
}
