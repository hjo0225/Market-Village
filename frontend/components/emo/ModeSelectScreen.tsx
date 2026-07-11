"use client";

import PixelPanel from "@/components/pixel/PixelPanel";
import PixelButton from "@/components/pixel/PixelButton";
import { Zap, Home } from "lucide-react";

// T-66 — 게임 모드 선택(3일 압축판 / 10일 정식판). 타이틀 "새 게임" 직후,
// 기존 온보딩(이름→설문→진단→배분) 진입 전 단계. 맵 배경은 부모(emo/page)의
// 공유 컷씬 iframe 위에 얹는다(TitleScreen과 동일 톤 — 전환 시 재부팅 없음).
// 카드 클릭 = 선택 즉시 진행(별도 확인 버튼 없음).
export default function ModeSelectScreen({
  onPick,
  onBack,
}: {
  onPick: (days: number) => void;
  onBack: () => void;
}) {
  return (
    <main className="relative min-h-screen overflow-hidden">
      <div className="absolute inset-0 bg-black/60" />
      <div className="absolute inset-0 bg-gradient-to-b from-black/50 via-transparent to-black/70" />

      <div className="relative z-10 flex min-h-screen flex-col items-center justify-center gap-8 px-4 py-10">
        <div className="text-center">
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white drop-shadow-[0_2px_6px_rgba(0,0,0,0.6)]">
            며칠을 살아볼까?
          </h1>
        </div>

        <div className="flex w-full max-w-md flex-col gap-4">
          <button type="button" onClick={() => onPick(3)} className="text-left">
            <PixelPanel tone="cloud" className="p-5 transition hover:brightness-95 active:translate-x-[1px] active:translate-y-[1px] active:shadow-none">
              <div className="flex items-center gap-2 mb-2">
                <Zap size={18} className="text-pixel-gold" />
                <h2 className="text-lg font-extrabold">3일 압축판</h2>
                <span className="ml-auto text-[11px] font-bold bg-pixel-grass text-black rounded-full px-3 py-1 border-2 border-black">
                  약 10분
                </span>
              </div>
              <p className="text-[13px] leading-relaxed">
                핵심만 빠르게. 급등의 유혹, 급락의 공포, 반등의 검증 — 사흘로 압축한 한 시즌.
              </p>
              <p className="mt-2 text-[11px] text-pixel-muted">처음이라면·시연이라면 이쪽.</p>
            </PixelPanel>
          </button>

          <button type="button" onClick={() => onPick(10)} className="text-left">
            <PixelPanel tone="cloud" className="p-5 transition hover:brightness-95 active:translate-x-[1px] active:translate-y-[1px] active:shadow-none">
              <div className="flex items-center gap-2 mb-2">
                <Home size={18} className="text-pixel-greenText" />
                <h2 className="text-lg font-extrabold">10일 정식판</h2>
                <span className="ml-auto text-[11px] font-bold bg-pixel-table text-black rounded-full px-3 py-1 border-2 border-black">
                  약 30분
                </span>
              </div>
              <p className="text-[13px] leading-relaxed">
                마을에서의 열흘. 감정 습관이 온전히 드러나는 정식 플레이.
              </p>
            </PixelPanel>
          </button>
        </div>

        <PixelButton size="md" variant="ghost" onClick={onBack}>
          ← 타이틀로
        </PixelButton>
      </div>
    </main>
  );
}
