"use client";

import { BadgeCheck, Copy, RotateCcw, ShieldCheck } from "lucide-react";
import { DispositionDiagnosis } from "@/lib/emoApi";
import PixelButton from "@/components/pixel/PixelButton";

const RISK_ROWS: [string, string][] = [
  ["안정형", "5등급 이하"],
  ["안정추구형", "4등급 이하"],
  ["위험중립형", "3등급 이하"],
  ["적극투자형", "2등급 이하"],
  ["공격투자형", "1등급 이하"],
];

interface Props {
  diagnosis: DispositionDiagnosis;
  onCopy: () => void;
  onReset: () => void;
}

export default function InvestmentTypeCard({ diagnosis, onCopy, onReset }: Props) {
  const shareText = `내 투자 성향은 ${diagnosis.declared_type} (권유 등급 ${diagnosis.risk_grade})`;

  return (
    <div className="flex flex-col gap-3">
      <section className="border-2 border-black rounded-xl bg-[#fff7d6] shadow-pixel-md p-4 animate-card-reveal">
        <div className="text-[11px] font-extrabold text-black/55">내 투자 성향</div>
        <div className="mt-1 flex items-end justify-between gap-3">
          <h2 className="text-3xl font-black leading-none">{diagnosis.declared_type}</h2>
          <div className="rounded-lg border-2 border-black bg-[#76d672] px-2.5 py-1 text-[11px] font-black">
            권유 등급 {diagnosis.risk_grade}
          </div>
        </div>
        <p className="mt-2.5 text-[12px] leading-relaxed font-semibold">{diagnosis.type_desc}</p>
        <div className="mt-2.5 grid grid-cols-2 gap-2 text-[11px]">
          <div className="rounded-lg border border-black/20 bg-white/70 px-2 py-1.5">
            감당 능력 <b>{diagnosis.capacity_score}</b>
          </div>
          <div className="rounded-lg border border-black/20 bg-white/70 px-2 py-1.5">
            감수 태도 <b>{diagnosis.attitude_score}</b>
          </div>
        </div>
      </section>

      <section className="rounded-xl border-2 border-black bg-pixel-wall p-3 shadow-pixel-sm">
        <div className="mb-2 flex items-center gap-1.5 text-[12px] font-black">
          <ShieldCheck className="h-4 w-4" />
          공식 5단계 · 내 위치
        </div>
        <div className="grid grid-cols-5 gap-1 text-center text-[10px] font-black">
          {RISK_ROWS.map(([type]) => {
            const active = type === diagnosis.declared_type;
            return (
              <div
                key={type}
                className={`flex flex-col items-center gap-0.5 rounded-md border px-1 py-1.5 leading-tight ${
                  active ? "border-black bg-[#76d672]" : "border-black/15 bg-white/60 text-black/55"
                }`}
              >
                {active && <BadgeCheck className="h-3.5 w-3.5" />}
                {type.replace("형", "")}
              </div>
            );
          })}
        </div>
      </section>

      <div className="grid grid-cols-2 gap-2">
        <PixelButton size="lg" variant="ghost" onClick={onReset}>
          <RotateCcw className="h-4 w-4" />
          다시 풀기
        </PixelButton>
        <PixelButton
          size="lg"
          onClick={() => {
            navigator.clipboard?.writeText(shareText).catch(() => undefined);
            onCopy();
          }}
        >
          <Copy className="h-4 w-4" />
          공유 문구
        </PixelButton>
      </div>

      <p className="text-center text-[10px] font-semibold text-black/40">{diagnosis.source}</p>
    </div>
  );
}
