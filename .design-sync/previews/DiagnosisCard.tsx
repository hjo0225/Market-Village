import React from "react";
import { DiagnosisCard } from "market-village-frontend";

// v3 §D1 — 설문 직후 진단 결과 화면(min-h-screen 풀스크린 레이아웃 그대로).
// 데이터는 backend/sim/diagnosis_report.py의 실제 산출 형태를 재현:
// axes = 감당 능력/위험 감수 태도(0~100), contributions = 문항→선택→축 점수 역추적,
// summary = 유형별 2줄 + 공통 마무리 문장.
// "왜냐하면" 접기 목록은 기본 접힘(useState) — 펼친 상태는 정적 캡처 불가, 접힌 토글만 보인다.

// 공격투자형 — 고득점 답안(원 진단표 컷오프 45점 이상)의 진단 결과.
export const AggressiveResult = () => (
  <DiagnosisCard
    onConfirm={() => {}}
    diagnosis={{
      declared_type: "공격투자형",
      axes: [
        { axis: "capacity", label: "감당 능력", score: 88, max: 100 },
        { axis: "attitude", label: "위험 감수 태도", score: 90, max: 100 },
      ],
      contributions: [
        { q: "Q1", q_label: "여유자금 1,000만 원이 생겼다. 예금과 코인에 나눈다면?", choice_label: "코인 1,000만 원", axis: "capacity", points: 10 },
        { q: "Q2", q_label: "이 자금을 얼마 동안 굴릴 생각이야?", choice_label: "1년 이상 ~ 3년 미만", axis: "attitude", points: 4 },
        { q: "Q3", q_label: "매달 남는 100만 원을 적금과 코인 적립에 나눈다면?", choice_label: "코인 100만 원", axis: "capacity", points: 10 },
        { q: "Q4", q_label: "자산관리에서 내가 우선하는 순서는?", choice_label: "수익성 > 유동성 > 안전성", axis: "attitude", points: 6 },
        { q: "Q5", q_label: "가장 선호하는 자산은?", choice_label: "신규 · 알트코인", axis: "attitude", points: 6 },
        { q: "Q6", q_label: "더 선호하는 투자 전략은?", choice_label: "원금 손실 위험이 있어도 시장 평균보다 높은 수익", axis: "attitude", points: 6 },
        { q: "Q7", q_label: "투자 손실을 어디까지 견딜 수 있어?", choice_label: "기대수익이 높다면 위험은 상관없다", axis: "capacity", points: 10 },
      ],
      summary: [
        "전액을 걸어도 괜찮다고 말할 만큼 공격적입니다.",
        "태도가 아니라 규율이 당신의 진짜 승부처입니다.",
        "클론은 이 성향대로 열흘을 산다. 진짜 당신과 같은지는, 끝에 확인하자.",
      ],
    }}
  />
);

// 안정형 — 저득점 답안(20점 이하)의 진단 결과. 축 바가 낮게 깔린다.
export const StableResult = () => (
  <DiagnosisCard
    onConfirm={() => {}}
    diagnosis={{
      declared_type: "안정형",
      axes: [
        { axis: "capacity", label: "감당 능력", score: 16, max: 100 },
        { axis: "attitude", label: "위험 감수 태도", score: 20, max: 100 },
      ],
      contributions: [
        { q: "Q1", q_label: "여유자금 1,000만 원이 생겼다. 예금과 코인에 나눈다면?", choice_label: "예금 1,000만 원", axis: "capacity", points: 2 },
        { q: "Q2", q_label: "이 자금을 얼마 동안 굴릴 생각이야?", choice_label: "1개월 이상 ~ 6개월 미만", axis: "attitude", points: 2 },
        { q: "Q3", q_label: "매달 남는 100만 원을 적금과 코인 적립에 나눈다면?", choice_label: "적금 100만 원", axis: "capacity", points: 2 },
        { q: "Q4", q_label: "자산관리에서 내가 우선하는 순서는?", choice_label: "안전성 > 유동성 > 수익성", axis: "attitude", points: 1 },
        { q: "Q5", q_label: "가장 선호하는 자산은?", choice_label: "예금 · 스테이블코인", axis: "attitude", points: 2 },
        { q: "Q6", q_label: "더 선호하는 투자 전략은?", choice_label: "분산된 포트폴리오로 시장 평균 정도의 성과", axis: "attitude", points: 3 },
        { q: "Q7", q_label: "투자 손실을 어디까지 견딜 수 있어?", choice_label: "무슨 일이 있어도 원금은 지켜야 한다", axis: "capacity", points: 2 },
      ],
      summary: [
        "당신은 원금을 지키는 것을 최우선으로 둡니다.",
        "손실보다, 남들이 벌 때 조급해지는 순간이 진짜 시험대입니다.",
        "클론은 이 성향대로 열흘을 산다. 진짜 당신과 같은지는, 끝에 확인하자.",
      ],
    }}
  />
);
