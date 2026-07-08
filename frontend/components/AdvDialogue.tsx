"use client";

import { useState } from "react";
import { NPC_NAME, npcPortraitSrc } from "@/lib/emoApi";

// T-31/T-32 — ADV say 스크린(대사 텍스트박스). 맵 위 하단에 오버레이. 선택지는
// 분리된 AdvChoiceMenu(choice 스크린)가 담당한다 — 정통 ADV처럼 say/choice 분리.
// T-42 — 좌측 프로필 = 캐릭터 초상 이미지(/assets/characters/profile). 에셋 없거나
// 로드 실패하면 NPC별 색 배경 + 이니셜로 폴백(기존 동작).

const AVATAR_BG: Record<string, string> = {
  panic_ant: "bg-sky-500", fomo_scalper: "bg-amber-500",
  conspiracy_influencer: "bg-violet-500", value_investor: "bg-emerald-500",
  quant_trader: "bg-indigo-500", macro_whale: "bg-cyan-600",
  contrarian: "bg-rose-500", jackpot_gambler: "bg-orange-500",
};

export default function AdvDialogue({
  speakerId,
  speakerName,
  role,
  title,
  text,
  tone = "chain",
}: {
  speakerId?: string;
  speakerName?: string;
  role?: string;
  title?: string;
  text: string;
  tone?: "chain" | "board" | "dilemma";
}) {
  const name = speakerName ?? (speakerId ? NPC_NAME[speakerId] ?? speakerId : "");
  const avatarBg = (speakerId && AVATAR_BG[speakerId]) || "bg-slate-500";
  const initial = (name || "?").trim().charAt(0);
  const portraitSrc = npcPortraitSrc(speakerId);
  const [imgOk, setImgOk] = useState(true);
  const accent =
    tone === "dilemma" ? "border-amber-400" : tone === "board" ? "border-sky-400" : "border-white/30";

  return (
    <div className={`bg-black/80 text-white rounded-xl border-2 ${accent} backdrop-blur-sm p-3 sm:p-4 shadow-lg`}>
      <div className="flex gap-3">
        {/* 초상 — T-42: 캐릭터 얼굴 이미지, 실패 시 색배경+이니셜 폴백 */}
        <div className="shrink-0">
          {portraitSrc && imgOk ? (
            <img
              src={portraitSrc}
              alt={name}
              onError={() => setImgOk(false)}
              className="w-14 h-14 sm:w-16 sm:h-16 rounded-lg border-2 border-white/40 object-cover bg-slate-700 [image-rendering:pixelated]"
            />
          ) : (
            <div
              className={`w-14 h-14 sm:w-16 sm:h-16 rounded-lg ${avatarBg} border-2 border-white/40 flex items-center justify-center text-2xl font-extrabold text-white`}
              aria-hidden
            >
              {initial}
            </div>
          )}
        </div>
        {/* 이름 + 대사 */}
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline gap-2 mb-1">
            <span className="text-[13px] font-extrabold">{name}</span>
            {role && <span className="text-[11px] text-white/50">{role}</span>}
          </div>
          {title && <div className="text-[12px] font-bold text-white/80 mb-0.5">{title}</div>}
          <p className="text-[13px] leading-relaxed whitespace-pre-line">{text}</p>
        </div>
      </div>
    </div>
  );
}
