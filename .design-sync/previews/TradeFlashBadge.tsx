import React from "react";
import { TradeFlashBadge } from "market-village-frontend";

// 클론 매매 플래시 배지 — absolute inset-x-0 top-[16%] 오버레이 + animate-pulse.
// 앱에서는 1.8초 뒤 사라지지만 프리뷰에서는 relative 컨테이너에 고정해 정적 노출.
// pulse 키프레임은 t=0에 opacity 1이라 캡처 프레임에서 항상 보인다.

const stage: React.CSSProperties = {
  position: "relative",
  height: 150,
  background: "#e8f4e8",
  border: "1px solid rgba(0,0,0,0.1)",
  borderRadius: 12,
  overflow: "hidden",
};

// 매수 플래시 — 게시판 여론에 올라타 클론이 코인을 사들일 때(rose 톤).
export const Buy = () => (
  <div style={{ padding: 16 }}>
    <div style={stage}>
      <TradeFlashBadge action="buy" />
    </div>
  </div>
);

// 매도 + 사유 — 현금화 딜레마 선택 라벨이 detail로 붙는다(sky 톤).
export const SellWithDetail = () => (
  <div style={{ padding: 16 }}>
    <div style={stage}>
      <TradeFlashBadge action="sell" detail="수익 실현하고 절반을 현금으로 옮겼다" />
    </div>
  </div>
);

// 매수 + 사유 — 밈 급등 소문에 올라탄 추격 매수.
export const BuyWithDetail = () => (
  <div style={{ padding: 16 }}>
    <div style={stage}>
      <TradeFlashBadge action="buy" detail="DOGE 급등 소문에 밈 비중을 늘렸다" />
    </div>
  </div>
);
