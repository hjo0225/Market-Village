"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import PixelButton from "@/components/pixel/PixelButton";
import PixelPanel from "@/components/pixel/PixelPanel";
import { getGameId } from "@/lib/session";

export default function MainMenu() {
  const router = useRouter();
  const [hasGame, setHasGame] = useState(false);

  useEffect(() => {
    setHasGame(!!getGameId());
  }, []);

  return (
    <main className="min-h-screen flex items-center justify-center bg-white p-6">
      <PixelPanel tone="cloud" className="w-full max-w-md p-8 text-center animate-pixel-pop">
        <div className="text-5xl mb-3">🪞</div>
        <h1 className="text-2xl font-extrabold mb-1">Market Village</h1>
        <p className="text-sm text-pixel-muted mb-8">
          블라인드 처리된 실제 과거 코인 시장에서<br />내 거울 클론이 30일을 산다
        </p>
        <div className="flex flex-col gap-3">
          <PixelButton size="lg" onClick={() => router.push("/setup")}>
            🧬 새 게임 시작
          </PixelButton>
          <PixelButton
            size="lg" variant="secondary"
            disabled={!hasGame}
            onClick={() => router.push("/history")}
          >
            📊 회차 기록 보기
          </PixelButton>
          {!hasGame && (
            <p className="text-xs text-pixel-muted mt-1">회차 기록은 게임을 한 번 시작한 뒤 볼 수 있어요</p>
          )}
        </div>
      </PixelPanel>
    </main>
  );
}
