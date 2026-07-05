"use client";

// T-231 — 설정 2/2단계: 포트폴리오만 (한 페이지 한 목적).
// T-274 — 사용자 지시: 단일 종목 모드 삭제, 4유형 배분 고정, UI 대형화.
// 1단계에서 확정된 인터뷰 답변(localStorage)을 소비 — 없으면 /setup으로 강제 복귀.
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import PixelButton from "@/components/pixel/PixelButton";
import PixelPanel from "@/components/pixel/PixelPanel";
import { api, CATEGORY_LABELS } from "@/lib/api";
import { clearSetupAnswers, getSetupAnswers, newGameId, setGameId } from "@/lib/session";

const CATEGORIES = ["large_stable", "mid_alt", "meme", "stable"];
const CATEGORY_ICONS: Record<string, string> = {
  large_stable: "🏛", mid_alt: "🚀", meme: "🐕", stable: "🪙",
};
const CATEGORY_DESC: Record<string, string> = {
  large_stable: "BTC급 — 느리지만 굵직하게",
  mid_alt: "중견 알트 — 테마 따라 출렁",
  meme: "밈코인 — 천국과 지옥 사이",
  stable: "스테이블 — 현금 대피소",
};

// T-273 — 마을 분위기 프리셋(🤖 council: 인원 불변, favored NPC 노출 빈도만 기움).
const VILLAGES: { key: string; icon: string; label: string; desc: string }[] = [
  { key: "balanced", icon: "⚖️", label: "균형 잡힌 마을", desc: "함정형과 도움형이 반반 (기본)" },
  { key: "conservative", icon: "🐢", label: "신중한 마을", desc: "차분한 투자자들을 더 자주 만난다" },
  { key: "aggressive", icon: "🔥", label: "불타는 마을", desc: "공포·FOMO를 자극하는 이웃이 늘어난다" },
];

export default function PortfolioSetupPage() {
  const router = useRouter();
  const [answers, setAnswers] = useState<Record<string, number> | null>(null);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const [village, setVillage] = useState("balanced");   // T-273

  // T-274 — 분산 4유형 고정(단일 종목 모드 삭제). 기본 균등 배분.
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
    if (!answers || !allocationValid) return;
    setStarting(true);
    setStartError(null);
    try {
      const gameId = newGameId();
      // symbol은 allocations가 있으면 서버가 무시(최대 비중 카테고리가 주력) — 기본값 유지.
      const r = await api.gameStart(gameId, answers, "DOGE", 100.0, allocations, village);
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

  return (
    <main className="min-h-screen bg-white p-6 sm:p-10">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-extrabold mb-2">🥧 시작 포트폴리오 <span className="text-sm text-pixel-muted font-bold">(2/2단계)</span></h1>
        <p className="text-base text-pixel-muted mb-6">
          감정 성향은 확정됐어요. 클론이 들고 시작할 자산을 4가지 유형에 나눠 담습니다.
          <button className="underline ml-2" onClick={() => router.push("/setup")}>← 인터뷰 다시 하기</button>
        </p>

        <PixelPanel tone="cloud" className="p-6 sm:p-8 animate-slide-up">
          <div className="flex flex-col gap-5">
            {CATEGORIES.map((c) => (
              <div key={c}>
                <div className="flex items-baseline justify-between mb-1.5">
                  <span className="text-base font-extrabold">
                    {CATEGORY_ICONS[c]} {CATEGORY_LABELS[c]}
                    <span className="ml-2 text-sm font-bold text-pixel-muted">{CATEGORY_DESC[c]}</span>
                  </span>
                  <span className="text-2xl font-extrabold tabular-nums">{allocations[c]}%</span>
                </div>
                <input
                  type="range" min={0} max={100} step={5} value={allocations[c]}
                  onChange={(e) => setAllocations((a) => ({ ...a, [c]: parseInt(e.target.value, 10) }))}
                  className="w-full h-3 accent-black cursor-pointer"
                />
              </div>
            ))}
            <p className={`text-lg font-extrabold text-right ${allocationValid ? "text-pixel-greenText" : "text-pixel-danger"}`}>
              합계 {allocationTotal}% {allocationValid ? "✓" : "— 100%를 맞춰주세요"}
            </p>
          </div>

          {/* T-273 — 마을 분위기 선택 */}
          <div className="mt-8 pt-6 border-t-2 border-black/10">
            <p className="text-base font-extrabold mb-3">🏘 마을 분위기</p>
            <div className="flex flex-col sm:flex-row gap-3">
              {VILLAGES.map((v) => (
                <button
                  key={v.key}
                  onClick={() => setVillage(v.key)}
                  className={`flex-1 text-left rounded-xl border-2 border-black p-4 cursor-pointer transition-all
                    ${village === v.key ? "bg-black text-white shadow-pixel-md" : "bg-white hover:bg-pixel-water"}`}
                >
                  <div className="text-base font-extrabold">{v.icon} {v.label}</div>
                  <div className={`text-sm mt-1 ${village === v.key ? "text-white/70" : "text-pixel-muted"}`}>
                    {v.desc}
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="flex justify-end mt-8">
            <PixelButton size="lg" disabled={!allocationValid || starting} onClick={handleStart}>
              {starting ? "시작 중…" : "게임 시작 (30일) ▶"}
            </PixelButton>
          </div>
        </PixelPanel>
        {startError && (
          <p className="text-base text-red-600 mt-3 text-right">{startError}</p>
        )}
      </div>
    </main>
  );
}
