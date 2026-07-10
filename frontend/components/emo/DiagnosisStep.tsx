"use client";

import InfoHint from "@/components/InfoHint";
import { QUESTIONS, QUESTION_HINTS } from "@/constants/emo";

// 온보딩 STEP 1 — 성향 진단(한 문항 한 화면).
export default function DiagnosisStep({ questionIndex, answers, onSelect }: {
  questionIndex: number;
  answers: Record<string, number>;
  onSelect: (optionIndex: number) => void;
}) {
  const q = QUESTIONS[questionIndex];
  const answered = q.key in answers;
  const progressPct = Math.round(((questionIndex + (answered ? 1 : 0)) / QUESTIONS.length) * 100);
  return (
    <div>
      <div className="mb-4">
        <div className="mb-1 flex items-center justify-between text-[11px] font-bold text-pixel-muted">
          <span>{questionIndex + 1} / {QUESTIONS.length}</span>
          <span>{progressPct}%</span>
        </div>
        <div className="h-2 rounded-full border-2 border-black bg-white overflow-hidden">
          <div className="h-full bg-[#76d672]" style={{ width: `${progressPct}%` }} />
        </div>
      </div>
      <div className="rounded-xl border-2 border-black bg-white p-4 shadow-pixel-sm">
        <div className="text-[11px] font-black text-black/45">{q.key}</div>
        <div className="mt-1 text-[17px] font-black leading-snug">
          {q.text}
          {QUESTION_HINTS[q.key] && (
            <span className="ml-1.5 inline-block">
              <InfoHint title={QUESTION_HINTS[q.key].title} text={QUESTION_HINTS[q.key].text} />
            </span>
          )}
        </div>
        <div className="mt-4 grid gap-2">
          {q.options.map(([label, val], optionIndex) => (
            <button
              type="button"
              key={label}
              aria-label={`선택지 ${optionIndex + 1}: ${label}`}
              className={`grid min-h-12 grid-cols-[1fr_auto] items-center gap-3 rounded-xl border-2 px-3 py-2 text-left text-[13px] font-extrabold shadow-pixel-sm ${answers[q.key] === val
                ? "border-black bg-yellow-300"
                : "border-black/35 bg-pixel-wall hover:bg-white"
                }`}
              onClick={() => onSelect(optionIndex)}
            >
              <span>{label}</span>
              <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-md px-1 text-[8px] leading-none border border-gray-400 text-gray-400">
                {optionIndex + 1}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
