"use client";

import PixelButton from "@/components/pixel/PixelButton";
import { FolderOpen, Play, Settings, Trophy } from "lucide-react";

// T-57 — 스플래시 + 시작 메뉴. 어둡게 한 the_ville 맵을 배경으로, 로고와 메뉴를 얹는다.
// 새 게임=온보딩 진입. 이어하기/업적(T-58/59)은 핸들러 없으면 비활성(준비 중).
export default function TitleScreen({
  onNewGame,
  onContinue,
  onAchievements,
  onSettings,
}: {
  onNewGame: () => void;
  onContinue?: () => void;
  onAchievements?: () => void;
  onSettings?: () => void;
}) {
  return (
    <main className="relative min-h-screen overflow-hidden">
      {/* 맵 배경은 부모(emo/page)의 공유 컷씬 iframe — 화면 전환 시 재부팅 방지. */}
      <div className="absolute inset-0 bg-black/60" />
      <div className="absolute inset-0 bg-gradient-to-b from-black/50 via-transparent to-black/70" />

      {/* 로고 + 시작 메뉴 */}
      <div className="relative z-10 flex min-h-screen flex-col items-center justify-center gap-10 px-4">
        <img
          src="/assets/ui/market_village_logo.png"
          alt="Market Village"
          className="w-[min(88vw,560px)] drop-shadow-[0_6px_0_rgba(0,0,0,0.45)]"
        />
        <nav className="flex w-60 flex-col gap-3">
          <PixelButton size="lg" className="w-full" onClick={onNewGame}>
            <Play size={16} /> 새 게임
          </PixelButton>
          <PixelButton
            size="lg"
            variant="secondary"
            className="w-full"
            disabled={!onContinue}
            title={onContinue ? undefined : "준비 중"}
            onClick={onContinue}
          >
            <FolderOpen size={16} /> 이어하기
          </PixelButton>
          <PixelButton
            size="lg"
            variant="secondary"
            className="w-full"
            disabled={!onAchievements}
            title={onAchievements ? undefined : "준비 중"}
            onClick={onAchievements}
          >
            <Trophy size={16} /> 업적
          </PixelButton>
          <PixelButton
            size="lg"
            variant="ghost"
            className="w-full"
            disabled={!onSettings}
            title={onSettings ? undefined : "준비 중"}
            onClick={onSettings}
          >
            <Settings size={16} /> 설정
          </PixelButton>
        </nav>
      </div>
    </main>
  );
}
