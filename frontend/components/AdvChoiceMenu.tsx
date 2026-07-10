"use client";

import { AXIS_LABEL, Axis } from "@/lib/emoApi";

// T-31/T-32 — ADV choice 스크린(선택 메뉴). say 박스와 분리되어 맵 위에 오버레이되는
// 창형 메뉴(정통 ADV). tone으로 색조 구분(만남/게시판/딜레마).
// 선택지 라벨과 그 선택이 주는 감정 영향(deltas)을 시각적으로 분리해 보여준다.

export interface AdvChoice {
  id: string;
  label: string;
  deltas?: Record<string, number>;
}

function EffectChips({ deltas }: { deltas: Record<string, number> }) {
  const entries = Object.entries(deltas).filter(([, v]) => v !== 0);
  if (!entries.length) return null;
  return (
    <span className="flex flex-wrap justify-center gap-x-2 gap-y-0.5 border-t border-white/20 pt-1 mt-1 w-full">
      {entries.map(([axis, v]) => {
        const up = v > 0;
        const mag = Math.min(3, Math.max(1, Math.round(Math.abs(v) / 4)));
        return (
          <span
            key={axis}
            className={`text-[10.5px] font-bold ${up ? "text-rose-200" : "text-sky-200"}`}
          >
            {AXIS_LABEL[axis as Axis] ?? axis}{(up ? "▲" : "▼").repeat(mag)}
          </span>
        );
      })}
    </span>
  );
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
        <button
          key={c.id}
          type="button"
          disabled={busy}
          onClick={() => onChoose(c.id)}
          className="w-full rounded-lg border-2 border-white/25 bg-slate-800/90 hover:bg-slate-700 hover:border-white/50
            px-3 py-2.5 text-[14px] font-extrabold text-white text-center transition-colors
            disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span className="flex w-full flex-col items-center">
            <span>{c.label}</span>
            {c.deltas && <EffectChips deltas={c.deltas} />}
          </span>
        </button>
      ))}
    </div>
  );
}
