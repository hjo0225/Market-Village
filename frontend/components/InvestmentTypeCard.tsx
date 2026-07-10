"use client";

import { BadgeCheck, Copy, RotateCcw, ShieldCheck } from "lucide-react";
import { DispositionDiagnosis } from "@/lib/emoApi";
import PixelButton from "@/components/pixel/PixelButton";
import InfoHint from "@/components/InfoHint";

const RISK_ROWS: [string, string][] = [
  ["안정형", "5등급 이하"],
  ["안정추구형", "4등급 이하"],
  ["위험중립형", "3등급 이하"],
  ["적극투자형", "2등급 이하"],
  ["공격투자형", "1등급 이하"],
];

// 금융투자협회 표준 투자권유준칙의 성향별 추천 금융상품 (상위등급 고객은 하위등급 추천상품 포함)
const TYPE_GUIDE: Record<string, { friendly: string; products: string[]; coins: string[] }> = {
  안정형: {
    friendly: "원금은 꼭 지키고 싶은 타입이에요. 예금처럼 안전한 상품이 잘 맞아요.",
    products: ["예금 · 현금성 자산", "RP", "국고채 · 통안채 · 지방채 · 특수채", "AA등급 이상 회사채", "6등급(매우 낮은 위험) 펀드"],
    coins: ["스테이블코인(USDT · USDC)", "현금 비중 유지"],
  },
  안정추구형: {
    friendly: "안전을 우선하되, 예금보다 조금 나은 수익도 노려보는 타입이에요.",
    products: ["A- 등급 이상 금융채 · 회사채", "원금보장 ELB · DLB", "채권형 펀드", "5등급(낮은 위험) 펀드"],
    coins: ["스테이블코인 위주", "비트코인 소액 적립"],
  },
  위험중립형: {
    friendly: "수익과 안전 사이에서 균형을 잡는 타입이에요. 적당한 위험은 감수할 수 있어요.",
    products: ["채권혼합형 · 주식혼합형 펀드", "공모주 펀드", "회사채 · CP · 전단채 · 후순위채권", "4등급(보통 위험) 펀드"],
    coins: ["비트코인 · 이더리움 같은 대장주 중심", "스테이블코인으로 안전판 확보"],
  },
  적극투자형: {
    friendly: "수익을 위해 어느 정도 손실 위험은 받아들이는 타입이에요.",
    products: ["주식 직접투자 · 주식형 펀드", "ETF · ELS · DLS", "주식형 랩어카운트", "하이일드 펀드", "2~3등급(높은 위험) 펀드"],
    coins: ["대장주 + 중견 알트코인 혼합", "알트코인은 일부 비중만"],
  },
  공격투자형: {
    friendly: "높은 수익을 위해 큰 위험도 감수하는 타입이에요. 손실 가능성도 그만큼 커요.",
    products: ["BB 이하 투기등급 회사채", "해외주식 투자", "레버리지 ETF", "1등급(매우 높은 위험) 펀드"],
    coins: ["알트코인 · 신규 코인", "밈코인 (급등급락 각오!)"],
  },
};

interface Props {
  diagnosis: DispositionDiagnosis;
  onCopy: () => void;
  onReset: () => void;
}

