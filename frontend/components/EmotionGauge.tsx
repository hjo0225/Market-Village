"use client";

import { ShieldAlert, TrendingUp, Waves, Activity } from "lucide-react";
import { AXES, AXIS_LABEL, Axis, Emotion } from "@/lib/emoApi";
import PixelPanel from "@/components/pixel/PixelPanel";

// T-5 · T-12 — 4축 감정 게이지. 이모지 대신 lucide 아이콘.
const ICON: Record<Axis, typeof ShieldAlert> = {
  fear: ShieldAlert, greed: TrendingUp, anxiety: Waves, restlessness: Activity,
};
const COLOR: Record<Axis, string> = {
  fear: "bg-sky-500", greed: "bg-amber-500", anxiety: "bg-violet-500", restlessness: "bg-teal-500",
};
const TEXT: Record<Axis, string> = {
  fear: "text-sky-600", greed: "text-amber-600", anxiety: "text-violet-600", restlessness: "text-teal-600",
};

export default function EmotionGauge({
  emotion, verdict, className = "",
}: { emotion: Emotion; verdict?: string; className?: string }) {
  return (
    <PixelPanel tone="cloud" className={`p-4 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-extrabold">감정</h2>
        {verdict && (
          <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-black/5">{verdict}</span>
        )}
      </div>
      <div className="flex flex-col gap-2">
        {AXES.map((axis: Axis) => {
          const v = Math.round(emotion[axis] ?? 0);
          const Icon = ICON[axis];
          return (
            <div key={axis} className="flex items-center gap-2 text-[11px]">
              <Icon className={`w-4 h-4 shrink-0 ${TEXT[axis]}`} aria-hidden />
              <span className="w-8 shrink-0 text-pixel-muted">{AXIS_LABEL[axis]}</span>
              <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden border border-black/10">
                <div className={`h-full ${COLOR[axis]} transition-all duration-500`} style={{ width: `${v}%` }} />
              </div>
              <span className="w-6 text-right font-bold">{v}</span>
            </div>
          );
        })}
      </div>
    </PixelPanel>
  );
}
