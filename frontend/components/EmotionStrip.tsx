"use client";

import { AXES, AXIS_LABEL, Axis, Emotion } from "@/lib/emoApi";

// T-31/T-35 — 상단 상시 노출용 슬림 감정 4축 스트립(대화 중에도 감정 체감).
// 값이 바뀌면 델타 플래시(T-35)는 상위에서 key로 트리거.
const COLOR: Record<Axis, string> = {
  fear: "bg-sky-500", greed: "bg-amber-500", anxiety: "bg-violet-500", restlessness: "bg-teal-500", composure: "bg-green-500",
};

export default function EmotionStrip({ emotion, flash }: { emotion: Emotion; flash?: Axis | null }) {
  return (
    <div className="flex items-center gap-2 sm:gap-3">
      {AXES.map((axis: Axis) => {
        const v = Math.round(emotion[axis] ?? 0);
        return (
          <div key={axis} className="flex items-center gap-1 min-w-0">
            <span className="text-[10px] text-pixel-muted shrink-0">{AXIS_LABEL[axis]}</span>
            <div className="w-10 sm:w-14 h-2 bg-slate-200 rounded-full overflow-hidden border border-black/10">
              <div
                className={`h-full ${COLOR[axis]} transition-all duration-500 ${flash === axis ? "animate-pulse" : ""}`}
                style={{ width: `${v}%` }}
              />
            </div>
            <span className={`text-[10px] font-bold tabular-nums w-5 text-right ${flash === axis ? "text-black" : ""}`}>{v}</span>
          </div>
        );
      })}
    </div>
  );
}
