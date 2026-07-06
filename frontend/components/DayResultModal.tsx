"use client";

import PixelButton from "@/components/pixel/PixelButton";
import { TradeStory } from "@/components/PhoneModal";
import { CATEGORY_LABELS, DayResult, FUND_FLOW_LABELS as FUND_FLOW_LABEL, STAT_LABELS } from "@/lib/api";

// T-306 — 종목별 한눈 보기(포트폴리오 4유형 + 현금).
const CAT_ICONS: Record<string, string> = {
  large_stable: "🏛", mid_alt: "🚀", meme: "🐕", stable: "🪙",
};
const pctTxt = (v: number) => `${v > 0 ? "+" : ""}${v}%`;

// T-261(사용자 피드백 2026-07-03) — 하루 마무리는 우하단 토스트가 아니라 블로킹
// 모달: 맵 연출 중엔 토스트가 안 보여 "하루 결과가 안 나온다"로 인지됐다.
// 내용은 구 DayResultToast 그대로, 닫아야 다음 조작이 자연스럽다.
export default function DayResultModal({ result, scene, day, onClose }:
  { result: DayResult | null; scene: string; day: number; onClose: () => void }) {
  if (!result) return null;
  const calm = result.trap === null;
  const bundled = result.bundle.length > 1;   // T-216 — 같은 날 2종목 이상 동시 트리거
  return (
    <div role="dialog" aria-modal="true" className="fixed inset-0 z-[120] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-pixel-ink/60" />
      <div className={`relative w-full max-w-sm border-2 border-black rounded-2xl shadow-pixel-lg p-4 animate-pixel-pop ${calm ? "bg-white" : result.swayed ? "bg-yellow-50" : "bg-green-50"}`}>
        <p className="text-[11px] text-pixel-muted font-bold mb-1">🌙 Day {day} 마무리</p>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-lg animate-bump">{calm ? "🌤" : result.swayed ? "😵" : "💪"}</span>
          <span className="font-extrabold text-sm">
            {calm ? "평온한 하루" : bundled
              ? `함정 ${result.bundle.length}건 동시 발생`
              : `함정 ${result.trap} — ${result.swayed ? "휘둘림" : "버팀"}`}
          </span>
        </div>
        {bundled ? (
          <div className="flex flex-col gap-1 mb-1">
            {result.bundle.map((b) => (
              <p key={b.category} className="text-xs text-pixel-muted">
                {CATEGORY_LABELS[b.category] ?? b.category} · {b.trap_name} —{" "}
                <span className={b.resisted ? "text-pixel-greenText font-bold" : "text-pixel-danger font-bold"}>
                  {b.resisted ? "버팀" : "휘둘림"}
                </span>
                {!b.resisted && b.fund_flow && ` (${FUND_FLOW_LABEL[b.fund_flow] ?? b.fund_flow})`}
              </p>
            ))}
          </div>
        ) : (
          !calm && result.swayed && (
            <p className="text-xs text-pixel-muted mb-1">{FUND_FLOW_LABEL[result.fund_flow] ?? result.fund_flow}</p>
          )
        )}
        {scene && <p className="text-xs italic text-pixel-greenText mb-2">💭 {scene}</p>}
        {/* T-301(사용자) — 매매 서사: 감정 원인→행동→시세→수익률을 정산에서 바로 */}
        {result.trade && (
          <div className="mb-1 rounded-lg border border-black/15 bg-white/70 px-2 py-1.5">
            <TradeStory trade={result.trade} day={day} />
            {/* T-306 — 포트폴리오 한눈 보기: 종목별 시세 등락 + 내 보유 비중 */}
            {result.trade.assets && result.trade.assets.length > 0 && (() => {
              const cash = result.trade!.cash ?? 0;
              const total = result.trade!.assets!.reduce((s, a) => s + a.value, 0) + cash;
              return (
                <div className="mt-1.5 pt-1.5 border-t border-black/10 flex flex-col gap-0.5">
                  {result.trade!.assets!.map((a) => (
                    <div key={a.category} className="flex items-center justify-between text-[11px]">
                      <span>{CAT_ICONS[a.category] ?? "📦"} {CATEGORY_LABELS[a.category] ?? a.category}</span>
                      <span className="tabular-nums">
                        <b className={a.price_pct > 0 ? "text-pixel-greenText" : a.price_pct < 0 ? "text-pixel-danger" : "text-pixel-muted"}>
                          {day === 0 ? "—" : pctTxt(a.price_pct)}
                        </b>
                        <span className="text-pixel-muted"> · 내 비중 {total > 0 ? Math.round((a.value / total) * 100) : 0}%</span>
                      </span>
                    </div>
                  ))}
                  {cash > 0 && (
                    <div className="flex items-center justify-between text-[11px] text-pixel-muted">
                      <span>💵 현금</span>
                      <span className="tabular-nums">내 비중 {total > 0 ? Math.round((cash / total) * 100) : 0}%</span>
                    </div>
                  )}
                </div>
              );
            })()}
            {result.npc_trades && result.npc_trades.length > 0 && (
              <p className="text-[10px] text-pixel-muted mt-1">
                💱 마을: {result.npc_trades.filter((t) => t.action === "buy").map((t) => t.name).join("·") || "—"} 매수
                {" / "}{result.npc_trades.filter((t) => t.action === "sell").map((t) => t.name).join("·") || "—"} 매도
              </p>
            )}
          </div>
        )}
        <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 mt-2 pt-2 border-t border-black/10">
          {STAT_LABELS.map((k) => (
            <div key={k} className="flex items-center justify-between text-[10px]">
              <span className="text-pixel-muted">{k}</span>
              <span className="font-bold">{Math.round(result.stats[k] ?? 0)}</span>
            </div>
          ))}
        </div>
        <div className="mt-3 flex justify-end">
          <PixelButton size="sm" onClick={onClose}>확인</PixelButton>
        </div>
      </div>
    </div>
  );
}
