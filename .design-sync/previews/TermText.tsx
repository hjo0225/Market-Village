import React from "react";
import { TermText } from "market-village-frontend";

// 데이터 문자열(선택지 라벨·이벤트 문구)에서 사전 키 첫 등장만 자동으로
// <Term> 트리거(점선 밑줄)로 감싼다. 기본 최대 2개 — 밑줄 범벅 방지.

// 선택지 라벨 — 실제 게임 선택지 문자열이 그대로 들어오고, 용어만 밑줄이 된다.
export const ChoiceLabels = () => (
  <div style={{ padding: 16, maxWidth: 380, display: "flex", flexDirection: "column", gap: 10, fontSize: 13 }}>
    <div style={{ border: "2px solid #161616", borderRadius: 10, padding: "8px 12px", background: "#fff" }}>
      <TermText text="밈코인 전량 익절하고 오늘은 관망한다" />
    </div>
    <div style={{ border: "2px solid #161616", borderRadius: 10, padding: "8px 12px", background: "#fff" }}>
      <TermText text="패닉셀 대신 스테이블코인으로 절반만 대피" />
    </div>
    <div style={{ border: "2px solid #161616", borderRadius: 10, padding: "8px 12px", background: "#fff" }}>
      <TermText text="물타기로 평균 단가를 낮추고 존버 계속" />
    </div>
  </div>
);

// maxTerms 축 — 같은 문장에서 감싸는 용어 수를 1 → 2 → 4로 조절.
export const MaxTermsAxis = () => (
  <div style={{ padding: 16, maxWidth: 420, display: "flex", flexDirection: "column", gap: 10, fontSize: 13, lineHeight: 1.7 }}>
    <div>
      <span style={{ fontSize: 11, fontWeight: 800, opacity: 0.5, marginRight: 8 }}>maxTerms=1</span>
      <TermText text="손절이냐 존버냐, 아니면 현금화냐 — 알트코인 앞에서 셋 다 고민된다" maxTerms={1} />
    </div>
    <div>
      <span style={{ fontSize: 11, fontWeight: 800, opacity: 0.5, marginRight: 8 }}>maxTerms=2 (기본)</span>
      <TermText text="손절이냐 존버냐, 아니면 현금화냐 — 알트코인 앞에서 셋 다 고민된다" />
    </div>
    <div>
      <span style={{ fontSize: 11, fontWeight: 800, opacity: 0.5, marginRight: 8 }}>maxTerms=4</span>
      <TermText text="손절이냐 존버냐, 아니면 현금화냐 — 알트코인 앞에서 셋 다 고민된다" maxTerms={4} />
    </div>
  </div>
);

// 사전 키 없는 문장 — 트리거 없이 평문 그대로 통과(폴백).
export const NoMatchFallback = () => (
  <div style={{ padding: 16, maxWidth: 380, fontSize: 13, lineHeight: 1.7 }}>
    <TermText text="오늘 마을 광장은 조용했다. 클론은 평소처럼 아침 산책을 나갔다." />
  </div>
);
