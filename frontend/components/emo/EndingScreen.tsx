"use client";

import * as api from "@/lib/emoApi";
import { EmoState } from "@/lib/emoApi";
import DiagnosisReport from "@/components/DiagnosisReport";
import PixelPanel from "@/components/pixel/PixelPanel";
import PixelButton from "@/components/pixel/PixelButton";

export default function EndingScreen({
  state, report, onRestart,
}: {
  state: EmoState;
  report: api.DiagnosisReport | null;
  onRestart: () => void;
}) {
  const e = state.ending!;
  return (
    <main className="min-h-screen bg-pixel-path flex items-start justify-center p-4 overflow-y-auto">
      <PixelPanel tone="cloud" className="w-full max-w-lg p-6 my-4">
        <div className="text-[11px] text-pixel-muted mb-1">{e.id} · {e.grade}</div>
        <h1 className="text-xl font-extrabold mb-4">{e.title}</h1>
        <div className="flex flex-col gap-3 text-[13px] leading-relaxed">
          {e.epilogue.map((line, i) => (
            <p key={i} className="border-l-2 border-black/10 pl-3">{line}</p>
          ))}
        </div>
        <div className="mt-5 text-[11px] text-pixel-muted flex items-center flex-wrap gap-x-1.5">
          <span>{state.clone_name} · 최종 자산 {Math.round(state.portfolio_value).toLocaleString()} · 특수이벤트 {state.special_event_count}회</span>
          {state.tier && <span className="font-bold text-black">· 최종 티어 {state.tier.icon} {state.tier.name}</span>}
        </div>

        <DiagnosisReport report={report} totalDays={state.total_days} />

        <PixelButton size="lg" className="w-full mt-6" onClick={onRestart}>
          다시 시작
        </PixelButton>
      </PixelPanel>
    </main>
  );
}
