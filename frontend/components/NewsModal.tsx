"use client";

import { NewsItem } from "@/lib/api";

// T-267 — 사용자 피드백: 글씨 확대 + 디자인시스템 정합. T-236의 다크 그라디언트
// 카드(T-217 팔레트 예외 준용)를 철회하고 DESIGN.md 기본(흰 카드·흑 보더·pixel
// 섀도, 그린/옐로 액센트)으로 재스킨. 톤 구분은 토큰 내 색으로만.
// T-234 — 하루진행 시 뉴스를 안 골랐으면 이 오버레이가 흐름 안에서 자동으로 뜬다(§7.4).
// T-279 — 게시판 NEWS 카드에서도 재사용(export).
export const TONE_STYLE: Record<string, { label: string; icon: string; text: string; chip: string }> = {
  fear: { label: "공포", icon: "📉", text: "text-pixel-danger", chip: "bg-yellow-50" },
  optimism: { label: "낙관", icon: "🚀", text: "text-pixel-greenText", chip: "bg-green-50" },
  uncertain: { label: "불확실", icon: "🌫", text: "text-pixel-muted", chip: "bg-slate-100" },
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
      <div className="relative w-full max-w-3xl flex flex-col items-center gap-6 animate-bump">
        <div className="text-center">
          <p className="text-sm font-bold text-pixel-grass mb-1 tracking-widest">📰 아침 뉴스</p>
          <h2 className="text-2xl font-extrabold text-white drop-shadow-md">오늘, 어떤 뉴스가 눈에 들어왔나?</h2>
          <p className="text-sm text-white/70 mt-1">고른 뉴스가 클론과 마을의 마음을 흔든다.</p>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 w-full justify-center">
          {news.map((n, i) => {
            const s = TONE_STYLE[n.tone] ?? TONE_STYLE.uncertain;
            return (
              <button
                key={n.id}
                onClick={() => { onSelect(n.id); onClose(); }}
                style={{ animationDelay: `${i * 130}ms` }}
                className="animate-card-reveal group relative flex-1 min-w-[180px] rounded-2xl border-2 border-black
                  bg-white shadow-pixel-md p-5 text-center cursor-pointer select-none
                  transition-all duration-150 ease-out
                  hover:-translate-y-1.5 hover:shadow-pixel-lg"
              >
                <div className={`mx-auto w-14 h-14 flex items-center justify-center rounded-xl border-2 border-black ${s.chip} text-3xl mb-3`}>
                  {s.icon}
                </div>
                <div className={`text-xs font-bold tracking-widest mb-2 ${s.text}`}>{s.label}</div>
                <div className="text-base font-extrabold text-black leading-snug">{n.headline}</div>
              </button>
            );
          })}
        </div>

        {/* T-247(사용자 리포트 ⑨) — 뉴스 선택은 실험 변인이라 스킵 없음. 하루를
            진행하려면 반드시 하나를 골라야 한다(X 닫기 = 진행 취소). */}
        {!onSkip && (
          <button
            onClick={onClose}
            className="text-sm text-white/60 hover:text-white underline underline-offset-4"
          >
            닫기
          </button>
        )}
      </div>
    </div>
  );
}
