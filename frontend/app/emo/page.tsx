"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Users, CalendarDays, Wallet } from "lucide-react";
import * as api from "@/lib/emoApi";
import { Board, ChainEvent, EmoState, NPC_NAME, CATEGORIES, CATEGORY_LABEL, Category } from "@/lib/emoApi";
import EmotionGauge from "@/components/EmotionGauge";
import PortfolioPanel from "@/components/PortfolioPanel";
import MapBackground, { MapBackgroundHandle } from "@/components/MapBackground";
import PixelPanel from "@/components/pixel/PixelPanel";
import PixelButton from "@/components/pixel/PixelButton";

// 초기 배분 기본값(비중, 합 100). 백엔드가 합으로 정규화하므로 정확히 100 아니어도 됨.
const DEFAULT_ALLOC: Record<Category, number> = {
  large_stable: 40, mid_alt: 30, meme: 20, stable: 10,
};

const QUESTIONS: { key: string; text: string; options: [string, number][] }[] = [
  { key: "q_panic", text: "급락장에서 당신의 첫 반응은?", options: [["바로 손절", 1], ["일부 정리", 0.5], ["버틴다", 0]] },
  { key: "q_fomo", text: "급등장에서 당신은?", options: [["추격매수", 1], ["조금만", 0.5], ["관망", 0]] },
  { key: "q_rumor", text: "출처 불명 루머에 얼마나 흔들리나요?", options: [["많이 흔들린다", 1], ["확인부터 한다", 0]] },
  { key: "q_check", text: "시세창을 얼마나 자주 보나요?", options: [["수시로", 1], ["가끔", 0.5], ["거의 안 봄", 0]] },
];

