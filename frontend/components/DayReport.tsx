"use client";

import { useEffect, useRef, useState } from "react";
import { Moon, TrendingUp, TrendingDown, Minus, ArrowRight } from "lucide-react";
import { AXES, AXIS_LABEL, Axis, Emotion, CATEGORIES, CATEGORY_LABEL, Category, Settlement, Attribution } from "@/lib/emoApi";
import PixelPanel from "@/components/pixel/PixelPanel";
import PixelButton from "@/components/pixel/PixelButton";

// T-33/T-34 — 하루 경계 연출(취침 암전 + 클론 감정 한마디) → 하루 정산 리포트.
// 하루가 시작하고 끝난다는 리듬을 준다(사용자 #8·#12).
// §5.2 — settlement이 있으면 cascade(선택→시장→포트폴리오→리밸런싱→감정 단계별
// 애니메이션) 단계를 sleep 앞에 추가. 없으면(구버전/폴백) 기존 sleep→report 그대로
// 동작(I6 하위호환) — settlement는 옵셔널.

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
  settlement?: Settlement;   // §5.1 — 있으면 cascade 단계 추가
}

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

// §5.2 — requestAnimationFrame 기반 롤링 카운터(라이브러리 추가 금지). from→to를
// durationMs에 걸쳐 easeOut으로 보간.
function useRollingNumber(target: number, active: boolean, durationMs = 700): number {
  const [value, setValue] = useState(active ? 0 : target);
  const fromRef = useRef(0);
  useEffect(() => {
    if (!active) { setValue(target); return; }
    fromRef.current = 0;
    const start = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / durationMs);
      const eased = 1 - Math.pow(1 - t, 3);
      setValue(fromRef.current + (target - fromRef.current) * eased);
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, active]);
  return value;
}

// §5.2 — 정산 캐스케이드: ① 선택 카드 강조 → ② 카테고리별 시장 변동 카운터 →
// ③ 포트폴리오 before→after 롤링 → ④ 리스크 비중 화살표 → ⑤ 감정 축 단계별 이동.
// 자동 진행(각 단계 표시 후 일정 시간 뒤 다음 단계) + 클릭으로 스킵/다음 단계 즉시 진행.
const CASCADE_STEP_MS = 1600;

function positionBadge(position: number): { label: string; cls: string } {
  if (position >= 0.2) return { label: "+매수", cls: "bg-rose-600 text-white" };
  if (position <= -0.2) return { label: "-매도", cls: "bg-sky-600 text-white" };
  return { label: "관망", cls: "bg-slate-500 text-white" };
}

