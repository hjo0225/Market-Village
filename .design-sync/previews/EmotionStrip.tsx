import React from "react";
import { EmotionStrip } from "market-village-frontend";

// 상단 헤더 상시 노출용 슬림 감정 5축 스트립. 배경이 투명이라 앱 헤더 톤의
// 밝은 배경 위에 올려 보여준다. flash=축 이름이면 그 축 막대가 pulse.

const wrap: React.CSSProperties = {
  padding: "10px 14px",
  background: "#fdf6e3",
  border: "1px solid rgba(0,0,0,0.12)",
  borderRadius: 10,
  display: "inline-block",
};

// 평온한 날 — 게임 초반의 안정적인 마음 상태.
export const Baseline = () => (
  <div style={{ padding: 16 }}>
    <div style={wrap}>
      <EmotionStrip emotion={{ fear: 20, greed: 25, anxiety: 22, restlessness: 18, composure: 70 }} />
    </div>
  </div>
);

// 공포 스파이크 — 급락 직후, fear 축이 델타 플래시(pulse) 중.
export const FearFlash = () => (
  <div style={{ padding: 16 }}>
    <div style={wrap}>
      <EmotionStrip
        emotion={{ fear: 82, greed: 12, anxiety: 74, restlessness: 60, composure: 24 }}
        flash="fear"
      />
    </div>
  </div>
);

// 탐욕 폭주 — 밈 급등 소식에 greed 축이 플래시 중.
export const GreedFlash = () => (
  <div style={{ padding: 16 }}>
    <div style={wrap}>
      <EmotionStrip
        emotion={{ fear: 10, greed: 88, anxiety: 35, restlessness: 76, composure: 22 }}
        flash="greed"
      />
    </div>
  </div>
);
