"use client";

import PixelButton from "@/components/pixel/PixelButton";

const STRATEGIES = [
  { value: "A_과거찌르기", label: "A 과거 찌르기" },
  { value: "B_함정직시", label: "B 함정 직시" },
  { value: "C_감정다독임", label: "C 감정 다독임" },
];

interface Props {
  trapName: string;
  busy: boolean;
  onChoose: (strategy: string | null) => void;
}

// 사용자 피드백(2026-07-01) — 위기 개입은 상시 노출 버튼이 아니라, 실제 위기가
// 터진 순간에만 갑작스러운 이벤트로 튀어나와야 한다. 평소엔 렌더 자체가 안 됨.
export default function CrisisEventModal({ trapName, busy, onChoose }: Props) {
  return (
    <div role="dialog" aria-modal="true" className="fixed inset-0 z-[140] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-pixel-ink/70" />
      <div className="relative w-full max-w-sm bg-white border-2 border-black rounded-2xl shadow-pixel-lg p-5 animate-bump">
        <p className="text-[11px] font-bold text-pixel-danger mb-1">⚠️ 위기 발생</p>
        <h2 className="text-lg font-extrabold mb-3">{trapName}</h2>
        <p className="text-xs text-pixel-muted mb-4">클론이 흔들리고 있다. 개입할까, 지켜볼까.</p>
        <div className="flex flex-col gap-2">
          {STRATEGIES.map((s) => (
            <PixelButton key={s.value} disabled={busy} onClick={() => onChoose(s.value)}>
              {s.label}
            </PixelButton>
          ))}
          <PixelButton variant="ghost" disabled={busy} onClick={() => onChoose(null)}>
            지켜본다 (개입 안 함)
          </PixelButton>
        </div>
      </div>
    </div>
  );
}
