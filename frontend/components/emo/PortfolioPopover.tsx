"use client";

import { X } from "lucide-react";
import { EmoState } from "@/lib/emoApi";
import EmotionGauge from "@/components/EmotionGauge";
import PortfolioPanel from "@/components/PortfolioPanel";

export default function PortfolioPopover({
  state, onClose,
}: {
  state: EmoState;
  onClose: () => void;
}) {
  return (
    <div className="absolute inset-0 z-20" onClick={onClose}>
      <div
        className="absolute right-2 top-12 sm:right-3 sm:top-14 w-80 max-w-[85vw] max-h-[78vh] bg-pixel-path rounded-xl border-2 border-black/25 shadow-lg p-3 overflow-y-auto flex flex-col gap-2"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-extrabold">상태</h2>
          <button onClick={onClose} aria-label="닫기"><X className="w-5 h-5" /></button>
        </div>
        <EmotionGauge emotion={state.emotion} verdict={state.verdict} />
        <PortfolioPanel holdings={state.holdings} ticker={state.ticker} />
      </div>
    </div>
  );
}
