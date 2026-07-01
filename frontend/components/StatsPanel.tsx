"use client";

import { CATEGORY_LABELS, CloneStats, Portfolio, STAT_LABELS } from "@/lib/api";
import PixelPanel from "@/components/pixel/PixelPanel";

export default function StatsPanel({
  stats, portfolio, className = "", showTitle = true,
}: { stats: CloneStats; portfolio?: Portfolio; className?: string; showTitle?: boolean }) {
  return (
    <PixelPanel tone="cloud" className={`p-4 ${className}`}>
      {showTitle && <h2 className="text-sm font-extrabold mb-3">🪞 클론 상태</h2>}
      <div className="flex flex-col gap-1.5">
        {STAT_LABELS.map((k) => {
          const v = Math.round(stats[k] ?? 0);
          return (
            <div key={k} className="flex items-center gap-2 text-[11px]">
              <span className="w-20 shrink-0 text-pixel-muted">{k}</span>
              <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden border border-black/10">
                <div className="h-full bg-pixel-grass transition-all" style={{ width: `${v}%` }} />
              </div>
              <span className="w-6 text-right font-bold">{v}</span>
            </div>
          );
        })}
      </div>

      {portfolio && (
        <div className="mt-4 pt-3 border-t-2 border-black/10">
          <h3 className="text-xs font-extrabold mb-2">💰 포트폴리오</h3>
          <div className="flex flex-col gap-1.5">
            {portfolio.holdings.map((h) => {
              const pnlSign = h.unrealized_pnl > 0 ? "+" : "";
              const pnlColor = h.unrealized_pnl > 0 ? "text-pixel-greenText"
                : h.unrealized_pnl < 0 ? "text-pixel-danger" : "text-pixel-muted";
              return (
                <div key={h.category} className="flex items-center justify-between text-[11px] bg-pixel-path rounded-lg px-2 py-1.5">
                  <span className="font-bold">{CATEGORY_LABELS[h.category] ?? h.category}</span>
                  <span className="text-pixel-muted">{h.quantity.toFixed(2)}개 · 평단 {Math.round(h.avg_cost)}</span>
                  <span className={`font-bold ${pnlColor}`}>
                    {Math.round(h.value)} ({pnlSign}{Math.round(h.unrealized_pnl)})
                  </span>
                </div>
              );
            })}
            <div className="flex items-center justify-between text-[11px] px-2 py-1">
              <span className="text-pixel-muted">현금</span>
              <span className="font-bold">{Math.round(portfolio.cash)}</span>
            </div>
          </div>
        </div>
      )}
    </PixelPanel>
  );
}
