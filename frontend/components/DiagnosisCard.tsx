"use client";

// v3 §D1 — 설문 직후(배분 완료 → 브릿지 씬 앞) 진단 결과 화면. POST /emo/start 응답의
// diagnosis(없으면 이 화면 자체를 스킵, I6은 호출부(app/emo/page.tsx)에서 처리).
import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { StartDiagnosis } from "@/lib/emoApi";
import PixelPanel from "@/components/pixel/PixelPanel";
import PixelButton from "@/components/pixel/PixelButton";
import { TermText } from "@/components/Term";

export default function DiagnosisCard({
  diagnosis, onConfirm,
}: { diagnosis: StartDiagnosis; onConfirm: () => void }) {
  const [open, setOpen] = useState(false);

  return (
    <main className="min-h-screen bg-pixel-path flex items-center justify-center p-4">
      <PixelPanel tone="wall" className="w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
        <div className="text-[11px] text-pixel-muted mb-1">진단 결과</div>
        <h1 className="text-xl font-extrabold mb-1">당신은 [{diagnosis.declared_type}]</h1>
        <p className="text-[12px] text-pixel-muted mb-5">
          클론은 이 성향대로 열흘을 산다. 진짜 당신과 같은지는, 끝에 확인하자.
        </p>

        {/* 축 바 */}
        {diagnosis.axes.length > 0 && (
          <section className="mb-5">
            <div className="text-[11px] text-pixel-muted mb-2">진단 축</div>
            <div className="flex flex-col gap-2.5">
              {diagnosis.axes.map((a) => {
                const pct = a.max > 0 ? Math.max(0, Math.min(100, (a.score / a.max) * 100)) : 0;
                return (
                  <div key={a.axis}>
                    <div className="flex justify-between text-[12px] font-bold mb-1">
                      <span>{a.label}</span>
                      <span className="tabular-nums text-pixel-muted">{a.score} / {a.max}</span>
                    </div>
                    <div className="h-2 rounded-full bg-black/10 overflow-hidden">
                      <div className="h-full bg-black/70 transition-all duration-500" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* 왜냐하면 — 접기 목록 */}
        {diagnosis.contributions.length > 0 && (
          <section className="mb-5">
            <button
              type="button"
              onClick={() => setOpen((o) => !o)}
              className="w-full flex items-center justify-between text-[12px] font-bold bg-black/5 rounded-lg px-3 py-2"
            >
              <span>왜냐하면</span>
              {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
            {open && (
              <div className="mt-2 flex flex-col gap-1.5">
                {diagnosis.contributions.map((c, i) => (
                  <div key={i} className="text-[12px] leading-relaxed border-l-2 border-black/10 pl-3">
                    <span className="text-pixel-muted">{c.q_label}</span>
                    <span className="mx-1">→</span>
                    <span className="font-bold">&ldquo;{c.choice_label}&rdquo;</span>
                    <span className="mx-1">→</span>
                    <span className="text-pixel-muted">{c.axis}</span>
                    <span className="ml-1 font-bold">+{c.points}</span>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* summary */}
        {diagnosis.summary.length > 0 && (
          <section className="mb-6 flex flex-col gap-2 bg-black/[0.03] rounded-lg p-3">
            {diagnosis.summary.map((s, i) => (
              <p key={i} className="text-[12.5px] leading-relaxed"><TermText text={s} /></p>
            ))}
          </section>
        )}

        <PixelButton size="lg" className="w-full" onClick={onConfirm}>확인 →</PixelButton>
      </PixelPanel>
    </main>
  );
}
