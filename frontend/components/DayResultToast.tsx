"use client";

import { CATEGORY_LABELS, DayResult, STAT_LABELS } from "@/lib/api";

const FUND_FLOW_LABEL: Record<string, string> = {
  to_cash: "공포 매도 → 현금 도피",
  to_stable: "공포 매도 → 스테이블 이동",
  to_hotter: "충동 추격 → 급등 종목에 새로 태움",
  concentrate: "몰빵 → 기존 포지션 더 매수",
  hold_winner: "익절 거부 → 계속 보유",
};

export default function DayResultToast({ result, scene }: { result: DayResult | null; scene: string }) {
  if (!result) return null;
  const calm = result.trap === null;
  const bundled = result.bundle.length > 1;   // T-216 — 같은 날 2종목 이상 동시 트리거
  return (
    <div className="fixed bottom-6 right-6 z-[110] max-w-sm animate-slide-up">
      <div className={`border-2 border-black rounded-2xl shadow-pixel-lg p-4 ${calm ? "bg-white" : result.swayed ? "bg-yellow-50" : "bg-green-50"}`}>
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
        {/* 사용자 피드백(2026-07-01) — 클론 상태는 리모콘 뒤로 숨기되, 하루마무리(여기)에선 보여준다. */}
        <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 mt-2 pt-2 border-t border-black/10">
          {STAT_LABELS.map((k) => (
            <div key={k} className="flex items-center justify-between text-[10px]">
              <span className="text-pixel-muted">{k}</span>
              <span className="font-bold">{Math.round(result.stats[k] ?? 0)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
