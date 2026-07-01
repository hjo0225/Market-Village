"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import PixelButton from "@/components/pixel/PixelButton";
import ResultCardView from "@/components/ResultCardView";
import { api, ResultCard } from "@/lib/api";
import { clearGameId, getGameId } from "@/lib/session";

export default function ReportPage() {
  const router = useRouter();
  const [gameId, setGid] = useState<string | null>(null);
  const [card, setCard] = useState<ResultCard | null>(null);
  const [notReady, setNotReady] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const id = getGameId();
    if (!id) { router.replace("/"); return; }
    setGid(id);
    api.gameCard(id).then((r) => {
      if (r.status === "ok" && r.card) setCard(r.card);
      else setNotReady(true);
    });
  }, [router]);

  async function playAgain() {
    if (!gameId) return;
    setBusy(true);
    await api.gameNewRun(gameId);
    router.push("/play");
  }

  function backToMain() {
    router.push("/");
  }

  function endAndClear() {
    clearGameId();
    router.push("/");
  }

  if (notReady) {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center gap-4 text-center p-6">
        <p className="text-pixel-muted">아직 완주하지 않은 회차예요. 30일을 다 살아야 결과를 볼 수 있어요.</p>
        <div className="flex gap-2">
          <PixelButton onClick={() => router.push("/play")}>이어서 플레이</PixelButton>
          <PixelButton variant="ghost" onClick={backToMain}>메인으로</PixelButton>
        </div>
      </main>
    );
  }

  if (!card) {
    return <main className="min-h-screen flex items-center justify-center text-pixel-muted">결과 불러오는 중…</main>;
  }

  return (
    <main className="min-h-screen bg-white p-6 flex items-center justify-center">
      <div className="w-full max-w-md">
        <h1 className="text-xl font-extrabold mb-4 text-center">🏁 30일 결과</h1>
        <ResultCardView
          returnPct={card.return_pct} grade={card.grade}
          emotionOverall={card.emotion_overall} evaluation={card.evaluation}
        />
        <div className="flex gap-2 mt-5">
          <PixelButton className="flex-1" disabled={busy} onClick={playAgain}>
            ↻ 새 회차 (같은 시험지)
          </PixelButton>
          <PixelButton className="flex-1" variant="secondary" onClick={() => router.push("/history")}>
            📊 회차 기록
          </PixelButton>
        </div>
        <div className="flex gap-2 mt-2">
          <PixelButton className="flex-1" variant="ghost" onClick={backToMain}>메인으로</PixelButton>
          <PixelButton className="flex-1" variant="ghost" onClick={endAndClear}>세션 종료</PixelButton>
        </div>
      </div>
    </main>
  );
}
