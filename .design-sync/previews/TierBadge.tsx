import React from "react";
import { TierBadge } from "market-village-frontend";

// 헤더의 감정 통제 티어 배지 — 아이콘 + 이름 + 다음 티어까지 진행 게이지.
// 티어 표는 backend/sim/tier.py의 실제 5단계.
export const Levels = () => (
  <div style={{ display: "flex", flexDirection: "column", gap: 10, padding: 16 }}>
    <TierBadge tier={{ name: "새싹", icon: "🌱", score: 21, next_at: 35 }} />
    <TierBadge tier={{ name: "불개미 졸업", icon: "🐜", score: 47, next_at: 55 }} />
    <TierBadge tier={{ name: "평정 수련", icon: "🧘", score: 63, next_at: 72 }} />
    <TierBadge tier={{ name: "강철 멘탈", icon: "🛡️", score: 80, next_at: 88 }} />
  </div>
);

// 최고 티어(next_at 없음)는 게이지가 가득 찬다.
export const MaxTier = () => (
  <div style={{ padding: 16 }}>
    <TierBadge tier={{ name: "마을의 현자", icon: "🧙", score: 93, next_at: null }} />
  </div>
);
