import React from "react";
import { AdvDialogue } from "market-village-frontend";

// T-31/T-32 — ADV say 스크린(대사 텍스트박스). 맵 위 하단 오버레이라 각 셀을
// 맵 느낌의 그라디언트 배경 위에 얹는다(인라인 스타일).
// 초상 이미지는 프리뷰 서버에서 404가 나므로 speakerId 대신 speakerName만 넘겨
// 색배경+이니셜 폴백 아바타(T-42 폴백 경로)를 결정론적으로 렌더한다.

const scene = (bg: string, minHeight = 230): React.CSSProperties => ({
  position: "relative",
  minHeight,
  borderRadius: 12,
  padding: 16,
  display: "flex",
  flexDirection: "column",
  justifyContent: "flex-end",
  background: bg,
});

// chain 톤(기본) — 마을 맵 위 NPC 대사. 이름 + 역할 라벨 + 여러 줄 대사.
export const ChainSay = () => (
  <div style={scene("linear-gradient(180deg, #86c95c 0%, #5aa73c 60%, #417d2e 100%)")}>
    <AdvDialogue
      speakerName="동수"
      role="겁 많은 개미"
      text={"어, 어제 산 게 벌써 -12%야…\n지금이라도 던져야 하나. 너라면 어떻게 할 거야?"}
    />
  </div>
);

// board 톤 — 게시판 글은 종이 카드(흰 배경 + @닉네임)로 보이는 분기.
export const BoardPost = () => (
  <div style={scene("linear-gradient(180deg, #475569 0%, #1f2937 100%)")}>
    <AdvDialogue
      speakerName="해나"
      title="자유게시판 · 오늘의 화제글"
      tone="board"
      text={"도지 오늘만 +8.7%… 존버가 답이었네.\n아직 안 탄 사람 있음? 지금이라도 늦지 않았다 가즈아!"}
    />
  </div>
);

// dilemma 톤 — 화자 없는 내레이션. 이름이 비면 "?" 아바타 폴백이 뜬다.
export const DilemmaNarration = () => (
  <div style={scene("linear-gradient(180deg, #1e2740 0%, #0f1424 100%)")}>
    <AdvDialogue
      title="밤의 갈림길"
      tone="dilemma"
      text={"지갑을 열자 어제의 수익이 보인다.\n여기서 절반을 익절하면 마음은 편해진다. 하지만 내일 더 오른다면?"}
    />
  </div>
);
