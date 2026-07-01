"use client";

import PixelPanel from "@/components/pixel/PixelPanel";

interface Props {
  runId?: string;
  returnPct: number;
  grade: string;
  emotionOverall: Record<string, number>;
  evaluation?: string;
}

const GRADE_ICON: Record<string, string> = {
  "고수": "🧘", "벼락부자형": "🎰", "강철멘탈형": "🛡", "호구": "😵",
};

export default function ResultCardView({ runId, returnPct, grade, emotionOverall, evaluation }: Props) {
  const up = returnPct >= 0;
  return (
    <PixelPanel tone="cloud" className="p-5 animate-pixel-pop">
      {runId && <div className="text-[11px] text-pixel-muted mb-1">회차 {runId}</div>}
      <div className="flex items-center gap-2 mb-2">
        <span className="text-2xl">{GRADE_ICON[grade] ?? "🎖"}</span>
        <span className={`text-xl font-extrabold ${up ? "text-pixel-greenText" : "text-pixel-danger"}`}>
          {up ? "+" : ""}{returnPct}%
        </span>
        <span className="px-2 py-0.5 bg-pixel-grass rounded-full text-[11px] font-bold border border-black">{grade}</span>
      </div>
      <div className="text-[11px] text-pixel-muted mb-2">
        {Object.entries(emotionOverall).map(([k, v]) => `${k} ${Math.round(v)}`).join(" · ")}
      </div>
      {evaluation && <p className="text-sm">{evaluation}</p>}
    </PixelPanel>
  );
}
