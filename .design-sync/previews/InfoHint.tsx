import React from "react";
import { InfoHint } from "market-village-frontend";

// 코인 입문자용 (i) 아이콘 팝오버 — 닫힌 상태는 라벨 옆의 작은 정보 아이콘.
// props(title/text)는 열린 카드에 들어가므로, OpenPopover 셀에서 마운트 후 클릭으로 열어 보여준다.

// 라벨 옆 인라인 — 지표·수치 라벨에 붙는 실사용 형태. 아이콘은 흐린 회색(hover 시 진해짐).
export const InlineWithLabels = () => (
  <div style={{ padding: 16, maxWidth: 340, display: "flex", flexDirection: "column", gap: 12, fontSize: 13 }}>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontWeight: 700 }}>
        리스크 비중 <InfoHint title="리스크 비중" text="전체 자산 중 가격이 출렁이는 코인의 비율. 높을수록 시장이 움직일 때 내 자산도 크게 움직여요." />
      </span>
      <span style={{ fontWeight: 800 }}>62%</span>
    </div>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontWeight: 700 }}>
        평가손익 <InfoHint title="평가손익" text="아직 팔지 않은 상태의 이익/손실. 팔기 전까지는 숫자일 뿐이에요." />
      </span>
      <span style={{ fontWeight: 800 }}>+184,200원</span>
    </div>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontWeight: 700 }}>
        불안 게이지 <InfoHint text="클론이 느끼는 불안의 정도. 급락일에 오르고, 평온한 날 서서히 내려가요." />
      </span>
      <span style={{ fontWeight: 800 }}>34 / 100</span>
    </div>
  </div>
);

// 열린 팝오버 — 마운트 직후 클릭으로 열어 title+text 카드를 보여준다.
const AutoOpen = ({ children }: { children: React.ReactNode }) => {
  const ref = React.useRef<HTMLSpanElement | null>(null);
  React.useEffect(() => {
    ref.current?.querySelector("button")?.click();
  }, []);
  return <span ref={ref}>{children}</span>;
};

export const OpenPopover = () => (
  <div style={{ position: "relative", height: 170, padding: 16, fontSize: 13 }}>
    <div style={{ marginLeft: 120, display: "inline-flex", alignItems: "center", gap: 4, fontWeight: 700 }}>
      스테이블(USDT){" "}
      <AutoOpen>
        <InfoHint title="스테이블코인" text="1달러에 고정되도록 설계된 코인. 가격이 거의 안 움직이는 대피처예요." />
      </AutoOpen>
    </div>
  </div>
);

// 제목 없는 카드 — title을 생략하면 본문 텍스트만 있는 얇은 카드가 열린다.
export const OpenNoTitle = () => (
  <div style={{ position: "relative", height: 140, padding: 16, fontSize: 13 }}>
    <div style={{ marginLeft: 120, display: "inline-flex", alignItems: "center", gap: 4, fontWeight: 700 }}>
      관망 일수{" "}
      <AutoOpen>
        <InfoHint text="사지도 팔지도 않고 지켜본 날의 수. 아무것도 안 하는 것도 선택이에요." />
      </AutoOpen>
    </div>
  </div>
);
