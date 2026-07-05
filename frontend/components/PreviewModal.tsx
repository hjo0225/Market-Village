"use client";

import { useState } from "react";
import PixelModal from "@/components/pixel/PixelModal";
import PixelButton from "@/components/pixel/PixelButton";
import { api, Designated, Meetings, NPC_LABELS, NPC_ROLES, Picks } from "@/lib/api";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  gameId: string;
  meetings: Meetings;
  picks: Picks;
  designated: Designated;
  onChanged: () => void;
}

function npcName(id: string) {
  return NPC_LABELS[id] ?? id;
}

// §9.2.1 전날밤 회피 + §9.2.1b 클론이 스스로 고른 대화 상대 노출.
// T-272a — 후보가 여럿인 슬롯은 플레이어가 상대를 지정할 수 있다(사용자 결정
// 2026-07-05: 참여감 강화). 기본은 여전히 클론의 선택 — 지정은 덮어쓰기.
export default function PreviewModal({ isOpen, onClose, gameId, meetings, picks, designated, onChanged }: Props) {
  const [slotA, setSlotA] = useState(3);
  const [slotB, setSlotB] = useState(1);
  const [busy, setBusy] = useState(false);

  const rows = Object.entries(meetings);

  async function doAvoid() {
    await api.gameAvoid(gameId, slotA, slotB);
    onChanged();
  }

  async function doDesignate(slot: string, npcId: string | null) {
    setBusy(true);
    try {
      await api.gameDesignate(gameId, Number(slot), npcId);
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  return (
    <PixelModal isOpen={isOpen} onClose={onClose} title="🌙 전날밤 — 내일 마주칠 NPC" size="md">
      {rows.length === 0 ? (
        <p className="text-sm text-pixel-muted">오늘은 마주칠 NPC가 없습니다.</p>
      ) : (
        <ul className="flex flex-col gap-2 mb-4">
          {rows.map(([slot, npcs]) => {
            const pick = picks[slot] || npcs[0];
            const isMine = designated[slot] === pick;
            return (
              <li key={slot} className="text-sm bg-pixel-path rounded-lg px-3 py-2">
                <div>
                  슬롯{slot}: <b>{npcName(pick)}</b>
                  <span className="text-pixel-muted"> ({NPC_ROLES[pick] ?? "?"})</span>와 대화
                  <span className={`ml-1.5 text-xs font-bold rounded px-1 ${
                    isMine ? "bg-yellow-100 text-yellow-800" : "bg-green-50 text-pixel-greenText"}`}>
                    {isMine ? "👤 내 지정" : "🪞 클론의 선택"}
                  </span>
                </div>
                {/* T-272a — 후보가 여럿일 때만 선택지 노출(하나뿐이면 정할 게 없다). */}
                {npcs.length > 1 && (
                  <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                    {npcs.map((n) => (
                      <button
                        key={n}
                        disabled={busy || n === pick}
                        onClick={() => doDesignate(slot, n)}
                        className={`text-xs font-bold border-2 border-black rounded-lg px-2 py-0.5
                          ${n === pick ? "bg-black text-white" : "bg-white hover:bg-pixel-water cursor-pointer"}
                          disabled:cursor-default`}
                      >
                        {npcName(n)}
                      </button>
                    ))}
                    {isMine && (
                      <button
                        disabled={busy}
                        onClick={() => doDesignate(slot, null)}
                        className="text-xs text-pixel-muted underline underline-offset-2 hover:text-black cursor-pointer"
                      >
                        클론에게 맡기기
                      </button>
                    )}
                  </div>
                )}
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
