"use client";

import { useState } from "react";
import { HistoryDay, NPC_LABELS } from "@/lib/api";
import { TradeStory } from "@/components/PhoneModal";

// T-269 — 좌측 발자취 패널(사용자 피드백 ④): 일별로 (a) 어떤 뉴스를 골랐는지
// (b) 누구와 어떤 대화를 했는지 (c) 어디를 갔는지 + 지금 어디로 가는지.
// 순수 표시 컴포넌트 — 데이터는 GET /history + 오늘의 preview/schedule.
const TONE_BADGE: Record<string, { label: string; cls: string }> = {
  optimism: { label: "🚀 호재", cls: "bg-green-50 text-pixel-greenText" },
  fear: { label: "📉 악재", cls: "bg-yellow-50 text-pixel-danger" },
  uncertain: { label: "🌫 불확실", cls: "bg-slate-100 text-pixel-muted" },
};

const PLACE_SHORT: Record<string, string> = { "집_차트": "집" };

function npcName(id: string) {
  return NPC_LABELS[id] ?? id;
}

function placesLine(schedule: Record<string, string>): string {
  return Object.keys(schedule)
    .sort((a, b) => Number(a) - Number(b))
    .map((k) => PLACE_SHORT[schedule[k]] ?? schedule[k])
    .join(" → ");
}

function socialLine(s: HistoryDay["social"][number]): string {
  if (s.kind === "persuade") {
    const dir = s.direction === "calm" ? "진정" : "부추김";
    return `💬 ${npcName(s.npc_id ?? "")}에게 ${dir} 권유 ${s.accepted ? "✓ 먹힘" : "✗ 씹힘"}`;
  }
  const tone = s.tone === "calm" ? "진정" : s.tone === "clarify" ? "팩트체크" : "공포 동참";
  return `📢 단톡방에 ${tone} 글`;
}

interface Props {
  history: HistoryDay[];
  todaySchedule: Record<string, string>;
  today: number;
  heading: string | null;   // 진행 연출 중 "지금 이동 중" 라벨(없으면 null)
  activity: string | null;  // T-292 — 맵의 활동 서술(말풍선은 이모지만, 텍스트는 여기)
}

export default function HistoryPanel({ history, todaySchedule, today, heading, activity }: Props) {
  const [open, setOpen] = useState(true);

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed left-4 top-1/2 -translate-y-1/2 z-10 bg-white/90 border-2 border-black
          rounded-xl shadow-pixel-md px-2 py-3 text-sm font-bold cursor-pointer hover:bg-pixel-water"
        aria-label="발자취 열기"
      >
        📜
      </button>
    );
  }

  const past = [...history].sort((a, b) => b.day - a.day);

  return (
    <aside className="fixed left-4 top-24 bottom-24 z-10 w-64 hidden md:flex flex-col
      bg-white/90 backdrop-blur-sm border-2 border-black rounded-2xl shadow-pixel-md overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 border-b-2 border-black bg-pixel-table flex-shrink-0">
        <span className="text-sm font-extrabold">📜 발자취</span>
        <div className="flex-1" />
        <button onClick={() => setOpen(false)} aria-label="발자취 접기"
          className="text-xs font-bold border-2 border-black rounded-lg px-1.5 bg-white cursor-pointer hover:bg-pixel-water">←</button>
      </div>

      <div className="flex-1 overflow-y-auto p-2.5 flex flex-col gap-2">
        {/* 오늘 — 일정 + 지금 이동 중 */}
        <div className="rounded-xl border-2 border-pixel-grass bg-green-50/60 p-2.5">
          <p className="text-xs font-extrabold mb-1">Day {today} · 오늘</p>
          {/* T-292 — 맵 활동 서술이 있으면 그것이 "지금"(말풍선 텍스트의 이사처) */}
          {activity
            ? <p className="text-xs font-bold mb-1">{activity}</p>
            : heading && <p className="text-xs font-bold mb-1">🚶 지금: {heading}</p>}
          <p className="text-[11px] text-pixel-muted leading-relaxed">
            {Object.keys(todaySchedule).length ? placesLine(todaySchedule) : "일과 준비 중…"}
          </p>
        </div>

        {past.length === 0 && (
          <p className="text-xs text-pixel-muted px-1">아직 지나온 날이 없어요.</p>
        )}
        {past.map((d) => {
          const tone = TONE_BADGE[d.news_tone];
          return (
            <div key={d.day} className="rounded-xl border border-black/20 bg-white p-2.5">
              <div className="flex items-center gap-1.5 mb-1">
                <span className="text-xs font-extrabold">Day {d.day}</span>
                {tone
                  ? <span className={`text-[10px] font-bold rounded px-1 ${tone.cls}`}>{tone.label}</span>
                  : <span className="text-[10px] text-pixel-muted">뉴스 안 봄</span>}
                {d.swayed && <span className="text-[10px] font-bold text-pixel-danger">🌀 휘둘림</span>}
              </div>
              {d.met.length > 0 && (
                <p className="text-[11px] leading-relaxed">
                  🤝 {d.met.map(npcName).join(", ")}와 대화
                </p>
              )}
              {d.social.map((s, i) => (
                <p key={i} className="text-[11px] text-pixel-muted leading-relaxed">{socialLine(s)}</p>
              ))}
              {/* T-300 — 그날의 매매 서사(감정→행동→시세→수익률) */}
              {d.trade && <TradeStory trade={d.trade} day={d.day} />}
              <p className="text-[10px] text-pixel-muted mt-1">{placesLine(d.schedule)}</p>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
