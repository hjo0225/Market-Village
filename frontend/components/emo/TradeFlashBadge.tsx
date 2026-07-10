"use client";

import { TrendingUp, TrendingDown } from "lucide-react";

export default function TradeFlashBadge({
  action, detail,
}: {
  action: "buy" | "sell";
  detail?: string;
}) {
  return (
    <div className="absolute inset-x-0 top-[16%] z-30 flex justify-center px-3 pointer-events-none">
      <div className={`rounded-xl shadow-lg px-4 py-2.5 max-w-[85vw] border-2 border-black/20 animate-pulse ${action === "buy" ? "bg-rose-600/90" : "bg-sky-600/90"}`}>
        <div className="flex items-center gap-1.5 text-[14px] font-extrabold text-white">
          {action === "buy" ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
          {action === "buy" ? "클론 매수" : "클론 매도"}
        </div>
        {detail && <div className="text-[12px] text-white/85 mt-0.5">{detail}</div>}
      </div>
    </div>
  );
}
