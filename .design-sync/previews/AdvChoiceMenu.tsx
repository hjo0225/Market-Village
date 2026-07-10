import React from "react";
import { AdvChoiceMenu } from "market-village-frontend";

// T-31/T-32 — ADV choice 스크린(선택 메뉴). say 박스와 분리되어 맵 위에
// 오버레이되는 창형 메뉴. 각 선택지 아래 감정 축(공포/탐욕/불안/조급/평정)
// 델타 칩이 붙는다. 셀은 맵 느낌 그라디언트 배경 위에 중앙 배치(인라인 스타일).

const scene = (bg: string): React.CSSProperties => ({
  position: "relative",
  minHeight: 250,
  borderRadius: 12,
  padding: 16,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  background: bg,
});

// chain 톤(기본) — NPC 만남 선택지 3개, 감정 델타 칩 방향(▲rose/▼sky) 비교.
export const ChainChoices = () => (
  <div style={scene("linear-gradient(180deg, #86c95c 0%, #5aa73c 60%, #417d2e 100%)")}>
    <AdvChoiceMenu
      onChoose={() => {}}
      choices={[
        { id: "add_buy", label: "지금이라도 따라 산다", deltas: { greed: 8, restlessness: 4 } },
        { id: "hold", label: "계획대로 관망한다", deltas: { composure: 6, anxiety: -4 } },
        { id: "sell_half", label: "절반만 익절한다", deltas: { composure: 4, fear: -3 } },
      ]}
    />
  </div>
);

// board 톤 — 게시판 여론 대응. 첫 선택지는 클론 성향의 본능 액션(T-64 ⚡배지).
export const BoardInstinctChoices = () => (
  <div style={scene("linear-gradient(180deg, #475569 0%, #1f2937 100%)")}>
    <AdvChoiceMenu
      tone="board"
      onChoose={() => {}}
      choices={[
        { id: "fomo_buy", label: "나도 올라탄다", instinct: true, deltas: { greed: 10, restlessness: 6 } },
        { id: "comment_watch", label: "댓글만 달고 관망", deltas: { anxiety: 4 } },
        { id: "partial_sell", label: "과열이다 — 일부 정리", deltas: { composure: 8, greed: -6 } },
      ]}
    />
  </div>
);

// dilemma 톤 + busy — 선택 전송 중 비활성(50% 투명) 상태. hover는 정적 캡처 불가.
export const DilemmaBusy = () => (
  <div style={scene("linear-gradient(180deg, #1e2740 0%, #0f1424 100%)")}>
    <AdvChoiceMenu
      tone="dilemma"
      busy
      onChoose={() => {}}
      choices={[
        { id: "take_profit", label: "절반 익절하고 마음의 평화", deltas: { composure: 8, greed: -4 } },
        { id: "let_ride", label: "끝까지 간다", deltas: { greed: 12, anxiety: 6 } },
      ]}
    />
  </div>
);
