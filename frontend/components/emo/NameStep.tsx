"use client";

import { daysWord } from "@/utils/emo";

// 온보딩 STEP 0 — 클론 이름 입력.
export default function NameStep({ name, totalDays = 10, onChange, onSubmit }: {
  name: string;
  totalDays?: number;   // T-66 — 모드 선택(3일/10일)이 이름 입력보다 먼저라 항상 확정돼 있다.
  onChange: (v: string) => void;
  onSubmit: () => void;
}) {
  return (
    <div>
      <p className="text-[12px] text-pixel-muted mb-4">이 마을에서 {daysWord(totalDays)}을 살아갈 내 클론의 이름을 지어주세요.</p>
      <label htmlFor="clone-name" className="text-[13px] font-bold block mb-2">클론 이름</label>
      <input
        id="clone-name" type="text" value={name} maxLength={12}
        placeholder="내 클론"
        autoFocus
        className="w-full px-3 py-2.5 text-[14px] rounded-lg border-2 border-black/15 bg-white focus:border-black/40 outline-none"
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter") onSubmit(); }}
      />
    </div>
  );
}
