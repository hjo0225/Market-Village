"use client";

const STAGES = [
  { icon: "🌅", label: "아침 — 하루가 시작된다" },
  { icon: "☀️", label: "한낮 — 시장이 움직인다" },
  { icon: "🌇", label: "저녁 — 오늘을 정리한다" },
];

// 사용자 피드백(2026-07-01) — "하루가 2분동안 진행되는 속도로" 순간이동처럼
// 느껴지지 않게, 하루가 실제로 흘러가는 느낌을 준다. 위기가 발생하면 이 진행이
// 멈추고 CrisisEventModal이 대신 뜬다(부모가 stageIndex 갱신을 멈춤).
export default function DayProgressOverlay({ stageIndex }: { stageIndex: number }) {
  if (stageIndex < 0 || stageIndex >= STAGES.length) return null;
  const stage = STAGES[stageIndex];
  return (
    <div className="fixed inset-0 z-[100] flex items-end justify-center pb-28 pointer-events-none">
      <div className="bg-white/95 border-2 border-black rounded-2xl shadow-pixel-lg px-6 py-3 flex items-center gap-3 animate-pixel-pop">
        <span className="text-2xl animate-bump">{stage.icon}</span>
        <span className="text-sm font-bold">{stage.label}</span>
      </div>
    </div>
  );
}
