"use client";

import { ReactNode } from "react";

// T-288(사용자 지시 "폰 UI 통일") — 게시판 이벤트(T-255)의 슬라이드업 폰 프레임을
// 공용 컴포넌트로 추출. 이벤트 폰과 헤더 📱핸드폰이 같은 프레임을 쓴다.
export default function PhoneFrame({ day, children, maxW = "max-w-lg" }: {
  day: number;
  children: ReactNode;
  maxW?: string;
}) {
  return (
    <div className={`relative w-full ${maxW} bg-slate-900 border-2 border-black rounded-t-[28px] sm:rounded-[32px] shadow-pixel-md pt-2 pb-4 px-2 animate-[phoneup_0.45s_ease-out]`}>
      <style>{`@keyframes phoneup { from { transform: translateY(60%); opacity: 0.4; } to { transform: translateY(0); opacity: 1; } }`}</style>
      <div className="mx-auto w-24 h-1.5 rounded-full bg-slate-700 mb-1.5" />
      <div className="flex items-center justify-between px-4 text-[10px] text-slate-400 font-bold mb-1">
        <span>Day {day}</span><span>마을넷 📶 🔋</span>
      </div>
      <div className="bg-white rounded-2xl overflow-hidden">
        {children}
      </div>
    </div>
  );
}
