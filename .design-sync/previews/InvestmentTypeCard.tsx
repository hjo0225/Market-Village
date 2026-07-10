import React from "react";
import { InvestmentTypeCard } from "market-village-frontend";

// 투자 성향 결과 카드 스택 — 성향 헤더(권유 등급 배지) + 금투협 표준 추천상품
// + 코인 추천 + 공식 5단계 내 위치. 데이터는 backend/sim/disposition.py의
// TYPE_DESC/RISK_GRADE_BY_TYPE/SOURCE 실값을 재현. InfoHint 팝오버는 클릭
// 인터랙션이라 정적 캡처에선 트리거(ⓘ)만 보인다.

const wrap: React.CSSProperties = { width: 400 };
const SOURCE = "전국투자자교육협의회 '투자 성향 진단표' 참고해 재구성";

// 공격투자형 — 1등급(가장 위험) 상품까지 권유 가능. 5단계 표 맨 오른쪽 활성.
export const Aggressive = () => (
  <div style={wrap}>
    <InvestmentTypeCard
      onCopy={() => {}}
      onReset={() => {}}
      diagnosis={{
        answers: { Q1: 10, Q2: 4, Q3: 10, Q4: 6, Q5: 6, Q6: 6, Q7: 10 },
        raw_score: 52,
        declared_type: "공격투자형",
        type_desc: "시장 수익률을 크게 넘어서길 원한다. 자산가치 변동 손실을 적극 수용한다.",
        risk_grade: "1등급 이하",
        capacity_score: 88,
        attitude_score: 90,
        seeds: ["greed", "over", "fomo"],
        seed_conflicts: [],
        expected_bias: { loss: 0.1, fomo: 0.8, disp: 0.3, over: 0.9, panic: 0.2 },
        source: SOURCE,
      }}
    />
  </div>
);

// 위험중립형 — 가운데 단계. 균형형 추천상품(혼합형 펀드 등) 목록.
export const Neutral = () => (
  <div style={wrap}>
    <InvestmentTypeCard
      onCopy={() => {}}
      onReset={() => {}}
      diagnosis={{
        answers: { Q1: 6, Q2: 4, Q3: 6, Q4: 3, Q5: 4, Q6: 3, Q7: 6 },
        raw_score: 32,
        declared_type: "위험중립형",
        type_desc: "위험과 수익은 비례한다고 본다. 예금+α를 위해 일정 손실을 감수한다.",
        risk_grade: "3등급 이하",
        capacity_score: 52,
        attitude_score: 48,
        seeds: [],
        seed_conflicts: [],
        expected_bias: { loss: 0.4, fomo: 0.4, disp: 0.5, over: 0.4, panic: 0.4 },
        source: SOURCE,
      }}
    />
  </div>
);

// 안정형 — 5등급 이하(가장 안전) 권유. 스테이블·현금 위주 코인 추천.
export const Stable = () => (
  <div style={wrap}>
    <InvestmentTypeCard
      onCopy={() => {}}
      onReset={() => {}}
      diagnosis={{
        answers: { Q1: 2, Q2: 2, Q3: 2, Q4: 1, Q5: 2, Q6: 3, Q7: 2 },
        raw_score: 14,
        declared_type: "안정형",
        type_desc: "원금 손실을 원치 않는다. 예금 수준의 안정 수익을 기대한다.",
        risk_grade: "5등급 이하",
        capacity_score: 16,
        attitude_score: 20,
        seeds: ["composure", "loss_aversion"],
        seed_conflicts: [],
        expected_bias: { loss: 0.8, fomo: 0.2, disp: 0.6, over: 0.1, panic: 0.7 },
        source: SOURCE,
      }}
    />
  </div>
);
