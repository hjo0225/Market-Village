"use client";

import { BadgeCheck, Copy, RotateCcw, ShieldCheck } from "lucide-react";
import { DispositionDiagnosis } from "@/lib/emoApi";
import PixelButton from "@/components/pixel/PixelButton";

const RISK_ROWS = [
  ["안정형", "5등급 이하"],
  ["안정추구형", "4등급 이하"],
  ["위험중립형", "3등급 이하"],
  ["적극투자형", "2등급 이하"],
  ["공격투자형", "1등급 이하"],
];

const AXIS_COPY: Record<string, { left: string; right: string }> = {
  AS: { left: "공격", right: "안전" },
  LQ: { left: "장기", right: "단기" },
  DF: { left: "데이터", right: "감" },
  RE: { left: "여유", right: "올인" },
};

interface Props {
  diagnosis: DispositionDiagnosis;
  onCopy: () => void;
  onReset: () => void;
}

export default function InvestmentTypeCard({ diagnosis, onCopy, onReset }: Props) {
  const shareText = `${diagnosis.mbti_type} ${diagnosis.mbti_name} · 공식 성향 ${diagnosis.declared_type}`;

  return (
    <div className="flex flex-col gap-4">
      <section className="border-2 border-black rounded-xl bg-[#fff7d6] shadow-pixel-md p-4 animate-card-reveal">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-[11px] font-extrabold text-black/55">투자 성향 코드</div>
            <h2 className="mt-1 text-3xl font-black leading-none tracking-normal">{diagnosis.mbti_type}</h2>
            <div className="mt-1 text-xl font-black">{diagnosis.mbti_name}</div>
          </div>
          <div className="rounded-lg border-2 border-black bg-[#76d672] px-2.5 py-1 text-[11px] font-black">
            {diagnosis.declared_type}
          </div>
        </div>
        <p className="mt-3 text-[13px] leading-relaxed font-semibold">{diagnosis.mbti_summary}</p>
        <div className="mt-3 grid grid-cols-2 gap-2 text-[11px]">
          <div className="rounded-lg border border-black/20 bg-white/70 px-2 py-1.5">
            잘 맞는 타입 <b>{diagnosis.mbti_good_match}</b>
          </div>
          <div className="rounded-lg border border-black/20 bg-white/70 px-2 py-1.5">
            삐걱 타입 <b>{diagnosis.mbti_bad_match}</b>
          </div>
        </div>
      </section>

      <section className="grid gap-2">
        {Object.entries(diagnosis.mbti_axes).map(([key, axis]) => {
          const label = AXIS_COPY[key] ?? { left: axis.left, right: axis.right };
          const leftActive = axis.selected === axis.left;
          return (
            <div key={key} className="rounded-xl border-2 border-black bg-white p-3 shadow-pixel-sm">
              <div className="mb-2 flex items-center justify-between gap-2 text-[12px] font-black">
                <span>{axis.label}</span>
                <span className="tabular-nums">{axis.left} {axis.left_pct}% / {axis.right} {axis.right_pct}%</span>
              </div>
              <div className="grid grid-cols-[42px_1fr_42px] items-center gap-2">
                <span className={`text-[11px] font-black ${leftActive ? "text-black" : "text-black/45"}`}>
                  {axis.left} {label.left}
                </span>
                <div className="h-3 rounded-full border-2 border-black bg-[#e8edf0] overflow-hidden">
                  <div
                    className="h-full bg-[#ff7664]"
                    style={{ width: `${axis.left_pct}%` }}
                  />
                </div>
                <span className={`text-right text-[11px] font-black ${!leftActive ? "text-black" : "text-black/45"}`}>
                  {axis.right} {label.right}
                </span>
              </div>
            </div>
          );
        })}
      </section>

      <section className="rounded-xl border-2 border-black bg-pixel-wall p-3 shadow-pixel-sm">
        <div className="mb-2 flex items-center gap-1.5 text-[13px] font-black">
          <ShieldCheck className="h-4 w-4" />
          공식 성향 기준
        </div>
        <div className="grid gap-1.5">
          {RISK_ROWS.map(([type, grade]) => (
            <div
              key={type}
              className={`grid grid-cols-[1fr_auto] items-center rounded-lg border px-2 py-1.5 text-[11px] font-bold ${
                type === diagnosis.declared_type
                  ? "border-black bg-[#76d672]"
                  : "border-black/15 bg-white/65 text-black/60"
              }`}
            >
              <span className="inline-flex items-center gap-1">
                {type === diagnosis.declared_type && <BadgeCheck className="h-3.5 w-3.5" />}
                {type}
              </span>
              <span>{grade}</span>
            </div>
          ))}
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
    </div>
  );
}
