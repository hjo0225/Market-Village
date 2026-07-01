"use client";

// 위기 개입 카드 연출(칼바람 증강 픽 참고, PRD_CRISIS_CARD_REVEAL.md D1~D3).
// 색상은 이 카드에 한해 프로젝트 기본 팔레트(흑백+그린/옐로)의 예외(D3, 사용자 승인).
const STRATEGIES = [
  {
    value: "A_과거찌르기", label: "과거 찌르기", icon: "🗡️",
    desc: "클론의 과거 기록을 직면시킨다.",
    glow: "#B91C1C", bg: "from-[#3A0A0A] to-[#1A0505]",
  },
  {
    value: "B_함정직시", label: "함정 직시", icon: "🪞",
    desc: "지금 빠진 감정에 이름을 붙여준다.",
    glow: "#0EA5E9", bg: "from-[#062233] to-[#03121C]",
  },
  {
    value: "C_감정다독임", label: "감정 다독임", icon: "🫂",
    desc: "동요를 가라앉히고 안심시킨다.",
    glow: "#EC4899", bg: "from-[#330A22] to-[#1C0512]",
  },
];

interface Props {
  trapName: string;
  busy: boolean;
  onChoose: (strategy: string | null) => void;
}

// 사용자 피드백(2026-07-01) — 위기 개입은 상시 노출 버튼이 아니라, 실제 위기가
// 터진 순간에만 갑작스러운 이벤트로 튀어나와야 한다. 평소엔 렌더 자체가 안 됨.
export default function CrisisEventModal({ trapName, busy, onChoose }: Props) {
  return (
    <div role="dialog" aria-modal="true" className="fixed inset-0 z-[140] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-pixel-ink/80" />
      <div className="relative w-full max-w-2xl flex flex-col items-center gap-5 animate-bump">
        <div className="text-center">
          <p className="text-[11px] font-bold text-pixel-danger mb-1 tracking-widest">⚠️ 위기 발생</p>
          <h2 className="text-xl font-extrabold text-white drop-shadow-md">{trapName}</h2>
          <p className="text-xs text-white/70 mt-1">클론이 흔들리고 있다. 어떻게 개입할까?</p>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 w-full justify-center">
          {STRATEGIES.map((s, i) => (
            <button
              key={s.value}
              disabled={busy}
              onClick={() => onChoose(s.value)}
              style={{ animationDelay: `${i * 130}ms`, boxShadow: `0 0 18px 2px ${s.glow}66` }}
              className={`animate-card-reveal group relative flex-1 min-w-[150px] rounded-2xl border-2 border-black
                bg-gradient-to-b ${s.bg} p-4 text-center cursor-pointer select-none
                transition-transform duration-150 ease-out
                hover:-translate-y-1.5 hover:scale-[1.04]
                disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:hover:scale-100`}
            >
              <span
                className="pointer-events-none absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity"
                style={{ boxShadow: `0 0 28px 6px ${s.glow}99, inset 0 0 20px ${s.glow}44` }}
              />
              <div className="relative text-3xl mb-2">{s.icon}</div>
              <div className="relative text-sm font-extrabold text-white">{s.label}</div>
              <div className="relative text-[11px] text-white/70 mt-1.5 leading-snug">{s.desc}</div>
            </button>
          ))}
        </div>

        <button
          disabled={busy}
          onClick={() => onChoose(null)}
          className="text-xs text-white/60 hover:text-white underline underline-offset-4 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          지켜본다 (개입 안 함)
        </button>
      </div>
    </div>
  );
}
