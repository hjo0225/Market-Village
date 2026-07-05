"use client";

// T-271 — 긴급 속보 사이렌(유저 트리거 외란). 우하단 🚨을 눌렀을 때 뜨는 3지선다.
// 효과는 심리 전용(가격·운명선 불가침 §7.1) — 서버 응답의 델타를 토스트로 보여준다.
const CHOICES: { key: "bad" | "good" | "skip"; icon: string; label: string; desc: string; chip: string }[] = [
  { key: "bad", icon: "📉", label: "갑작스런 악재", desc: "마을과 클론이 공포에 술렁인다", chip: "bg-yellow-50" },
  { key: "good", icon: "🚀", label: "갑작스런 호재", desc: "마을과 클론이 들뜬다 (FOMO)", chip: "bg-green-50" },
  { key: "skip", icon: "🤫", label: "이번 속보는 넘어가기", desc: "아무 일도 일어나지 않는다", chip: "bg-slate-100" },
];

interface Props {
  isOpen: boolean;
  busy: boolean;
  onChoose: (choice: "bad" | "good" | "skip") => void;
  onClose: () => void;
}

export default function SirenEventModal({ isOpen, busy, onChoose, onClose }: Props) {
  if (!isOpen) return null;
  return (
    <div role="dialog" aria-modal="true" className="fixed inset-0 z-[140] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-pixel-ink/80" onClick={onClose} />
      <div className="relative w-full max-w-2xl flex flex-col items-center gap-5 animate-bump">
        <div className="text-center">
          <p className="text-sm font-bold text-red-400 mb-1 tracking-widest animate-pulse">🚨 긴급 속보</p>
          <h2 className="text-2xl font-extrabold text-white drop-shadow-md">마을에 무슨 소식을 흘릴까?</h2>
          <p className="text-sm text-white/70 mt-1">시장 가격은 변하지 않는다 — 흔들리는 건 마음뿐.</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-4 w-full justify-center">
          {CHOICES.map((c, i) => (
            <button
              key={c.key} disabled={busy}
              onClick={() => onChoose(c.key)}
              style={{ animationDelay: `${i * 120}ms` }}
              className="animate-card-reveal flex-1 min-w-[170px] rounded-2xl border-2 border-black
                bg-white shadow-pixel-md p-5 text-center cursor-pointer select-none
                transition-all duration-150 ease-out hover:-translate-y-1.5 hover:shadow-pixel-lg
                disabled:opacity-60 disabled:cursor-default"
            >
              <div className={`mx-auto w-14 h-14 flex items-center justify-center rounded-xl border-2 border-black ${c.chip} text-3xl mb-3`}>
                {c.icon}
              </div>
              <div className="text-base font-extrabold text-black leading-snug">{c.label}</div>
              <div className="text-xs text-pixel-muted mt-1.5">{c.desc}</div>
            </button>
          ))}
        </div>
        <button onClick={onClose} className="text-sm text-white/60 hover:text-white underline underline-offset-4">
          닫기 (사이렌은 잠시 더 울린다)
        </button>
      </div>
    </div>
  );
}
