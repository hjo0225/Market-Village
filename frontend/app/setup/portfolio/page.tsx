"use client";

// T-231 — 설정 2/2단계: 포트폴리오만 (한 페이지 한 목적).
// 1단계에서 확정된 인터뷰 답변(localStorage)을 소비 — 없으면 /setup으로 강제 복귀.
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import PixelButton from "@/components/pixel/PixelButton";
import PixelPanel from "@/components/pixel/PixelPanel";
import { api, CATEGORY_LABELS } from "@/lib/api";
import { clearSetupAnswers, getSetupAnswers, newGameId, setGameId } from "@/lib/session";

const SYMBOLS = ["DOGE", "BTC", "SOL", "USDT"];
const CATEGORIES = ["large_stable", "mid_alt", "meme", "stable"];

export default function PortfolioSetupPage() {
  const router = useRouter();
  const [answers, setAnswers] = useState<Record<string, number> | null>(null);
  const [symbol, setSymbol] = useState("DOGE");
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  // -- 분산해서 시작 (T-215 D1, 기본 꺼짐) --
  const [diversify, setDiversify] = useState(false);
  const [allocations, setAllocations] = useState<Record<string, number>>({
    large_stable: 25, mid_alt: 25, meme: 25, stable: 25,
  });
  const allocationTotal = CATEGORIES.reduce((sum, c) => sum + (allocations[c] ?? 0), 0);
  const allocationValid = allocationTotal === 100;

  useEffect(() => {
    // 순서 강제 — 확정된 인터뷰 없이는 이 단계에 못 들어온다.
    const saved = getSetupAnswers();
    if (!saved) { router.replace("/setup"); return; }
    setAnswers(saved);
  }, [router]);

  async function handleStart() {
    if (!answers) return;
    setStarting(true);
    setStartError(null);
    try {
      const gameId = newGameId();
      const r = await api.gameStart(gameId, answers, symbol, 100.0, diversify ? allocations : undefined);
      if (r.status !== "ok") {
        // 실패해도 확정 답변은 보존 — 그대로 재시도 가능(비동기 유실 방지).
        setStartError("서버 연결에 실패했어요. 잠시 후 다시 시도해주세요.");
        return;
      }
      setGameId(gameId);
      clearSetupAnswers();   // 시작이 확정된 뒤에만 정리
      router.push("/play");
    } finally {
      setStarting(false);
    }
  }

  if (!answers) {
    return <main className="min-h-screen flex items-center justify-center text-pixel-muted">확인 중…</main>;
  }

  const canStart = !diversify || allocationValid;

  return (
    <main className="min-h-screen bg-white p-6">
      <div className="max-w-lg mx-auto">
        <h1 className="text-xl font-extrabold mb-1">🥧 시작 포트폴리오 <span className="text-xs text-pixel-muted font-bold">(2/2단계)</span></h1>
        <p className="text-xs text-pixel-muted mb-4">
          감정 성향은 확정됐어요. 이제 클론이 들고 시작할 자산을 정합니다.
          <button className="underline ml-1" onClick={() => router.push("/setup")}>← 인터뷰 다시 하기</button>
        </p>

        <PixelPanel tone="cloud" className="p-5 animate-slide-up">
          <label className="flex items-center gap-2 text-sm font-bold mb-1 cursor-pointer select-none">
            <input type="checkbox" checked={diversify} onChange={(e) => setDiversify(e.target.checked)} />
            🥧 분산해서 시작 — 4카테고리에 나눠 담기
          </label>

          {!diversify ? (
            <div className="flex items-center gap-3 mt-2">
              <label className="text-sm font-bold">종목</label>
              <select
                className="border-2 border-black rounded-lg px-3 py-2 text-sm"
                value={symbol} onChange={(e) => setSymbol(e.target.value)}
              >
                {SYMBOLS.map((s) => <option key={s}>{s}</option>)}
              </select>
            </div>
          ) : (
            <div className="flex flex-col gap-3 mt-2">
              {CATEGORIES.map((c) => (
                <div key={c}>
                  <div className="flex justify-between text-xs text-pixel-muted mb-1">
                    <span>{CATEGORY_LABELS[c]}</span>
                    <span className="font-bold">{allocations[c]}%</span>
                  </div>
                  <input
                    type="range" min={0} max={100} step={5} value={allocations[c]}
                    onChange={(e) => setAllocations((a) => ({ ...a, [c]: parseInt(e.target.value, 10) }))}
                    className="w-full accent-black"
                  />
                </div>
              ))}
              <p className={`text-xs font-bold text-right ${allocationValid ? "text-pixel-greenText" : "text-pixel-danger"}`}>
                합계 {allocationTotal}% {allocationValid ? "✓" : "(100%을 맞춰주세요)"}
              </p>
            </div>
          )}

          <div className="flex justify-end mt-4">
            <PixelButton size="lg" disabled={!canStart || starting} onClick={handleStart}>
              {starting ? "시작 중…" : "게임 시작 (30일) ▶"}
            </PixelButton>
          </div>
        </PixelPanel>
        {startError && (
          <p className="text-sm text-red-600 mt-2 text-right">{startError}</p>
        )}
      </div>
    </main>
  );
}
