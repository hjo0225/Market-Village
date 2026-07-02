"use client";

import { NewsItem } from "@/lib/api";

// T-236 — 뉴스 3지선다를 위기 개입(T-217, PRD_CRISIS_CARD_REVEAL)과 같은
// 칼바람 증강 픽 카드 연출로. 색상은 T-217 D3 선례(카드 연출 한정 팔레트 예외) 준용.
// T-234 — 하루진행 시 뉴스를 안 골랐으면 이 오버레이가 흐름 안에서 자동으로 뜬다(§7.4).
const TONE_STYLE: Record<string, { label: string; icon: string; glow: string; bg: string }> = {
  fear: {
    label: "공포", icon: "📉",
    glow: "#B91C1C", bg: "from-[#3A0A0A] to-[#1A0505]",
  },
  optimism: {
    label: "낙관", icon: "🚀",
    glow: "#F59E0B", bg: "from-[#332508] to-[#1C1204]",
  },
  uncertain: {
    label: "불확실", icon: "🌫",
    glow: "#64748B", bg: "from-[#1E2733] to-[#0D131C]",
  },
};

interface Props {
  isOpen: boolean;
  onClose: () => void;
  news: NewsItem[];
  onSelect: (newsId: string) => void;
  // T-234 — 하루진행이 뉴스 선택을 기다릴 때만 전달됨: "안 읽고 진행" 스킵 경로.
  onSkip?: () => void;
}

export default function NewsModal({ isOpen, onClose, news, onSelect, onSkip }: Props) {
  if (!isOpen) return null;
  return (
    <div role="dialog" aria-modal="true" className="fixed inset-0 z-[125] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-pixel-ink/80" onClick={onClose} />
      <div className="relative w-full max-w-2xl flex flex-col items-center gap-5 animate-bump">
        <div className="text-center">
          <p className="text-[11px] font-bold text-pixel-grass mb-1 tracking-widest">📰 아침 뉴스</p>
          <h2 className="text-xl font-extrabold text-white drop-shadow-md">오늘, 어떤 뉴스가 눈에 들어왔나?</h2>
          <p className="text-xs text-white/70 mt-1">고른 뉴스가 클론의 마음을 흔든다 — 가격은 흔들지 않는다.</p>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 w-full justify-center">
          {news.map((n, i) => {
            const s = TONE_STYLE[n.tone] ?? TONE_STYLE.uncertain;
            return (
              <button
                key={n.id}
                onClick={() => { onSelect(n.id); onClose(); }}
                style={{ animationDelay: `${i * 130}ms`, boxShadow: `0 0 18px 2px ${s.glow}66` }}
                className={`animate-card-reveal group relative flex-1 min-w-[150px] rounded-2xl border-2 border-black
                  bg-gradient-to-b ${s.bg} p-4 text-center cursor-pointer select-none
                  transition-transform duration-150 ease-out
                  hover:-translate-y-1.5 hover:scale-[1.04]`}
              >
                <span
                  className="pointer-events-none absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity"
                  style={{ boxShadow: `0 0 28px 6px ${s.glow}99, inset 0 0 20px ${s.glow}44` }}
                />
                <div className="relative text-3xl mb-2">{s.icon}</div>
                <div className="relative text-[10px] font-bold tracking-widest mb-1.5" style={{ color: s.glow }}>
                  {s.label}
                </div>
                <div className="relative text-sm font-extrabold text-white leading-snug">{n.headline}</div>
              </button>
            );
          })}
        </div>

        {onSkip ? (
          <button
            onClick={() => { onSkip(); onClose(); }}
            className="text-xs text-white/60 hover:text-white underline underline-offset-4"
          >
            오늘 뉴스는 안 읽고 진행 ▶
          </button>
        ) : (
          <button
            onClick={onClose}
            className="text-xs text-white/60 hover:text-white underline underline-offset-4"
          >
            닫기
          </button>
        )}
      </div>
    </div>
  );
}
