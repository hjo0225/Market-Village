import React from "react";
import { EmotionGauge } from "market-village-frontend";

// 포트폴리오 팝오버의 감정 5축 게이지 — 함정 4축(공포/탐욕/불안/조급) + 긍정 '평정'.
// verdict는 backend player_emotion.verdict의 3분기: 과열 / 위축 / 중립.

// 평온한 날 — 부정 축 낮고 평정 높음, 판정 중립.
export const CalmDay = () => (
  <div style={{ maxWidth: 340, padding: 16 }}>
    <EmotionGauge
      emotion={{ fear: 18, greed: 22, anxiety: 20, restlessness: 15, composure: 74 }}
      verdict="중립"
    />
  </div>
);

// 탐욕 폭주 — 밈코인 급등을 지켜본 다음 날. 탐욕·조급이 치솟고 평정이 무너짐.
export const GreedRush = () => (
  <div style={{ maxWidth: 340, padding: 16 }}>
    <EmotionGauge
      emotion={{ fear: 12, greed: 84, anxiety: 38, restlessness: 72, composure: 26 }}
      verdict="과열"
    />
  </div>
);

// 공포 장세 — 연속 하락 후. 공포·불안이 지배하고 판정 위축.
export const FearMarket = () => (
  <div style={{ maxWidth: 340, padding: 16 }}>
    <EmotionGauge
      emotion={{ fear: 86, greed: 8, anxiety: 78, restlessness: 55, composure: 21 }}
      verdict="위축"
    />
  </div>
);

// verdict 없이(구버전 폴백) — 배지 없이 게이지만.
export const NoVerdict = () => (
  <div style={{ maxWidth: 340, padding: 16 }}>
    <EmotionGauge emotion={{ fear: 44, greed: 51, anxiety: 47, restlessness: 40, composure: 49 }} />
  </div>
);
