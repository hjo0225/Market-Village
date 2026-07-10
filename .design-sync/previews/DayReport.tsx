import React from "react";
import { DayReport } from "market-village-frontend";

// 하루 정산 오버레이 — absolute inset-0 오버레이라 relative 컨테이너가 필요하다.
// settlement가 있으면 정산 캐스케이드(선택→시장→포트폴리오→감정)로 시작,
// 없으면 취침(암전 + 클론 한마디) 화면으로 시작한다.

const emotion = (fear: number, greed: number, anxiety: number, restlessness: number, composure: number) => ({
  fear,
  greed,
  anxiety,
  restlessness,
  composure,
});

const settlement = {
  day: 6,
  choice: { id: "c2", label: "밈코인 소문에 흔들리지 않고 비중 유지", position: 0.0 },
  market: [
    { category: "large_stable", pct: 2.1, before: 100, after: 102.1 },
    { category: "mid_alt", pct: -1.4, before: 100, after: 98.6 },
    { category: "meme", pct: 8.7, before: 100, after: 108.7 },
    { category: "stable", pct: 0.0, before: 100, after: 100 },
  ],
  portfolio: { before: 1000000, after: 1038000, pnl_pct: 3.8 },
  rebalance: { risk_share_before: 0.42, risk_share_after: 0.45 },
  emotion_steps: [
    { source: "choice", label: "선택의 여파", deltas: { greed: 4, composure: 2 } },
    { source: "market", label: "밈 급등을 지켜본 마음", deltas: { restlessness: 6, greed: 3 } },
  ],
  emotion_before: emotion(32, 48, 41, 44, 58),
  emotion_after: emotion(32, 55, 41, 50, 60),
  attribution: {
    actual_pnl_pct: 3.8,
    counterfactual_pnl_pct: 1.2,
    delta_pct: 2.6,
    cause_choice_label: "어제 밈 비중을 줄인 선택",
    text: "어제 밈 비중을 한 발 줄여둔 덕에 오늘 급등락 장에서도 손익이 덜 흔들렸다.",
  },
};

const baseData = {
  day: 6,
  name: "동동이",
  prevEmotion: emotion(32, 48, 41, 44, 58),
  nextEmotion: emotion(32, 55, 41, 50, 60),
  prevAsset: 1000000,
  nextAsset: 1038000,
  prevHoldings: { large_stable: 400000, mid_alt: 250000, meme: 100000, stable: 150000, cash: 100000 },
  nextHoldings: { large_stable: 408000, mid_alt: 246000, meme: 109000, stable: 150000, cash: 125000 },
  choiceLabel: "밈코인 소문에 흔들리지 않고 비중 유지",
  market: { large_stable: 2.1, mid_alt: -1.4, meme: 8.7, stable: 0 },
};

// 정산 캐스케이드 — "선택은 이렇게 이어졌다" 카드(첫 단계: 오늘의 선택 강조).
export const SettlementCascade = () => (
  <div style={{ position: "relative", height: 560, width: "100%" }}>
    <DayReport data={{ ...baseData, settlement, prevTier: { name: "불개미 졸업", icon: "🐜", score: 47, next_at: 55 }, nextTier: { name: "평정 수련", icon: "🧘", score: 57, next_at: 72 } }} onNext={() => {}} />
  </div>
);

// 취침 화면 — settlement 없는 폴백. 클론의 하루 끝 한마디와 함께 암전.
export const SleepScreen = () => (
  <div style={{ position: "relative", height: 420, width: "100%" }}>
    <DayReport data={baseData} onNext={() => {}} />
  </div>
);