export default function InvestmentTypeCard({ diagnosis, onCopy, onReset }: Props) {
  const shareText = `내 투자 성향은 ${diagnosis.declared_type} (권유 등급 ${diagnosis.risk_grade})`;
  const guide = TYPE_GUIDE[diagnosis.declared_type];

  return (
    <div className="flex flex-col gap-3">
      <section className="border-2 border-black rounded-xl bg-[#fff7d6] shadow-pixel-md p-4 animate-card-reveal">
        <div className="text-[11px] font-extrabold text-black/55">내 투자 성향</div>
        <div className="mt-1 flex items-end justify-between gap-3">
          <h2 className="text-3xl font-black leading-none">{diagnosis.declared_type}</h2>
          <div className="flex items-center gap-1 rounded-lg border-2 border-black bg-[#76d672] px-2.5 py-1 text-[11px] font-black">
            권유 등급 {diagnosis.risk_grade}
            <InfoHint
              title="권유 등급이란?"
              text="금융상품은 위험도에 따라 1등급(가장 위험)부터 6등급(가장 안전)으로 나뉘어요. 이 성향에는 표시된 등급까지, 즉 그보다 안전한 상품을 권할 수 있다는 뜻입니다."
            />
          </div>
        </div>
        {guide && (
          <p className="mt-2 text-[12px] leading-relaxed font-bold">{guide.friendly}</p>
        )}
        <p className="mt-2.5 text-[12px] leading-relaxed font-semibold">{diagnosis.type_desc}</p>
        <div className="mt-2.5 grid grid-cols-2 gap-2 text-[11px]">
          <div className="rounded-lg border border-black/20 bg-white/70 px-2 py-1.5">
            감당 능력 <b>{diagnosis.capacity_score}</b>{" "}
            <InfoHint
              title="감당 능력이란?"
              text="나이·수입·투자 가능 기간처럼 객관적인 형편으로 볼 때, 손실이 나도 버틸 수 있는 정도를 뜻해요."
            />
          </div>
          <div className="rounded-lg border border-black/20 bg-white/70 px-2 py-1.5">
            감수 태도 <b>{diagnosis.attitude_score}</b>{" "}
            <InfoHint
              title="감수 태도란?"
              text="손실이 났을 때 마음이 얼마나 편한지, 즉 위험을 스스로 받아들이려는 성향의 정도를 뜻해요."
            />
          </div>
        </div>
      </section>

      {guide && (
        <section className="rounded-xl border-2 border-black bg-white p-3 shadow-pixel-sm animate-card-reveal">
          <div className="mb-2 flex items-center gap-1.5 text-[12px] font-black">
            <BadgeCheck className="h-4 w-4" />
            투자를 한다면 이런 상품이 어울려요
            <InfoHint
              title="추천 금융상품"
              text="금융투자협회 표준 투자권유준칙에서 성향별로 권할 수 있다고 정한 상품이에요. 내 성향보다 안전한(숫자가 큰 등급) 상품은 언제든 선택할 수 있어요."
            />
          </div>
          <ul className="flex flex-col gap-1">
            {guide.products.map((p) => (
              <li
                key={p}
                className="rounded-lg border border-black/15 bg-[#f6f9f2] px-2.5 py-1.5 text-[11px] font-semibold"
              >
                {p}
              </li>
            ))}
          </ul>
          <div className="mt-2.5 mb-1.5 flex items-center gap-1.5 text-[11px] font-black text-black/70">
            🪙 코인이라면?
            <InfoHint
              title="코인 추천"
              text="코인은 공식 분류엔 없는 고위험 자산이에요. 아래 종목들은 참고용으로 알려드려요."
            />
          </div>
          <ul className="flex flex-col gap-1">
            {guide.coins.map((c) => (
              <li
                key={c}
                className="rounded-lg border border-black/15 bg-[#fff3e0] px-2.5 py-1.5 text-[11px] font-semibold"
              >
                {c}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="rounded-xl border-2 border-black bg-pixel-wall p-3 shadow-pixel-sm">
        <div className="mb-2 flex items-center gap-1.5 text-[12px] font-black">
          <ShieldCheck className="h-4 w-4" />
          공식 5단계 · 내 위치
        </div>
        <div className="grid grid-cols-5 gap-1 text-center text-[10px] font-black">
          {RISK_ROWS.map(([type]) => {
            const active = type === diagnosis.declared_type;
            return (
              <div
                key={type}
                className={`flex flex-col items-center gap-0.5 rounded-md border px-1 py-1.5 leading-tight ${active ? "border-black bg-[#76d672]" : "border-black/15 bg-white/60 text-black/55"
                  }`}
              >
                {type.replace("형", "")}
              </div>
            );
          })}
        </div>
      </section>

      <p className="text-center text-[10px] font-semibold text-black/40">{diagnosis.source}</p>
    </div>
  );
}
