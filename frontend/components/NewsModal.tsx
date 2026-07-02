"use client";

import PixelModal from "@/components/pixel/PixelModal";
import { NewsItem } from "@/lib/api";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  news: NewsItem[];
  onSelect: (newsId: string) => void;
  // T-234 — 하루진행이 뉴스 선택을 기다릴 때만 전달됨: "안 읽고 진행" 스킵 경로.
  onSkip?: () => void;
}

// 사용자 피드백(2026-07-01) — 뉴스 선택도 상시 인라인 목록이 아니라 리모콘의
// 한 버튼으로 숨겨두고, 하나 고르면 모달이 자동으로 내려간다.
// T-234 — 하루진행 시 뉴스를 안 골랐으면 이 모달이 흐름 안에서 자동으로 뜬다(§7.4).
export default function NewsModal({ isOpen, onClose, news, onSelect, onSkip }: Props) {
  return (
    <PixelModal isOpen={isOpen} onClose={onClose} title="☀️ 오늘 — 아침 뉴스" size="sm">
      <div className="flex flex-col gap-2">
        {news.map((n) => (
          <button
            key={n.id}
            onClick={() => { onSelect(n.id); onClose(); }}
            className="text-left text-sm px-3 py-2 rounded-lg border-2 border-black/15 hover:border-black hover:bg-pixel-water"
          >
            <span className="text-[10px] uppercase text-pixel-muted mr-1">[{n.tone}]</span>{n.headline}
          </button>
        ))}
        {onSkip && (
          <button
            onClick={() => { onSkip(); onClose(); }}
            className="text-right text-xs text-pixel-muted underline underline-offset-2 mt-1"
          >
            오늘 뉴스는 안 읽고 진행 ▶
          </button>
        )}
      </div>
    </PixelModal>
  );
}
