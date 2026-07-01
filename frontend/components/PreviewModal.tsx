"use client";

import { useState } from "react";
import PixelModal from "@/components/pixel/PixelModal";
import PixelButton from "@/components/pixel/PixelButton";
import { api, Meetings, Picks } from "@/lib/api";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  gameId: string;
  meetings: Meetings;
  picks: Picks;
  onChanged: () => void;
}

// §9.2.1 전날밤 회피 + §9.2.1b 클론이 스스로 고른 대화 상대 노출.
export default function PreviewModal({ isOpen, onClose, gameId, meetings, picks, onChanged }: Props) {
  const [slotA, setSlotA] = useState(3);
  const [slotB, setSlotB] = useState(1);

  const rows = Object.entries(meetings);

  async function doAvoid() {
    await api.gameAvoid(gameId, slotA, slotB);
    onChanged();
  }

  return (
    <PixelModal isOpen={isOpen} onClose={onClose} title="🌙 전날밤 — 내일 마주칠 NPC" size="sm">
      {rows.length === 0 ? (
        <p className="text-sm text-pixel-muted">오늘은 마주칠 NPC가 없습니다.</p>
      ) : (
        <ul className="flex flex-col gap-2 mb-4">
          {rows.map(([slot, npcs]) => {
            const pick = picks[slot];
            const cand = npcs.length > 1 ? `${npcs.join(", ")} 중 ` : "";
            return (
              <li key={slot} className="text-sm bg-pixel-path rounded-lg px-3 py-2">
                슬롯{slot}: {cand}<b>{pick || npcs[0]}</b>와 대화
              </li>
            );
          })}
        </ul>
      )}
      <div className="border-t-2 border-black/10 pt-3">
        <p className="text-xs text-pixel-muted mb-2">일과 항목 둘을 바꿔 동선을 튼다(하나만):</p>
        <div className="flex items-center gap-2">
          <input type="number" min={1} max={8} value={slotA} onChange={(e) => setSlotA(+e.target.value)}
            className="w-14 border-2 border-black rounded-lg px-2 py-1 text-sm" />
          <span>↔</span>
          <input type="number" min={1} max={8} value={slotB} onChange={(e) => setSlotB(+e.target.value)}
            className="w-14 border-2 border-black rounded-lg px-2 py-1 text-sm" />
          <PixelButton size="sm" onClick={doAvoid}>회피</PixelButton>
        </div>
      </div>
    </PixelModal>
  );
}