function SettlementCascade({ settlement, onDone }: { settlement: Settlement; onDone: () => void }) {
  // 스텝 = choice(1) + market(1, 전체 동시 카운팅) + portfolio(1) + [attribution(1) — 있을 때만,
  // v3 §C1: 포트폴리오 다음에 삽입] + rebalance(1) + emotion_steps(N개, 각각 1스텝).
  const hasAttribution = !!settlement.attribution;
  const attributionStep = 3;                              // 포트폴리오(2) 다음
  const rebalanceStep = hasAttribution ? 4 : 3;
  const emoStepStart = rebalanceStep + 1;
  const stepCount = emoStepStart + settlement.emotion_steps.length;
  const [step, setStep] = useState(0);
  const [emoRunning, setEmoRunning] = useState<Record<string, number>>({ ...settlement.emotion_before });

  useEffect(() => {
    if (step >= stepCount) return;
    const t = setTimeout(() => setStep((s) => s + 1), CASCADE_STEP_MS);
    return () => clearTimeout(t);
  }, [step, stepCount]);

  // 감정 단계가 진행될 때마다 해당 시점까지의 누적 델타를 반영(스텝별 바 이동).
  useEffect(() => {
    const doneEmoSteps = Math.max(0, Math.min(settlement.emotion_steps.length, step - emoStepStart));
    const running: Record<string, number> = { ...settlement.emotion_before };
    for (let i = 0; i < doneEmoSteps; i++) {
      const deltas = settlement.emotion_steps[i]?.deltas ?? {};
      Object.entries(deltas).forEach(([k, v]) => { running[k] = (running[k] ?? 0) + v; });
    }
    setEmoRunning(running);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, settlement, emoStepStart]);

  const badge = positionBadge(settlement.choice.position);
  const portfolioValue = useRollingNumber(settlement.portfolio.after, step >= 2);
  const riskAfterPct = useRollingNumber(settlement.rebalance.risk_share_after * 100, step >= rebalanceStep);

  const skip = () => onDone();
  const advance = () => {
    if (step >= stepCount) onDone();
    else setStep((s) => s + 1);
  };

  return (
    <button
      type="button"
      onClick={advance}
      className="w-full max-w-md text-left cursor-pointer"
    >
      <PixelPanel tone="cloud" className="w-full p-6">
        <div className="flex items-center justify-between mb-1">
          <div className="text-[11px] text-pixel-muted">Day {settlement.day + 1} · 정산</div>
          <span onClick={(e) => { e.stopPropagation(); skip(); }} className="text-[11px] font-bold text-pixel-muted underline">
            건너뛰기
          </span>
        </div>
        <h2 className="text-lg font-extrabold mb-4">선택은 이렇게 이어졌다</h2>

        <div className="flex flex-col gap-4 min-h-[220px]">
          {/* ① 선택 카드 강조 */}
          {step >= 0 && (
            <div className={`rounded-lg border-2 p-3 transition-all duration-500 ${step === 0 ? "border-black scale-[1.02]" : "border-black/15"}`}>
              <div className="flex items-center justify-between gap-2">
                <span className="text-[13px] font-bold flex-1">{settlement.choice.label}</span>
                <span className={`text-[11px] font-extrabold rounded-full px-2 py-0.5 shrink-0 ${badge.cls}`}>{badge.label}</span>
              </div>
            </div>
          )}

          {/* ② 카테고리별 시장 변동 */}
          {step >= 1 && (
            <div className="animate-fade-in">
              <div className="text-[12px] font-bold mb-1.5">오늘의 장</div>
              <div className="grid grid-cols-2 gap-2">
                {settlement.market.map((row) => (
                  <MarketRow key={row.category} row={row} active={step === 1} />
                ))}
              </div>
            </div>
          )}

          {/* ③ 포트폴리오 before→after 롤링 */}
          {step >= 2 && (
            <div className="animate-fade-in flex items-center justify-between text-[13px]">
              <span className="font-bold">포트폴리오</span>
              <span className="flex items-center gap-2 tabular-nums">
                <span className="text-pixel-muted line-through">{Math.round(settlement.portfolio.before).toLocaleString()}</span>
                <ArrowRight className="w-3 h-3 text-pixel-muted" />
                <span className={`font-extrabold ${settlement.portfolio.pnl_pct >= 0 ? "text-rose-600" : "text-sky-600"}`}>
                  {Math.round(portfolioValue).toLocaleString()}
                </span>
                <span className={`text-[11px] font-bold ${settlement.portfolio.pnl_pct >= 0 ? "text-rose-600" : "text-sky-600"}`}>
                  ({settlement.portfolio.pnl_pct >= 0 ? "+" : ""}{settlement.portfolio.pnl_pct.toFixed(1)}%)
                </span>
              </span>
            </div>
          )}

          {/* v3 §C1 — 원인 카드: 포트폴리오 다음, 리밸런싱 전. attribution 없으면(day 0 등) 스킵(I6). */}
          {hasAttribution && step >= attributionStep && (
            <AttributionCard attribution={settlement.attribution!} />
          )}

          {/* ④ 리스크 비중 화살표 */}
          {step >= rebalanceStep && (
            <div className="animate-fade-in">
              <div className="flex items-center justify-between text-[13px]">
                <span className="font-bold">리스크 노출</span>
                <span className="flex items-center gap-2 tabular-nums">
                  <span className="text-pixel-muted">{Math.round(settlement.rebalance.risk_share_before * 100)}%</span>
                  <ArrowRight className="w-3 h-3 text-pixel-muted" />
                  <span className="font-extrabold">{Math.round(riskAfterPct)}%</span>
                </span>
              </div>
              <p className="text-[11px] text-pixel-muted mt-1 text-right">오늘의 선택은 내일의 노출을 바꾼다</p>
            </div>
          )}

          {/* ⑤ 감정 축별 단계 이동 */}
          {step >= emoStepStart && (
            <div className="animate-fade-in">
              <div className="text-[12px] font-bold mb-1.5">
                {settlement.emotion_steps[Math.min(step - emoStepStart, settlement.emotion_steps.length - 1)]?.label ?? "감정 변화"}
              </div>
              <div className="grid grid-cols-2 gap-2">
                {AXES.map((a: Axis) => (
                  <div key={a} className="flex items-center justify-between text-[12px] bg-black/[0.03] rounded px-2 py-1">
                    <span className="text-pixel-muted">{AXIS_LABEL[a]}</span>
                    <span className="tabular-nums font-bold">{Math.round(emoRunning[a] ?? 0)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="text-[11px] text-pixel-muted text-center mt-4">화면을 눌러 계속</div>
      </PixelPanel>
    </button>
  );
}

// v3 §C1 — 원인 카드: "어제의 나에게서 온 결과". 실제 vs 어제 리밸런스 안 했을 때(counterfactual)
// pnl을 나란히 보여주고 델타를 강조한다.
function AttributionCard({ attribution }: { attribution: Attribution }) {
  const better = attribution.delta_pct >= 0;
  return (
    <div className="animate-fade-in rounded-lg border-2 border-black/15 p-3 bg-black/[0.02]">
      <div className="text-[11px] text-pixel-muted mb-2">어제의 나에게서 온 결과</div>
      <p className="text-[12.5px] leading-relaxed mb-3">{attribution.text}</p>
      <div className="flex items-center justify-between gap-3 text-[12px]">
        <div className="flex-1">
          <div className="text-pixel-muted">실제</div>
          <div className={`font-extrabold tabular-nums ${attribution.actual_pnl_pct >= 0 ? "text-rose-600" : "text-sky-600"}`}>
            {attribution.actual_pnl_pct >= 0 ? "+" : ""}{attribution.actual_pnl_pct.toFixed(1)}%
          </div>
        </div>
        <ArrowRight className="w-3 h-3 text-pixel-muted shrink-0" />
        <div className="flex-1 text-right">
          <div className="text-pixel-muted">어제 그대로였다면</div>
          <div className={`font-bold tabular-nums ${attribution.counterfactual_pnl_pct >= 0 ? "text-rose-600" : "text-sky-600"}`}>
            {attribution.counterfactual_pnl_pct >= 0 ? "+" : ""}{attribution.counterfactual_pnl_pct.toFixed(1)}%
          </div>
        </div>
      </div>
      <div className={`mt-2 text-[11px] font-bold text-right ${better ? "text-rose-600" : "text-sky-600"}`}>
        차이 {attribution.delta_pct >= 0 ? "+" : ""}{attribution.delta_pct.toFixed(1)}%p · {attribution.cause_choice_label}
      </div>
    </div>
  );
}

function MarketRow({ row, active }: { row: { category: string; pct: number; before: number; after: number }, active: boolean }) {
  const pct = useRollingNumber(row.pct, active, 900);
  const cat = row.category as Category;
  const label = CATEGORY_LABEL[cat] ?? row.category;
  return (
    <div className="flex items-center justify-between text-[12px] bg-black/[0.03] rounded px-2 py-1">
      <span className="text-pixel-muted">{label}</span>
      <span className={`font-bold tabular-nums ${row.pct > 0 ? "text-rose-600" : row.pct < 0 ? "text-sky-600" : "text-pixel-muted"}`}>
        {pct > 0 ? "+" : ""}{pct.toFixed(1)}%
      </span>
    </div>
  );
}

export default function DayReport({ data, onNext }: { data: DayReportData; onNext: () => void }) {
  // 3단계(settlement 있을 때): cascade(선택→시장→포트폴리오→리밸런싱→감정) → 취침 →
  // 리포트. settlement 없으면(I6) 기존 2단계 sleep → report.
  const [phase, setPhase] = useState<"cascade" | "sleep" | "report">(data.settlement ? "cascade" : "sleep");
  const assetDelta = Math.round(data.nextAsset) - Math.round(data.prevAsset);

  return (
    <div className="absolute inset-0 z-30 bg-black/85 flex items-center justify-center p-4 transition-opacity duration-500">
      {phase === "cascade" && data.settlement ? (
        <SettlementCascade settlement={data.settlement} onDone={() => setPhase("sleep")} />
      ) : phase === "sleep" ? (
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

          {data.choiceLabel && (
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
