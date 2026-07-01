"use client";

import { CloneStats, STAT_LABELS } from "@/lib/api";
import PixelPanel from "@/components/pixel/PixelPanel";

export default function StatsPanel({
  stats, className = "", showTitle = true,
}: { stats: CloneStats; className?: string; showTitle?: boolean }) {
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
    </PixelPanel>
  );
}
