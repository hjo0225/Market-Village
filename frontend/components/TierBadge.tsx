"use client";

import { Tier } from "@/lib/emoApi";

// v3 §C2 — 헤더 티어 배지 + next_at까지 진행 게이지. tier가 없으면(구버전 폴백)
// 렌더 안 함(I6, 호출부 가드). 티어 상승 토스트는 상위(emo/page.tsx)에서 관리.
export default function TierBadge({ tier, className = "" }: { tier: Tier; className?: string }) {
  // next_at이 없으면(최종 티어) 게이지를 꽉 채운다.
  const pct = tier.next_at != null && tier.next_at > 0
    ? Math.max(0, Math.min(100, (tier.score / tier.next_at) * 100))
    : 100;
  return (
    <span className={`inline-flex items-center gap-1.5 text-[11px] font-bold ${className}`}>
      <span className="shrink-0">{tier.icon} {tier.name}</span>
      <span className="w-12 h-1.5 rounded-full bg-black/10 overflow-hidden border border-black/10" aria-hidden>
        <span className="block h-full bg-amber-500 transition-all duration-500" style={{ width: `${pct}%` }} />
      </span>
    </span>
  );
}
