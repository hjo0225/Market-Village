"use client";

import { motion } from "framer-motion";
import * as api from "@/lib/emoApi";
import PixelPanel from "@/components/pixel/PixelPanel";
import PixelButton from "@/components/pixel/PixelButton";
import InvestmentTypeCard from "@/components/InvestmentTypeCard";
import NameStep from "@/components/emo/NameStep";
import DiagnosisStep from "@/components/emo/DiagnosisStep";
import AllocationStep from "@/components/emo/AllocationStep";
import { CatalogCoin, Category } from "@/lib/emoApi";
import { Level, LevelMap } from "@/types/emo";
import { QUESTIONS } from "@/constants/emo";

const STEP_TITLE = ["이사 온 날", "투자 성향 진단", "성향 결과", "초기 자산 배분"];

export default function OnboardingWizard({
  step, name, questionIndex, answers, diagnosis, levels, catalog, busy, error,
  onNameChange, onNameSubmit, onSelectOption, onLevelChange,
  onBack, onNext, onStart, onResetDiagnosis, onCopyShare,
}: {
  step: number;
  name: string;
  questionIndex: number;
  answers: Record<string, number>;
  diagnosis: api.DispositionDiagnosis | null;
  levels: LevelMap;
  catalog: CatalogCoin[] | null;
  busy: boolean;
  error: string | null;
  onNameChange: (v: string) => void;
  onNameSubmit: () => void;
  onSelectOption: (optionIndex: number) => void;
  onLevelChange: (cat: Category, lv: Level) => void;
  onBack: () => void;
  onNext: () => void;
  onStart: () => void;
  onResetDiagnosis: () => void;
  onCopyShare: () => void;
}) {
  const diagnosisReady = QUESTIONS.every((q) => q.key in answers);
  const currentAnswered = QUESTIONS[questionIndex].key in answers;

  return (
    <main className="relative min-h-screen flex items-center justify-center p-4 overflow-hidden">
      {/* 맵 배경은 부모(emo/page)의 공유 컷씬 iframe — 화면 전환 시 재부팅 방지. */}
      <div className="fixed inset-0 bg-black/55 pointer-events-none" />
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src="/assets/ui/market_village_logo.png"
        alt="Market Village"
        className="fixed left-4 top-4 z-20 w-32 sm:w-40 drop-shadow-[0_2px_8px_rgba(0,0,0,0.8)]"
      />

      <motion.div
        className="relative z-10 w-full max-w-xl pt-16"
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.55, ease: "easeOut" }}
      >
        <PixelPanel tone="wall" className="w-full max-w-xl p-6">
          <div className="flex items-center gap-1.5 mb-4">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className={`h-1.5 flex-1 rounded-full ${i <= step ? "bg-black/70" : "bg-black/15"}`} />
            ))}
          </div>
          <div className="text-[11px] text-pixel-muted mb-1">{step + 1} / 4</div>
          <h1 className="text-lg font-extrabold mb-5">{STEP_TITLE[step]}</h1>

          {step === 0 && <NameStep name={name} onChange={onNameChange} onSubmit={onNameSubmit} />}

          {step === 1 && (
            <DiagnosisStep questionIndex={questionIndex} answers={answers} onSelect={onSelectOption} />
          )}

          {step === 2 && (
            diagnosis ? (
              <InvestmentTypeCard diagnosis={diagnosis} onCopy={onCopyShare} onReset={onResetDiagnosis} />
            ) : (
              <div className="rounded-xl border-2 border-black bg-white p-4 text-[13px] font-bold shadow-pixel-sm">
                결과를 계산하는 중…
              </div>
            )
          )}

          {step === 3 && <AllocationStep levels={levels} catalog={catalog} onChange={onLevelChange} />}

          {error && <p className="mt-4 text-[12px] font-bold text-red-600" role="alert">{error}</p>}

          <div className="flex gap-2 mt-6">
            {step > 0 && (
              <PixelButton size="lg" variant="ghost" className="shrink-0" onClick={onBack}>
                ← 뒤로
              </PixelButton>
            )}
            {step < 3 ? (
              <PixelButton
                size="lg" className="flex-1"
                disabled={(step === 1 && !currentAnswered) || (step === 2 && (!diagnosisReady || !diagnosis))}
                onClick={onNext}
              >
                {step === 1 && questionIndex < QUESTIONS.length - 1 ? "다음 문항 →" : "다음 →"}
              </PixelButton>
            ) : (
              <PixelButton size="lg" className="flex-1" disabled={busy} onClick={onStart}>
                {busy ? "시작하는 중…" : "이사 온 날 →"}
              </PixelButton>
            )}
          </div>
        </PixelPanel>
      </motion.div>
    </main>
  );
}
