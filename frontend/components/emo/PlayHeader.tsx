"use client";

import { Users, CalendarDays, Wallet, PieChart } from "lucide-react";
import { EmoState, NPC_NAME, Axis } from "@/lib/emoApi";
import EmotionStrip from "@/components/EmotionStrip";
import TierBadge from "@/components/TierBadge";
import CoachMark from "@/components/CoachMark";

export default function PlayHeader({
  state, flashAxis, onOpenPortfolio,
}: {
  state: EmoState;
  flashAxis: Axis | null;
  onOpenPortfolio: () => void;
}) {
  return (
    <>
      <header className="shrink-0 flex items-center gap-3 flex-wrap px-1">
        <span className="text-[12px] font-extrabold">{state.clone_name}</span>
        <span className="inline-flex items-center gap-1 text-[11px] font-bold"><CalendarDays className="w-3.5 h-3.5" />Day {state.day + 1}/{state.total_days}</span>
        <span className="inline-flex items-center gap-1 text-[11px] font-bold"><Wallet className="w-3.5 h-3.5" />{Math.round(state.portfolio_value).toLocaleString()}</span>
        {state.companion && (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold"><Users className="w-3.5 h-3.5" />{NPC_NAME[state.companion] ?? state.companion}</span>
        )}
        {state.tier && <TierBadge tier={state.tier} />}
        <span className="hidden sm:block ml-auto relative">
          <EmotionStrip emotion={state.emotion} flash={flashAxis} />
          <CoachMark
            id="emotionStrip"
            text="클론의 지금 마음. 공포가 높으면 하락에 과민해져요."
            className="absolute right-0 top-full mt-2"
          />
        </span>
        <button
          onClick={onOpenPortfolio}
          className="ml-auto sm:ml-2 inline-flex items-center gap-1 text-[11px] font-bold bg-black/5 rounded px-2 py-1"
        >
          <PieChart className="w-3.5 h-3.5" />포트폴리오
        </button>
      </header>
      <div className="sm:hidden shrink-0 px-1"><EmotionStrip emotion={state.emotion} flash={flashAxis} /></div>
    </>
  );
}
