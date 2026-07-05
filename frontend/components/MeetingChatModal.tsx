"use client";

import Image from "next/image";
import PixelButton from "@/components/pixel/PixelButton";

// T-281 — 만남 1:1 대화를 핸드폰 채팅창으로(사용자 반복 피드백 — 맵 말풍선 대체).
// 하루 진행 중 만남 시간대에 map.html이 meeting_talk를 올리면 이 폰이 슬라이드업,
// 닫으면 부모가 meeting_done을 iframe에 보내 걷기가 재개된다(T-275 순서 계승).
// 관찰 전용 — 개입(권유)은 기존 📱 핸드폰 1:1 탭 그대로.
export interface MeetingNpc {
  id: string;
  name: string;
  role: string;
  portrait: string | null;
}
export interface MeetingLine {
  who: "npc" | "clone";
  text: string;
}

export default function MeetingChatModal({ npc, lines, onClose }: {
  npc: MeetingNpc; lines: MeetingLine[]; onClose: () => void;
}) {
  return (
    <div role="dialog" aria-modal="true" className="fixed inset-0 z-[135] flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="absolute inset-0 bg-pixel-ink/60" />
      {/* T-255와 같은 핸드폰 프레임 */}
      <div className="relative w-full max-w-md bg-slate-900 border-2 border-black rounded-t-[28px] sm:rounded-[32px] shadow-pixel-md pt-2 pb-4 px-2 animate-[phoneup_0.45s_ease-out]">
        <style>{`@keyframes phoneup { from { transform: translateY(60%); opacity: 0.4; } to { transform: translateY(0); opacity: 1; } }`}</style>
        <div className="mx-auto w-24 h-1.5 rounded-full bg-slate-700 mb-1.5" />
        <div className="flex items-center justify-between px-4 text-[10px] text-slate-400 font-bold mb-1">
          <span>💬 1:1</span><span>마을넷 📶 🔋</span>
        </div>
        <div className="bg-white rounded-2xl overflow-hidden">
          {/* 채팅 상대 헤더 */}
          <div className="flex items-center gap-2.5 px-4 py-2.5 border-b-2 border-black">
            {npc.portrait ? (
              <Image
                src={`/assets/characters/profile/${npc.portrait}.png`}
                alt={npc.name} width={32} height={32}
                className="rounded-full border-2 border-black bg-pixel-grass/30"
                unoptimized
              />
            ) : (
              <span className="w-8 h-8 rounded-full border-2 border-black bg-pixel-grass/40 flex items-center justify-center text-[15px]">🤖</span>
            )}
            <div className="min-w-0">
              <h2 className="text-base font-extrabold leading-tight">{npc.name}</h2>
              <p className="text-[11px] text-pixel-muted leading-tight">{npc.role} · 마주쳤다</p>
            </div>
          </div>

          {/* 대화 버블 — 순차 등장(게시판 카드와 같은 pop 리듬) */}
          <div className="flex flex-col gap-2 max-h-[50vh] overflow-y-auto p-3 bg-slate-50">
            {lines.map((m, i) => (
              <div
                key={i}
                className={`animate-pixel-pop ${m.who === "clone" ? "self-end" : "self-start"} max-w-[85%]`}
                style={{ animationDelay: `${i * 0.55}s`, animationFillMode: "backwards" }}
              >
                {m.who === "npc" && (
                  <p className="text-[10px] font-bold text-pixel-muted mb-0.5">{npc.name}</p>
                )}
                <div className={`border rounded-xl px-3 py-2 text-sm leading-snug ${
                  m.who === "clone"
                    ? "bg-pixel-grass/60 border-black/20 rounded-br-sm"
                    : "bg-slate-100 border-black/20 rounded-bl-sm"}`}>
                  {m.text}
                </div>
                {m.who === "clone" && (
                  <p className="text-[10px] font-bold text-pixel-grass-dark text-right mt-0.5">내 클론</p>
                )}
              </div>
            ))}
          </div>

          <div className="px-3 py-2.5 border-t border-black/10 flex items-center justify-between">
            <p className="text-[12px] text-pixel-muted">클론에게 말을 걸고 싶다면 📱 1:1 탭에서.</p>
            <PixelButton size="sm" onClick={onClose}>대화 마치기 ▶</PixelButton>
          </div>
        </div>
      </div>
    </div>
  );
}
