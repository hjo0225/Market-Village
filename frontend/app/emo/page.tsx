"use client";

import { useCallback, useState } from "react";
import { Users, CalendarDays, Wallet } from "lucide-react";
import * as api from "@/lib/emoApi";
import { Board, ChainEvent, EmoState, NPC_NAME, CATEGORIES, CATEGORY_LABEL, Category } from "@/lib/emoApi";
import EmotionGauge from "@/components/EmotionGauge";
import PortfolioPanel from "@/components/PortfolioPanel";
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

  const refresh = useCallback(async (s: EmoState) => {
    setState(s);
    if (s.is_over) { setBoard(null); setChain(null); return; }
    const b = await api.getBoard(s.game_id);
    setBoard(b);
    setChain(s.has_pending_chain ? await api.getChain(s.game_id) : null);
  }, []);

  const start = async () => {
    setBusy(true);
    const seed = Math.floor(Math.random() * 100000);
    const s = await api.startEmo(answers, seed, 10, alloc);
    if (s) await refresh(s);
    setBusy(false);
  };

  const act = (fn: () => Promise<EmoState | null>) => async () => {
    setBusy(true);
    const s = await fn();
    if (s) await refresh(s);
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
          <PixelButton size="lg" className="w-full mt-6" disabled={!ready || busy} onClick={start}>
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

  // ---------- 플레이 ----------
  return (
    <main className="min-h-screen bg-pixel-path p-4">
      <div className="max-w-2xl mx-auto flex flex-col gap-4">
        {/* 헤더 */}
        <div className="flex items-center gap-3 text-[12px] font-bold">
          <span className="inline-flex items-center gap-1"><CalendarDays className="w-4 h-4" />Day {state.day + 1}/{state.total_days}</span>
          <span className="inline-flex items-center gap-1"><Wallet className="w-4 h-4" />{Math.round(state.portfolio_value).toLocaleString()}</span>
          {state.companion && (
            <span className="inline-flex items-center gap-1"><Users className="w-4 h-4" />{NPC_NAME[state.companion] ?? state.companion}</span>
          )}
        </div>

        <EmotionGauge emotion={state.emotion} verdict={state.verdict} />
        <PortfolioPanel holdings={state.holdings} />

        {/* 동행 체인(만남) — 있으면 먼저 */}
        {chain && (
          <PixelPanel tone="path" className="p-4">
            <div className="text-[11px] text-pixel-muted mb-1">
              {NPC_NAME[chain.npc_id] ?? chain.npc_id}{chain.place ? ` · ${chain.place}` : ""}
            </div>
            <h3 className="text-sm font-extrabold mb-2">{chain.title}</h3>
            <p className="text-[13px] leading-relaxed mb-3 whitespace-pre-line">{chain.text}</p>
            <div className="flex flex-col gap-2">
              {chain.choices.map((c) => (
                <PixelButton key={c.id} variant="secondary" disabled={busy}
                  onClick={act(() => api.chooseChain(state.game_id, c.id))}>
                  {c.label}
                </PixelButton>
              ))}
            </div>
          </PixelPanel>
        )}

        {/* 게시판 강제노출 + 선택지 */}
        {board && (
          <PixelPanel tone="wall" className="p-4">
            <div className="text-[11px] text-pixel-muted mb-2">게시판 · 여론 {board.verdict}</div>
            <div className="flex flex-col gap-1.5 mb-4 max-h-40 overflow-y-auto">
              {board.threads.slice(0, 5).map((t, i) => (
                <div key={i} className="text-[11px] bg-black/[0.03] rounded px-2 py-1">
                  <span className="font-bold">{NPC_NAME[t.author_id] ?? t.author_id}</span> {t.text}
                </div>
              ))}
            </div>
            <p className="text-[13px] leading-relaxed mb-3">{board.scenario.text}</p>
            <div className="flex flex-col gap-2">
              {board.scenario.choices.map((c) => (
                <PixelButton key={c.id} disabled={busy || !!chain}
                  onClick={act(() => api.choose(state.game_id, c.id))}>
                  {c.label}
                </PixelButton>
              ))}
            </div>
            {chain && <p className="text-[11px] text-pixel-muted mt-2">먼저 위 만남에 응답하세요.</p>}
          </PixelPanel>
        )}
      </div>
    </main>
  );
}
