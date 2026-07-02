"use client";

// T-237 §12.1b — 하루 8슬롯의 4시간대와 1:1 대응(각 단계에서 그 시간대 일과를 걷는다).
const STAGES = [
  { icon: "🌅", label: "오전 — 마을이 깨어난다" },
  { icon: "🍜", label: "점심 — 사람들이 오간다" },
  { icon: "☀️", label: "오후 — 시장이 움직인다" },
  { icon: "🌇", label: "저녁 — 오늘을 정리한다" },
];

// 사용자 피드백(2026-07-01) — "하루가 2분동안 진행되는 속도로" 순간이동처럼
// 느껴지지 않게, 하루가 실제로 흘러가는 느낌을 준다. 위기가 발생하면 이 진행이
// 멈추고 CrisisEventModal이 대신 뜬다(부모가 stageIndex 갱신을 멈춤).
//
// 사용자 피드백(2026-07-02) — 그 결과 한 단계가 20초씩 이어지는데 등장 때
// 0.45초짜리 bump 말고는 정말 아무 것도 안 움직여서 "멈춘 것"처럼 보임(마지막
// 저녁 단계는 실제 서버 응답까지 더 걸림, 즉 길이가 정해져 있지 않음). 그래서
// 고정 길이 프로그레스바 대신, 하루가 여전히 흐르고 있다는 걸 계속 보여주는
// 무한반복 펄스(아이콘)+인디터미닛 바를 켜 둔다(§ 정확한 진행률은 알 수 없음).
export default function DayProgressOverlay({ stageIndex, plan }: { stageIndex: number; plan?: string }) {
  if (stageIndex < 0 || stageIndex >= STAGES.length) return null;
  const stage = STAGES[stageIndex];
  return (
    <div className="fixed inset-0 z-[100] flex items-end justify-center pb-28 pointer-events-none">
      <div className="bg-white/95 border-2 border-black rounded-2xl shadow-pixel-lg px-6 py-3 flex flex-col gap-2 animate-pixel-pop min-w-[220px]">
        <div className="flex items-center gap-3">
          <span key={stageIndex} className="text-2xl animate-bump">{stage.icon}</span>
          <span className="text-sm font-bold animate-pulse-soft">{stage.label}</span>
        </div>
        {/* T-240 — 지금 시간대의 일정(회피로 매일 달라질 수 있어 안내가 필요). */}
        {plan && <p className="text-[11px] text-pixel-muted">🗓 일정: {plan}</p>}
        <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-black/10">
          <div className="absolute inset-y-0 w-1/3 rounded-full bg-pixel-greenText/70 animate-bar-indeterminate" />
        </div>
      </div>
    </div>
  );
}
