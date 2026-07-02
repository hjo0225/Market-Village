"use client";

// T-227 · §13.6 회차 비교 화면 — 거울의 핵심 산출물 (PRD_MIRROR_COMPARE C1~C4).
// 이전 회차와 이번 회차를 같은 날 위에 겹쳐 본다: 행동/교류/자금흐름/결과.
// 30일 나열이 아니라 "행동이 갈린 날"(분기일)만 탭으로(§13.3 빨리감기).
import { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import PixelButton from "@/components/pixel/PixelButton";
import {
  api, CompareDayView, FUND_FLOW_LABELS, NPC_LABELS, RunSummary,
} from "@/lib/api";
import { getGameId } from "@/lib/session";

function companionLabel(v: string): string {
  if (!v) return "혼자 보냄";
  return NPC_LABELS[v] ?? v;
}

function flowLabel(v: string): string {
  return v ? FUND_FLOW_LABELS[v] ?? v : "유지";
}

// C4 — 카타르시스 인사이트 한 줄(규칙 기반, LLM 불요 §12.0).
function insight(a: CompareDayView, b: CompareDayView): string {
  if (a.swayed && !b.swayed) {
    return b.total_asset >= a.total_asset
      ? "💡 같은 날, 다른 선택 — 이번엔 버텼고, 결과도 뒤집었다."
      : "💡 같은 날, 다른 선택 — 이번엔 버텼다. 결과는 시장의 몫, 판단은 내 몫.";
  }
  if (!a.swayed && b.swayed) {
    return "💡 지난 회차엔 버텼던 날 — 이번엔 휩쓸렸다. 아는 것과 안 휘둘리는 건 다르다.";
  }
  if (a.swayed && b.swayed) {
    return "💡 두 회차 모두 휩쓸린 날 — 이 함정이 내 반복 패턴이다.";
  }
  return "💡 행동의 결이 달라진 날 — 교류가 다르면 하루가 다르게 흘러간다.";
}

function DayColumn({ title, view }: { title: string; view: CompareDayView }) {
  return (
    <div className="flex-1 min-w-0">
      <p className="text-[11px] font-extrabold text-pixel-muted mb-2">{title}</p>
      <div className="flex flex-col gap-1.5 text-[12px]">
        <p>{view.swayed ? "😱 휩쓸림" : "🪨 버팀"}</p>
        <p className="truncate">👥 {companionLabel(view.companion)}</p>
        <p className="leading-snug">💸 {flowLabel(view.fund_flow)}</p>
        <p>📊 총자산 {Math.round(view.total_asset)}
          {view.realized_pnl !== 0 && ` (실현 ${view.realized_pnl > 0 ? "+" : ""}${Math.round(view.realized_pnl)})`}
        </p>
      </div>
    </div>
  );
}

function CompareInner() {
  const router = useRouter();
  const params = useSearchParams();
  const [gameId, setGid] = useState<string | null>(null);
  const [summaries, setSummaries] = useState<RunSummary[]>([]);
  const [runA, setRunA] = useState<string | null>(params.get("a"));
  const [runB, setRunB] = useState<string | null>(params.get("b"));
  const [days, setDays] = useState<number[] | null>(null);
  const [selDay, setSelDay] = useState<number | null>(null);
  const [view, setView] = useState<{ a: CompareDayView | null; b: CompareDayView | null } | null>(null);

  useEffect(() => {
    const id = getGameId();
    if (!id) { router.replace("/"); return; }
    setGid(id);
    api.gameSummaries(id).then((r) => {
      if (r.status !== "ok") return;
      setSummaries(r.summaries);
      // C1 — 기본은 "직전 완주 vs 마지막 완주". URL 파라미터가 있으면 그걸 존중.
      if (r.summaries.length >= 2) {
        setRunB((b) => b ?? r.summaries[r.summaries.length - 1].run_id);
        setRunA((a) => a ?? r.summaries[r.summaries.length - 2].run_id);
      }
    });
  }, [router]);

  const loadDays = useCallback(async (id: string, a: string, b: string) => {
    setDays(null); setSelDay(null); setView(null);
    const r = await api.gameCompareDays(id, a, b);
    if (r.status !== "ok") return;
    setDays(r.days);
    if (r.days.length > 0) setSelDay(r.days[0]);
  }, []);

  useEffect(() => {
    if (gameId && runA && runB) loadDays(gameId, runA, runB);
  }, [gameId, runA, runB, loadDays]);

  useEffect(() => {
    if (gameId && runA && runB && selDay !== null) {
      api.gameCompare(gameId, runA, runB, selDay).then((r) => {
        if (r.status === "ok") setView({ a: r.a, b: r.b });
      });
    }
  }, [gameId, runA, runB, selDay]);

  if (!gameId) return null;
  if (summaries.length < 2) {
    return (
      <main className="min-h-screen bg-white p-6 flex items-center justify-center">
        <div className="text-center">
          <p className="text-sm font-bold mb-1">🪞 비교하려면 완주한 회차가 2개 필요해요</p>
          <p className="text-xs text-pixel-muted mb-4">같은 30일을 한 번 더 살아보면, 두 회차가 겹쳐 보입니다.</p>
          <PixelButton size="sm" onClick={() => router.push("/")}>메인으로</PixelButton>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-white p-6">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-3 mb-1 flex-wrap">
          <h1 className="text-xl font-extrabold">🪞 회차 비교</h1>
          <div className="flex-1" />
          <PixelButton size="sm" variant="ghost" onClick={() => router.push("/history")}>컬렉션으로</PixelButton>
        </div>
        <div className="flex items-center gap-2 mb-4 text-[12px]">
          <span className="font-bold">{runB}(이번)</span>
          <span className="text-pixel-muted">vs</span>
          <select
            className="border-2 border-black rounded-lg px-2 py-1"
            value={runA ?? ""} onChange={(e) => setRunA(e.target.value)}
          >
            {summaries.filter((s) => s.run_id !== runB).map((s) => (
              <option key={s.run_id} value={s.run_id}>
                {s.run_id} ({s.return_pct > 0 ? "+" : ""}{s.return_pct}% · {s.grade})
              </option>
            ))}
          </select>
        </div>

        {days === null ? (
          <p className="text-pixel-muted text-sm">분기일을 찾는 중…</p>
        ) : days.length === 0 ? (
          <p className="text-sm">두 회차가 같은 선택을 했습니다 — 행동이 갈린 날이 없어요.</p>
        ) : (
          <>
            <p className="text-[12px] text-pixel-muted mb-2">행동이 갈린 날 {days.length}개를 찾았습니다:</p>
            <div className="flex gap-2 mb-4 flex-wrap">
              {days.map((d) => (
                <PixelButton
                  key={d} size="sm"
                  variant={d === selDay ? "primary" : "secondary"}
                  onClick={() => setSelDay(d)}
                >Day {d}</PixelButton>
              ))}
            </div>
            {view && view.a && view.b && selDay !== null && (
              <div className="border-2 border-black rounded-2xl shadow-pixel-md p-4">
                <p className="text-sm font-extrabold mb-3">Day {selDay}</p>
                <div className="flex gap-4">
                  <DayColumn title={`${runA}`} view={view.a} />
                  <div className="w-px bg-black/20" />
                  <DayColumn title={`${runB}(이번)`} view={view.b} />
                </div>
                <p className="text-[12px] font-bold mt-4 pt-3 border-t-2 border-black/10">
                  {insight(view.a, view.b)}
                </p>
              </div>
            )}
          </>
        )}
      </div>
    </main>
  );
}

export default function ComparePage() {
  return (
    <Suspense fallback={<main className="min-h-screen flex items-center justify-center text-pixel-muted">불러오는 중…</main>}>
      <CompareInner />
    </Suspense>
  );
}
