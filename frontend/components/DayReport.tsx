"use client";

import { useState } from "react";
import { Moon, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { AXES, AXIS_LABEL, Axis, Emotion, CATEGORIES, CATEGORY_LABEL, Category } from "@/lib/emoApi";
import PixelPanel from "@/components/pixel/PixelPanel";
import PixelButton from "@/components/pixel/PixelButton";

// T-33/T-34 — 하루 경계 연출(취침 암전 + 클론 감정 한마디) → 하루 정산 리포트.
// 하루가 시작하고 끝난다는 리듬을 준다(사용자 #8·#12).

export interface DayReportData {
  day: number;            // 마친 날(0-index)
  name: string;
  prevEmotion: Emotion;
  nextEmotion: Emotion;
  prevAsset: number;
  nextAsset: number;
  prevHoldings: Record<string, number>;   // T-38 — 전일 카테고리별 보유액(현금 포함)
  nextHoldings: Record<string, number>;   // T-38 — 정산 후 카테고리별 보유액
  choiceLabel: string;
  market: Record<string, number>;   // T-35 — 오늘 카테고리별 수익률(%)
  log?: { label: string; tag: "buy" | "sell" | "hold" }[];   // 하루 동작 로그(감정·자산 변화와 함께 정산에서 확인)
}

const TAG_LABEL: Record<"buy" | "sell" | "hold", string> = { buy: "매수", sell: "매도", hold: "관망" };
const TAG_CLASS: Record<"buy" | "sell" | "hold", string> = {
  buy: "bg-rose-100 text-rose-700", sell: "bg-sky-100 text-sky-700", hold: "bg-black/5 text-pixel-muted",
};

// 클론의 하루 끝 한마디 — 우세 감정 기반(표현 계층, 결정론).
function sleepLine(e: Emotion): string {
  const entries = AXES.map((a) => [a, e[a] ?? 0] as [Axis, number]);
  const [axis, val] = entries.reduce((m, x) => (x[1] > m[1] ? x : m));
  if (val < 55) return "오늘은 그럭저럭. 이만 자야겠다…";
  if (axis === "greed") return "오늘은 좀 과했나… 그래도 기분은 좋아. 자자.";
  if (axis === "fear") return "무서운 하루였어. 내일은 좀 쉬엄쉬엄… 자야지.";
  if (axis === "anxiety") return "머릿속이 복잡하다. 일단 눈 좀 붙이자…";
  return "쉴 새 없는 하루였네. 오늘은 여기까지, 자야겠다.";
}

function Delta({ from, to }: { from: number; to: number }) {
  const d = Math.round(to) - Math.round(from);
  if (d === 0) return <span className="inline-flex items-center gap-0.5 text-pixel-muted"><Minus className="w-3 h-3" />0</span>;
  const up = d > 0;
  return (
    <span className={`inline-flex items-center gap-0.5 font-bold ${up ? "text-rose-600" : "text-sky-600"}`}>
      {up ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
      {up ? "+" : ""}{d}
    </span>
  );
}

export default function DayReport({ data, onNext }: { data: DayReportData; onNext: () => void }) {
  // 2단계: 취침 암전(클론 한마디) → 리포트.
  const [phase, setPhase] = useState<"sleep" | "report">("sleep");
  const assetDelta = Math.round(data.nextAsset) - Math.round(data.prevAsset);

  return (
    <div className="absolute inset-0 z-30 bg-black/85 flex items-center justify-center p-4 transition-opacity duration-500">
      {phase === "sleep" ? (
        <button className="w-full h-full flex flex-col items-center justify-center gap-4 text-white" onClick={() => setPhase("report")}>
          <Moon className="w-10 h-10 opacity-70" />
          <p className="text-[15px] font-bold max-w-sm text-center leading-relaxed">
            {data.name}: “{sleepLine(data.nextEmotion)}”
          </p>
          <span className="text-[11px] text-white/40 mt-2">화면을 눌러 하루 정산 보기</span>
        </button>
      ) : (
        <PixelPanel tone="cloud" className="w-full max-w-md p-6">
          <div className="text-[11px] text-pixel-muted mb-1">Day {data.day + 1} 정산</div>
          <h2 className="text-lg font-extrabold mb-4">오늘 하루</h2>

          <div className="mb-4">
            <div className="text-[12px] font-bold mb-2">감정 변화</div>
            <div className="grid grid-cols-2 gap-2">
              {AXES.map((a: Axis) => (
                <div key={a} className="flex items-center justify-between text-[12px] bg-black/[0.03] rounded px-2 py-1">
                  <span className="text-pixel-muted">{AXIS_LABEL[a]}</span>
                  <span className="flex items-center gap-2">
                    <span className="tabular-nums">{Math.round(data.nextEmotion[a] ?? 0)}</span>
                    <Delta from={data.prevEmotion[a] ?? 0} to={data.nextEmotion[a] ?? 0} />
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* T-35 — 오늘의 장(카테고리별 시장 움직임) */}
          {CATEGORIES.some((c) => c in data.market) && (
            <div className="mb-4">
              <div className="text-[12px] font-bold mb-2">오늘의 장</div>
              <div className="grid grid-cols-2 gap-2">
                {CATEGORIES.filter((c) => c in data.market).map((c: Category) => {
                  const pct = data.market[c];
                  return (
                    <div key={c} className="flex items-center justify-between text-[12px] bg-black/[0.03] rounded px-2 py-1">
                      <span className="text-pixel-muted">{CATEGORY_LABEL[c]}</span>
                      <span className={`font-bold tabular-nums ${pct > 0 ? "text-rose-600" : pct < 0 ? "text-sky-600" : "text-pixel-muted"}`}>
                        {pct > 0 ? "+" : ""}{pct}%
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* T-38 — 자산 내역(카테고리별 보유액 + 전일 대비 금액 변화, 현금 포함) */}
          <div className="mb-4 border-t border-black/10 pt-3">
            <div className="flex items-center justify-between text-[12px] font-bold mb-2">
              <span>자산 내역</span>
              <span className="text-[11px] text-pixel-muted font-normal">전일 대비</span>
            </div>
            <div className="flex flex-col gap-1">
              {CATEGORIES.map((c: Category) => {
                const now = data.nextHoldings[c] ?? 0;
                const d = Math.round(now) - Math.round(data.prevHoldings[c] ?? 0);
                return (
                  <div key={c} className="flex items-center justify-between text-[12px]">
                    <span className="text-pixel-muted">{CATEGORY_LABEL[c]}</span>
                    <span className="flex items-center gap-3 tabular-nums">
                      <span className="w-20 text-right">{Math.round(now).toLocaleString()}</span>
                      <span className={`w-16 text-right font-bold ${d > 0 ? "text-rose-600" : d < 0 ? "text-sky-600" : "text-pixel-muted"}`}>
                        {d > 0 ? "+" : ""}{d.toLocaleString()}
                      </span>
                    </span>
                  </div>
                );
              })}
            </div>
            <div className="flex items-center justify-between text-[13px] font-bold border-t border-black/10 mt-2 pt-2">
              <span>합계</span>
              <span className="flex items-center gap-3 tabular-nums">
                <span className="w-20 text-right">{Math.round(data.nextAsset).toLocaleString()}</span>
                <span className={`w-16 text-right ${assetDelta > 0 ? "text-rose-600" : assetDelta < 0 ? "text-sky-600" : "text-pixel-muted"}`}>
                  {assetDelta > 0 ? "+" : ""}{assetDelta.toLocaleString()}
                </span>
              </span>
            </div>
          </div>

          {/* 하루 동작 로그 — 감정·자산 변화와 함께 오늘 무엇을 했는지 훑어보기 */}
          {data.log && data.log.length > 0 ? (
            <div className="mb-5">
              <div className="text-[12px] font-bold mb-2">오늘의 동작</div>
              <div className="flex flex-col gap-1.5">
                {data.log.map((entry, i) => (
                  <div key={i} className="flex items-center gap-2 text-[12px]">
                    <span className={`shrink-0 font-bold rounded px-1.5 py-0.5 ${TAG_CLASS[entry.tag]}`}>{TAG_LABEL[entry.tag]}</span>
                    <span className="text-pixel-muted">{entry.label}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : data.choiceLabel && (
            <div className="mb-5 text-[12px]">
              <span className="text-pixel-muted">오늘의 선택 · </span>
              <span className="font-bold">{data.choiceLabel}</span>
            </div>
          )}

          <PixelButton size="lg" className="w-full" onClick={onNext}>다음 날 →</PixelButton>
        </PixelPanel>
      )}
    </div>
  );
}
