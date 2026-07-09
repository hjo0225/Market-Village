"use client";

import { useEffect, useState } from "react";

// §3 — 설문 전후 스토리 씬(정적, 프론트 전용). AdvDialogue 스타일 컷 진행:
// 클릭/Enter로 다음 컷, "건너뛰기"로 전체 스킵. cuts는 정적 한국어 스크립트(스펙
// §3.1/§3.2/§3.3 그대로) — LLM 호출 없음(I5).

export interface StoryCut {
  bg?: string;          // 톤 힌트(예: "dark") — 배경색 변주용, 필수 아님
  speaker?: string;
  lines: string[];
}

export default function StoryScene({
  cuts,
  onDone,
}: {
  cuts: StoryCut[];
  onDone: () => void;
}) {
  const [i, setI] = useState(0);
  const cut = cuts[i];
  const isLast = i >= cuts.length - 1;

  const advance = () => {
    if (isLast) onDone();
    else setI((n) => n + 1);
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); advance(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [i, cuts.length]);

  if (!cut) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black flex items-center justify-center p-4">
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); onDone(); }}
        className="absolute top-4 right-4 text-[12px] font-bold text-white/60 hover:text-white/90 bg-white/10 rounded px-3 py-1.5 border border-white/20"
      >
        건너뛰기
      </button>

      <button
        type="button"
        onClick={advance}
        aria-label="다음"
        className="w-full h-full max-w-2xl flex flex-col items-center justify-center gap-6 cursor-pointer text-left"
      >
        <div className="w-full flex flex-col gap-3">
          {cut.speaker && (
            <div className="text-[13px] font-extrabold text-white/70 text-center">{cut.speaker}</div>
          )}
          {cut.lines.map((line, li) => (
            <p key={li} className="text-[16px] sm:text-[18px] leading-relaxed text-white text-center whitespace-pre-line">
              {line}
            </p>
          ))}
        </div>
        <div className="text-[11px] text-white/40 animate-pulse mt-4">
          {isLast ? "클릭하여 계속" : "▶ 클릭 또는 Enter"}
        </div>
      </button>

      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-1.5">
        {cuts.map((_, ci) => (
          <div key={ci} className={`h-1.5 w-6 rounded-full ${ci <= i ? "bg-white/70" : "bg-white/20"}`} />
        ))}
      </div>
    </div>
  );
}
