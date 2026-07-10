"use client";

import AdvChoiceMenu from "@/components/AdvChoiceMenu";
import { CATEGORY_LABEL } from "@/lib/emoApi";
import { TRADE_CATS } from "@/constants/emo";

export default function CoinPicker({
  action, holdings, busy, onPick, onCancel,
}: {
  action: string;
  holdings: Record<string, number> | undefined;
  busy: boolean;
  onPick: (cat: string) => void;
  onCancel: () => void;
}) {
  return (
    <div className="absolute right-2 sm:right-3 bottom-40 sm:bottom-44 z-30 flex flex-col items-stretch gap-2">
      <div className="flex items-center justify-between gap-3 bg-black/70 text-white rounded px-3 py-1">
        <span className="text-[13px] font-extrabold">
          {action === "buy" ? "어떤 코인을 매수할까?" : "어떤 코인을 매도할까?"}
        </span>
        <button type="button" onClick={onCancel} className="text-[12px] font-bold text-white/70 hover:text-white underline shrink-0">
          ← 다시 고르기
        </button>
      </div>
      <AdvChoiceMenu
        tone="board"
        busy={busy}
        onChoose={onPick}
        choices={TRADE_CATS.map((c) => ({
          id: c,
          label: `${CATEGORY_LABEL[c]} · ${Math.round(holdings?.[c] ?? 0).toLocaleString()}원`,
        }))}
      />
    </div>
  );
}
