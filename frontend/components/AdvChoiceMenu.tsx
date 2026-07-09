"use client";

import PixelButton from "@/components/pixel/PixelButton";

// T-31/T-32 — ADV choice 스크린(선택 메뉴). say 박스와 분리되어 맵 중앙 상단에
// 오버레이되는 창형 메뉴(정통 ADV). tone으로 색조 구분(만남/게시판/딜레마).

export interface AdvChoice {
  id: string;
  label: string;
}

export default function AdvChoiceMenu({
  choices,
  onChoose,
  busy = false,
  tone = "chain",
}: {
  choices: AdvChoice[];
  onChoose: (id: string) => void;
  busy?: boolean;
  tone?: "chain" | "board" | "dilemma";
}) {
  if (!choices.length) return null;
  const accent =
    tone === "dilemma" ? "border-amber-400" : tone === "board" ? "border-sky-400" : "border-white/40";
  return (
    <div className={`bg-black/85 border-2 ${accent} rounded-xl backdrop-blur-sm p-2.5 shadow-lg flex flex-col gap-2 min-w-[240px] max-w-[80vw]`}>
      {choices.map((c) => (
        <PixelButton
          key={c.id}
          variant={tone === "dilemma" ? "secondary" : "primary"}
          className="w-full justify-center text-[14px] py-2.5"
          disabled={busy}
          onClick={() => onChoose(c.id)}
        >
          {c.label}
        </PixelButton>
      ))}
    </div>
  );
}
