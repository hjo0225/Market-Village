"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import PixelButton from "@/components/pixel/PixelButton";
import ResultCardView from "@/components/ResultCardView";
import { api, RunSummary } from "@/lib/api";
import { getGameId } from "@/lib/session";

export default function HistoryPage() {
  const router = useRouter();
  const [summaries, setSummaries] = useState<RunSummary[] | null>(null);

  useEffect(() => {
    const id = getGameId();
    if (!id) { router.replace("/"); return; }
    api.gameSummaries(id).then((r) => { if (r.status === "ok") setSummaries(r.summaries); });
  }, [router]);

  return (
    <main className="min-h-screen bg-white p-6">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-3 mb-5">
          <h1 className="text-xl font-extrabold">📊 회차 기록 (거울 비교)</h1>
          <div className="flex-1" />
          <PixelButton size="sm" variant="ghost" onClick={() => router.push("/")}>메인으로</PixelButton>
        </div>

        {summaries === null ? (
          <p className="text-pixel-muted">불러오는 중…</p>
        ) : summaries.length === 0 ? (
          <p className="text-pixel-muted">아직 완주한 회차가 없습니다. 30일을 다 살아보면 여기 쌓입니다.</p>
        ) : (
          <div className="flex flex-col gap-3">
            {summaries.map((s) => (
              <div key={s.run_id}>
                <ResultCardView
                  runId={s.run_id}
                  returnPct={s.return_pct} grade={s.grade} emotionOverall={s.emotion_overall}
                />
                {/* T-227 §13.6 — 이 회차를 최신 회차와 겹쳐보기(최신 카드면 직전과). */}
                {summaries.length >= 2 && (
                  <div className="flex justify-end mt-1">
                    <PixelButton
                      size="sm" variant="ghost"
                      onClick={() => {
                        const latest = summaries[summaries.length - 1].run_id;
                        const a = s.run_id === latest
                          ? summaries[summaries.length - 2].run_id : s.run_id;
                        router.push(`/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(latest)}`);
                      }}
                    >🪞 비교</PixelButton>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
