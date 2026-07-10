import React from "react";
import { PixelPanel } from "market-village-frontend";

// 게임 전반의 기본 컨테이너 — 픽셀 보더(2px 검정) + 라운드 + 하드 섀도.
// tone 축: wall(#FFF) / ink(#161616) / cloud(#FFF) / path(#F2F4F7) — wall·cloud는 토큰상 동일(화이트 베이스 DS).
export const Tones = () => (
  <div style={{ display: "flex", gap: 14, padding: 16, flexWrap: "wrap", alignItems: "stretch" }}>
    <PixelPanel tone="wall" style={{ padding: 14, width: 150 }}>
      <div style={{ fontSize: 11, fontWeight: 800, opacity: 0.55, marginBottom: 4 }}>wall</div>
      <div style={{ fontSize: 13, fontWeight: 700 }}>오늘의 마을 소식</div>
      <div style={{ fontSize: 12, marginTop: 4 }}>광장에 사람이 몰리고 있다.</div>
    </PixelPanel>
    <PixelPanel tone="ink" style={{ padding: 14, width: 150 }}>
      <div style={{ fontSize: 11, fontWeight: 800, opacity: 0.55, marginBottom: 4 }}>ink</div>
      <div style={{ fontSize: 13, fontWeight: 700 }}>자산 요약</div>
      <div style={{ fontSize: 12, marginTop: 4 }}>총 평가액 1,042만 원</div>
    </PixelPanel>
    <PixelPanel tone="cloud" style={{ padding: 14, width: 150 }}>
      <div style={{ fontSize: 11, fontWeight: 800, opacity: 0.55, marginBottom: 4 }}>cloud</div>
      <div style={{ fontSize: 13, fontWeight: 700 }}>감정 일지</div>
      <div style={{ fontSize: 12, marginTop: 4 }}>오늘은 불안 지수가 낮았다.</div>
    </PixelPanel>
    <PixelPanel tone="path" style={{ padding: 14, width: 150 }}>
      <div style={{ fontSize: 11, fontWeight: 800, opacity: 0.55, marginBottom: 4 }}>path</div>
      <div style={{ fontSize: 13, fontWeight: 700 }}>Day 12</div>
      <div style={{ fontSize: 12, marginTop: 4 }}>클론이 거래소로 향한다.</div>
    </PixelPanel>
  </div>
);

// shadow 끄기 — 겹쳐 쌓는 내부 패널 등에서 섀도 없는 평면 카드로 쓴다.
export const ShadowToggle = () => (
  <div style={{ display: "flex", gap: 18, padding: 16, alignItems: "center" }}>
    <PixelPanel tone="cloud" style={{ padding: 14, width: 170 }}>
      <div style={{ fontSize: 12, fontWeight: 800 }}>shadow (기본)</div>
      <div style={{ fontSize: 12, marginTop: 4 }}>하드 오프셋 섀도 적용</div>
    </PixelPanel>
    <PixelPanel tone="cloud" shadow={false} style={{ padding: 14, width: 170 }}>
      <div style={{ fontSize: 12, fontWeight: 800 }}>shadow=false</div>
      <div style={{ fontSize: 12, marginTop: 4 }}>평면 — 보더만 남는다</div>
    </PixelPanel>
  </div>
);

// 실사용 조합 — 포트폴리오 요약 카드(잉크 헤더 + 자산 카테고리 행).
export const Composed = () => (
  <div style={{ padding: 16, maxWidth: 340 }}>
    <PixelPanel tone="cloud" style={{ overflow: "hidden" }}>
      <PixelPanel tone="ink" shadow={false} style={{ padding: "10px 14px", borderRadius: 0, borderWidth: 0, borderBottomWidth: 2 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <span style={{ fontSize: 13, fontWeight: 800 }}>클론의 포트폴리오</span>
          <span style={{ fontSize: 11, opacity: 0.7 }}>Day 12 저녁</span>
        </div>
      </PixelPanel>
      <div style={{ padding: 14, display: "flex", flexDirection: "column", gap: 8 }}>
        {[
          ["대형 안정형", "42%", "+3.1%"],
          ["중견 알트형", "23%", "-1.8%"],
          ["밈형", "8%", "+12.4%"],
          ["스테이블(USDT)", "12%", "0.0%"],
          ["현금(KRW)", "15%", "—"],
        ].map(([name, weight, chg]) => (
          <div key={name} style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
            <span style={{ fontWeight: 700 }}>{name}</span>
            <span style={{ display: "flex", gap: 10 }}>
              <span>{weight}</span>
              <span style={{ opacity: 0.6, minWidth: 44, textAlign: "right" }}>{chg}</span>
            </span>
          </div>
        ))}
      </div>
    </PixelPanel>
  </div>
);
