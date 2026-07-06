"use client";

import { useEffect, useState } from "react";
import { api, Designated, Meetings, NPC_LABELS, NPC_ROLES, Picks } from "@/lib/api";

const PLACE_SHORT: Record<string, string> = { "집_차트": "집(차트)" };

function npcName(id: string) {
  return NPC_LABELS[id] ?? id;
}

interface PreviewData {
  schedule: Record<string, string>;
  meetings: Meetings;
  picks: Picks;
  designated: Designated;
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
  const [err, setErr] = useState("");
  // T-284(사용자: "동작하는데 안 되는 것처럼 보임") — 성공을 즉시 보여준다.
  // 컨트롤드 값이 props에 묶여 있어, 클릭 후 전체 새로고침(refresh, API 5콜)이
  // 돌아올 때까지 select가 옛 값으로 스냅백해 무반응처럼 보였다. 변이 API가
  // 새 preview를 응답에 담아 주므로 그걸 로컬 미러에 즉시 반영하고, props가
  // 갱신되면(refresh 완료) 미러를 비워 단일 진실 소스로 복귀한다.
  const [local, setLocal] = useState<PreviewData | null>(null);
  useEffect(() => { setLocal(null); }, [schedule, meetings, picks, designated]);
  const cur: PreviewData = local ?? { schedule, meetings, picks, designated };

  const slots = Object.keys(cur.schedule).sort((a, b) => Number(a) - Number(b));
  const places = slots.map((s) => cur.schedule[s]);

  // T-283 후속 — 실패도 조용히 삼키지 않는다(서버 거부·네트워크 실패 사유 표시).
  async function run(p: Promise<{ status: string; error?: string } & Partial<PreviewData>>) {
    setBusy(true);
    setErr("");
    try {
      const r = await p;
      if (r.status !== "ok") {
        setErr(`⚠️ 반영 안 됨 — ${r.error ?? "서버가 거부했어요"}`);
        return;
      }
      setLocal({
        schedule: r.schedule ?? cur.schedule,
        meetings: r.meetings ?? cur.meetings,
        picks: r.picks ?? cur.picks,
        designated: r.designated ?? cur.designated,
      });
      onChanged();
    } catch {
      setErr("⚠️ 네트워크 오류 — 잠시 후 다시 시도해 주세요.");
    } finally {
      setBusy(false);
    }
  }

  if (slots.length === 0) {
    return <p className="text-sm text-pixel-muted">내일 일과를 불러오는 중…</p>;
  }
  return (
    <>
      {err && <p className="text-xs font-bold text-pixel-danger mb-1.5">{err}</p>}
      <ul aria-busy={busy} className={`flex flex-col gap-1.5 transition-opacity ${busy ? "opacity-60" : ""}`}>
        {slots.map((slot) => {
          const npcs = cur.meetings[slot] ?? [];
          const pick = cur.picks[slot] || npcs[0];
          const isMine = cur.designated[slot] === pick;
          return (
            <li key={slot} className="bg-pixel-path rounded-lg px-3 py-2">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-pixel-muted w-10">슬롯{slot}</span>
                {/* T-272b — 행선지 지정: 고르면 그 장소가 있던 슬롯과 자리를 바꾼다. */}
                <select
                  value={cur.schedule[slot]} disabled={busy}
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
