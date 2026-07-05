"use client";

import { useState } from "react";
import { api, Designated, Meetings, NPC_LABELS, NPC_ROLES, Picks } from "@/lib/api";

const PLACE_SHORT: Record<string, string> = { "집_차트": "집(차트)" };

function npcName(id: string) {
  return NPC_LABELS[id] ?? id;
}

// §9.2.1 전날밤 — 내일 일과 8슬롯을 한 눈에.
// T-272b — 슬롯별 행선지 지정(🤖 council: 장소지정≡스왑 등가 — 회피와 동일 파워,
//   원하는 장소를 끌어오면 원래 장소가 그 슬롯으로 밀려난다). 구 숫자입력 스왑 UI 대체.
// T-272a — 후보가 여럿인 슬롯은 대화 상대도 지정 가능(기본은 클론의 선택).
// T-283(사용자 지시 "전날밤 이거 없애자") — 별도 모달·헤더 버튼 제거, 이 본문을
//   📱 핸드폰의 "🌙 일과" 탭이 임베드한다(기능은 유지, 진입점만 폰으로).
export function PreviewBody({ gameId, meetings, picks, designated, schedule, onChanged }: {
  gameId: string;
  meetings: Meetings;
  picks: Picks;
  designated: Designated;
  schedule: Record<string, string>;
  onChanged: () => void;
}) {
  const [busy, setBusy] = useState(false);

  const slots = Object.keys(schedule).sort((a, b) => Number(a) - Number(b));
  const places = slots.map((s) => schedule[s]);

  async function run(p: Promise<unknown>) {
    setBusy(true);
    try { await p; onChanged(); } finally { setBusy(false); }
  }

  if (slots.length === 0) {
    return <p className="text-sm text-pixel-muted">내일 일과를 불러오는 중…</p>;
  }
  return (
    <>
      <ul className="flex flex-col gap-1.5">
        {slots.map((slot) => {
          const npcs = meetings[slot] ?? [];
          const pick = picks[slot] || npcs[0];
          const isMine = designated[slot] === pick;
          return (
            <li key={slot} className="bg-pixel-path rounded-lg px-3 py-2">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-pixel-muted w-10">슬롯{slot}</span>
                {/* T-272b — 행선지 지정: 고르면 그 장소가 있던 슬롯과 자리를 바꾼다. */}
                <select
                  value={schedule[slot]} disabled={busy}
                  onChange={(e) => void run(api.gameRelocate(gameId, Number(slot), e.target.value))}
                  className="text-sm font-bold border-2 border-black rounded-lg px-1.5 py-0.5 bg-white cursor-pointer"
                >
                  {places.map((p) => (
                    <option key={p} value={p}>{PLACE_SHORT[p] ?? p}</option>
                  ))}
                </select>
                {npcs.length > 0 && pick && (
                  <span className="text-sm">
                    🤝 <b>{npcName(pick)}</b>
                    <span className="text-pixel-muted text-xs"> ({NPC_ROLES[pick] ?? "?"})</span>
                    <span className={`ml-1 text-[10px] font-bold rounded px-1 ${
                      isMine ? "bg-yellow-100 text-yellow-800" : "bg-green-50 text-pixel-greenText"}`}>
                      {isMine ? "👤 내 지정" : "🪞 클론"}
                    </span>
                  </span>
                )}
              </div>
              {/* T-272a — 후보가 여럿일 때만 상대 선택지 노출. */}
              {npcs.length > 1 && (
                <div className="mt-1.5 ml-10 flex flex-wrap items-center gap-1.5">
                  {npcs.map((n) => (
                    <button
                      key={n} disabled={busy || n === pick}
                      onClick={() => void run(api.gameDesignate(gameId, Number(slot), n))}
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
                      onClick={() => void run(api.gameDesignate(gameId, Number(slot), null))}
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
      <p className="text-xs text-pixel-muted mt-3">
        장소를 고르면 그 장소가 있던 슬롯과 <b>자리가 바뀝니다</b> — 피한 자리에 누가 올지는 가봐야 안다.
      </p>
    </>
  );
}