export default function EmoPage() {
  const [state, setState] = useState<EmoState | null>(null);
  const [board, setBoard] = useState<Board | null>(null);
  const [chain, setChain] = useState<ChainEvent | null>(null);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [alloc, setAlloc] = useState<Record<string, number>>({ ...DEFAULT_ALLOC });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mapRef = useRef<MapBackgroundHandle>(null);
  const [mapActivity, setMapActivity] = useState<string | null>(null);
  const day = state?.day ?? -1;

  // T-22 — 하루가 바뀌면 맵에서 클론이 그날 동선을 걷는다(배경 연출, 논블로킹).
  useEffect(() => {
    if (day >= 0 && state && !state.is_over) mapRef.current?.playWalk();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [day]);

  const refresh = useCallback(async (s: EmoState) => {
    setState(s);
    if (s.is_over) { setBoard(null); setChain(null); return; }
    const b = await api.getBoard(s.game_id);
    setBoard(b);
    setChain(s.has_pending_chain ? await api.getChain(s.game_id) : null);
  }, []);

  const start = async () => {
    setBusy(true); setError(null);
    const seed = Math.floor(Math.random() * 100000);
    const s = await api.startEmo(answers, seed, 10, alloc);
    if (s) await refresh(s);
    else setError("게임을 시작하지 못했어요. 잠시 후 다시 시도해 주세요.");
    setBusy(false);
  };

  const act = (fn: () => Promise<EmoState | null>) => async () => {
    setBusy(true); setError(null);
    const s = await fn();
    if (s) await refresh(s);
    else setError("요청이 처리되지 않았어요. 다시 시도해 주세요.");
    setBusy(false);
  };

  // ---------- 시작(진단) ----------
  if (!state) {
    const ready = QUESTIONS.every((q) => q.key in answers);
    return (
      <main className="min-h-screen bg-pixel-path flex items-center justify-center p-4">
        <PixelPanel tone="wall" className="w-full max-w-lg p-6">
          <h1 className="text-lg font-extrabold mb-1">마켓 빌리지의 열흘</h1>
          <p className="text-[12px] text-pixel-muted mb-5">몇 가지로 당신의 투자 성향을 진단해요.</p>
          <div className="flex flex-col gap-4">
            {QUESTIONS.map((q) => (
              <div key={q.key}>
                <div className="text-[13px] font-bold mb-2">{q.text}</div>
                <div className="flex flex-wrap gap-2">
                  {q.options.map(([label, val]) => (
                    <PixelButton
                      key={label}
                      size="sm"
                      variant={answers[q.key] === val ? "primary" : "ghost"}
                      onClick={() => setAnswers((a) => ({ ...a, [q.key]: val }))}
                    >
                      {label}
                    </PixelButton>
                  ))}
                </div>
              </div>
            ))}
          </div>
          {/* T-11 · 초기 자산 배분 */}
          {(() => {
            const sum = CATEGORIES.reduce((s, c) => s + (alloc[c] ?? 0), 0);
            return (
              <div className="mt-6 border-t border-black/10 pt-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="text-[13px] font-bold">초기 자산 배분</div>
                  <span className="text-[11px] text-pixel-muted">합계 {sum}{sum === 100 ? " ✓" : "%"}</span>
                </div>
                <div className="flex flex-col gap-2.5">
                  {CATEGORIES.map((c: Category) => {
                    const pct = sum > 0 ? Math.round(((alloc[c] ?? 0) / sum) * 100) : 0;
                    return (
                      <div key={c} className="flex items-center gap-3 text-[12px]">
                        <span className="w-20 shrink-0 text-pixel-muted">{CATEGORY_LABEL[c]}</span>
                        <input
                          type="range" min={0} max={100} step={5} value={alloc[c] ?? 0}
                          className="flex-1 accent-black"
                          onChange={(e) => setAlloc((a) => ({ ...a, [c]: Number(e.target.value) }))}
                        />
                        <span className="w-9 text-right font-bold tabular-nums">{pct}%</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })()}
          {error && (
            <p className="mt-4 text-[12px] font-bold text-red-600" role="alert">{error}</p>
          )}
          <PixelButton size="lg" className="w-full mt-4" disabled={!ready || busy} onClick={start}>
            {busy ? "시작하는 중…" : "이사 온 날 →"}
          </PixelButton>
        </PixelPanel>
      </main>
    );
  }

  // ---------- 엔딩 ----------
  if (state.is_over && state.ending) {
    const e = state.ending;
    return (
      <main className="min-h-screen bg-pixel-path flex items-center justify-center p-4">
        <PixelPanel tone="cloud" className="w-full max-w-lg p-6">
          <div className="text-[11px] text-pixel-muted mb-1">{e.id} · {e.grade}</div>
          <h1 className="text-xl font-extrabold mb-4">{e.title}</h1>
          <div className="flex flex-col gap-3 text-[13px] leading-relaxed">
            {e.epilogue.map((line, i) => (
              <p key={i} className="border-l-2 border-black/10 pl-3">{line}</p>
            ))}
          </div>
          <div className="mt-5 text-[11px] text-pixel-muted">
            최종 자산 {Math.round(state.portfolio_value).toLocaleString()} · 특수이벤트 {state.special_event_count}회
          </div>
          <PixelButton size="lg" className="w-full mt-5" onClick={() => { setState(null); setAnswers({}); }}>
            다시 시작
          </PixelButton>
        </PixelPanel>
      </main>
    );
  }

  // ---------- 플레이 (프린세스메이커식 프레임: 상태바 / 맵창+스탯 / 커맨드) ----------
  const active: { kind: "chain" | "board"; label: string; choices: { id: string; label: string }[];
    on: (id: string) => Promise<EmoState | null> } | null = chain
    ? { kind: "chain", label: "만남", choices: chain.choices,
        on: (id) => api.chooseChain(state.game_id, id) }
    : board
    ? { kind: "board", label: "선택", choices: board.scenario.choices,
        on: (id) => api.choose(state.game_id, id) }
    : null;
  return (
    <main className="h-screen w-screen overflow-hidden bg-pixel-path flex flex-col gap-2 p-2 sm:p-3">
      {/* 상태바 */}
      <header className="shrink-0 flex items-center gap-4 text-[12px] font-bold px-1">
        <span className="inline-flex items-center gap-1"><CalendarDays className="w-4 h-4" />Day {state.day + 1}/{state.total_days}</span>
        <span className="inline-flex items-center gap-1"><Wallet className="w-4 h-4" />{Math.round(state.portfolio_value).toLocaleString()}</span>
        {state.companion && (
          <span className="inline-flex items-center gap-1"><Users className="w-4 h-4" />동행 · {NPC_NAME[state.companion] ?? state.companion}</span>
        )}
      </header>

      {/* 중단: 맵 장면 창(좌) + 스탯 패널(우) */}
      <div className="flex-1 min-h-0 flex flex-col md:flex-row gap-2">
        {/* 맵 장면 창 */}
        <div className="relative flex-1 min-h-0 min-w-0 rounded-xl overflow-hidden border-2 border-black/25">
          <MapBackground ref={mapRef} gameId={state.game_id} game="emo" contained onActivity={setMapActivity} />
          {mapActivity && !chain && !board && (
            <div className="absolute top-2 left-2 z-10 text-[11px] font-bold bg-black/60 text-white rounded px-2 py-1">{mapActivity}</div>
          )}
          {/* 이벤트 서사 오버레이(만남/게시판) — 맵 창 하단 대사 박스 */}
          {(chain || board) && (
            <div className="absolute inset-x-0 bottom-0 z-10 p-3">
              <div className="bg-black/72 text-white rounded-lg px-4 py-3 backdrop-blur-sm">
                {chain ? (
                  <>
                    <div className="text-[11px] text-white/60 mb-1">{NPC_NAME[chain.npc_id] ?? chain.npc_id}{chain.place ? ` · ${chain.place}` : ""}</div>
                    <div className="text-[13px] font-extrabold mb-1">{chain.title}</div>
                    <p className="text-[13px] leading-relaxed whitespace-pre-line">{chain.text}</p>
                  </>
                ) : board ? (
                  <>
                    <div className="text-[11px] text-white/60 mb-1">게시판 · 여론 {board.verdict}</div>
                    <p className="text-[13px] leading-relaxed">{board.scenario.text}</p>
                  </>
                ) : null}
              </div>
            </div>
          )}
        </div>

        {/* 스탯 패널 */}
        <aside className="shrink-0 md:w-72 flex flex-col gap-2 overflow-y-auto">
          <EmotionGauge emotion={state.emotion} verdict={state.verdict} />
          <PortfolioPanel holdings={state.holdings} />
          {board && !chain && (
            <PixelPanel tone="wall" className="p-3">
              <div className="text-[11px] text-pixel-muted mb-2">게시판 여론</div>
              <div className="flex flex-col gap-1">
                {board.threads.slice(0, 4).map((t, i) => (
                  <div key={i} className="text-[11px] bg-black/[0.03] rounded px-2 py-1">
                    <span className="font-bold">{NPC_NAME[t.author_id] ?? t.author_id}</span> {t.text}
                  </div>
                ))}
              </div>
            </PixelPanel>
          )}
        </aside>
      </div>

      {/* 하단: 커맨드/선택 바 */}
      <div className="shrink-0">
        {error && (
          <div className="mb-2 text-[12px] font-bold text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2" role="alert">{error}</div>
        )}
        {active && (
          <PixelPanel tone={active.kind === "chain" ? "path" : "wall"} className="p-2">
            <div className="flex flex-col sm:flex-row gap-2">
              {active.choices.map((c) => (
                <PixelButton key={c.id} variant={active.kind === "chain" ? "secondary" : "primary"}
                  className="flex-1" disabled={busy}
                  onClick={act(() => active.on(c.id))}>
                  {c.label}
                </PixelButton>
              ))}
            </div>
          </PixelPanel>
        )}
      </div>
    </main>
  );
}
