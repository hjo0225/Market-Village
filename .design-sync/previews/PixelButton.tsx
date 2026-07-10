import React from "react";
import { PixelButton } from "market-village-frontend";

// 게임 전반의 기본 액션 버튼 — 픽셀 보더 + 하드 섀도, 누르면 1px 밀림.
export const Variants = () => (
  <div style={{ display: "flex", alignItems: "center", gap: 12, padding: 16 }}>
    <PixelButton variant="primary">새 게임</PixelButton>
    <PixelButton variant="secondary">이어하기</PixelButton>
    <PixelButton variant="danger">전량 매도</PixelButton>
    <PixelButton variant="ghost">건너뛰기</PixelButton>
  </div>
);

export const Sizes = () => (
  <div style={{ display: "flex", alignItems: "center", gap: 12, padding: 16 }}>
    <PixelButton size="sm">작게</PixelButton>
    <PixelButton size="md">보통</PixelButton>
    <PixelButton size="lg">Day 2 시작</PixelButton>
  </div>
);

export const Disabled = () => (
  <div style={{ display: "flex", alignItems: "center", gap: 12, padding: 16 }}>
    <PixelButton disabled>매수 불가</PixelButton>
    <PixelButton variant="danger" disabled>
      매도 불가
    </PixelButton>
  </div>
);
