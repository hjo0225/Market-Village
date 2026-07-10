import React from "react";
import { Term } from "market-village-frontend";

// 용어 트리거 — 점선 밑줄 버튼. 클릭 시 앵커드 팝오버(사전 뜻)가 열린다.
// 정적 카드에선 닫힌 트리거 상태가 기본이고, OpenPopover 셀은 마운트 후 클릭으로 열어 보여준다.

// 문장 속 트리거 — 게임 나레이션 안에서 사전 용어가 점선 밑줄로 표시된다.
export const InSentence = () => (
  <div style={{ padding: 16, maxWidth: 360, fontSize: 13, lineHeight: 1.7 }}>
    <p>
      클론은 새벽 급락 알림을 보고 <Term term="패닉셀">패닉셀</Term> 직전까지 갔지만,
      결국 <Term term="관망">관망</Term>을 택했다.
    </p>
    <p style={{ marginTop: 8 }}>
      <Term term="밈코인">밈코인</Term> 비중이 커질수록 <Term term="리스크 비중">리스크 비중</Term>도
      함께 올라간다.
    </p>
  </div>
);

// children 커스텀 — 사전 키(term)와 화면 표기(children)를 다르게 쓸 수 있다.
export const CustomLabel = () => (
  <div style={{ padding: 16, maxWidth: 360, fontSize: 13, lineHeight: 1.7 }}>
    <p>
      옆집 주민이 자랑을 늘어놓자 <Term term="FOMO">포모</Term>가 스멀스멀 올라왔다.
      그래도 <Term term="익절">이익 실현</Term> 타이밍은 계획대로 가기로 했다.
    </p>
  </div>
);

// 사전에 없는 term — 트리거 없이 평문으로 그대로 렌더된다(폴백).
export const UnknownTermFallback = () => (
  <div style={{ padding: 16, maxWidth: 360, fontSize: 13, lineHeight: 1.7 }}>
    <p>
      사전에 있는 <Term term="손절">손절</Term>은 점선 밑줄,
      사전에 없는 <Term term="레버리지">레버리지</Term>는 평문 그대로.
    </p>
  </div>
);

// 열린 팝오버 — 마운트 직후 트리거를 클릭해 사전 카드(용어·뜻·게임 영향)를 보여준다.
const AutoOpen = ({ children }: { children: React.ReactNode }) => {
  const ref = React.useRef<HTMLSpanElement | null>(null);
  React.useEffect(() => {
    ref.current?.querySelector("button")?.click();
  }, []);
  return <span ref={ref}>{children}</span>;
};

export const OpenPopover = () => (
  <div style={{ position: "relative", height: 190, padding: 16, fontSize: 13 }}>
    <div style={{ marginLeft: 60, maxWidth: 300, lineHeight: 1.7 }}>
      떨어질 때마다 사 모으는 게{" "}
      <AutoOpen>
        <Term term="물타기">물타기</Term>
      </AutoOpen>
      일까, 전략일까?
    </div>
  </div>
);
