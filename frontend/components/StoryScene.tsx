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
  cloneName,
  dim = true,
}: {
  cuts: StoryCut[];
  onDone: () => void;
  cloneName?: string;   // 있으면 컷씬 배경의 클론 이름표로 표시
  dim?: boolean;        // false면 배경 어둡기(backdrop) 없이 마을이 그대로 보임
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
  const dark = cut.bg === "dark";   // 암전 컷(무드 라인)은 배경 없이 검정 유지

  return (
    <div className="fixed inset-0 z-50 bg-black overflow-hidden">
      {/* 게임 컷씬 배경 — Phaser(map.html?mode=cutscene)가 마을을 천천히 팬.
          씬 전체에서 1회만 마운트(컷 넘겨도 카메라 팬 연속), 암전 컷에선 opacity로 숨김. */}
      <iframe
        src={`/map.html?mode=cutscene${cloneName ? `&name=${encodeURIComponent(cloneName)}` : ""}`}
        title="컷씬 배경"
        aria-hidden
        className={`absolute inset-0 h-full w-full border-0 pointer-events-none transition-opacity duration-700 ${dark ? "opacity-0" : "opacity-100"}`}
      />
      {/* 텍스트 가독용 어둡기 + 시네마 레터박스 */}
      {!dark && dim && <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/25 to-black/75 pointer-events-none" />}
      <div className="absolute top-0 inset-x-0 h-10 sm:h-14 bg-black pointer-events-none" />
      <div className="absolute bottom-0 inset-x-0 h-10 sm:h-14 bg-black pointer-events-none" />

      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); onDone(); }}
        className="absolute top-14 sm:top-[4.5rem] right-4 z-10 text-[12px] font-bold text-white/60 hover:text-white/90 bg-black/40 rounded px-3 py-1.5 border border-white/20"
      >
        건너뛰기
      </button>

      {/* 클릭 영역 전체 + 하단 대사창(JRPG 컷씬 스타일) */}
      <button
        type="button"
        onClick={advance}
        aria-label="다음"
        className="absolute inset-0 z-[5] flex items-end justify-center cursor-pointer text-left pb-16 sm:pb-20 px-4"
      >
        <div className="w-full max-w-2xl rounded-xl border-2 border-white/25 bg-black/70 backdrop-blur-sm p-4 sm:p-5 shadow-lg">
          {cut.speaker && (
            <div className="text-[13px] font-extrabold text-[#baff7a] mb-1.5">{cut.speaker}</div>
          )}
          {cut.lines.map((line, li) => (
            <p key={li} className="text-[15px] sm:text-[16px] leading-relaxed text-white whitespace-pre-line">
              {line}
            </p>
          ))}
          <div className="text-[11px] text-white/40 animate-pulse mt-3 text-right">
            {isLast ? "클릭하여 계속" : "▶ 클릭 또는 Enter"}
          </div>
        </div>
      </button>

      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10 flex gap-1.5">
        {cuts.map((_, ci) => (
          <div key={ci} className={`h-1.5 w-6 rounded-full ${ci <= i ? "bg-white/70" : "bg-white/20"}`} />
        ))}
      </div>
    </div>
  );
}
