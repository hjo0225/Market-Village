"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import PixelButton from "@/components/pixel/PixelButton";
import PixelPanel from "@/components/pixel/PixelPanel";
import { api, CATEGORY_LABELS } from "@/lib/api";
import { newGameId, setGameId } from "@/lib/session";

const SYMBOLS = ["DOGE", "BTC", "SOL", "USDT"];
const CATEGORIES = ["large_stable", "mid_alt", "meme", "stable"];

export default function SetupPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"slider" | "chat">("slider");
  const [symbol, setSymbol] = useState("DOGE");
  const [sliders, setSliders] = useState({ q_panic: 0.7, q_fomo: 0.3, q_rumor: 0.5, q_check: 0.5 });
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  // -- 분산해서 시작 (T-215 D1, 기본 꺼짐) --
  const [diversify, setDiversify] = useState(false);
  const [allocations, setAllocations] = useState<Record<string, number>>({
    large_stable: 25, mid_alt: 25, meme: 25, stable: 25,
  });
  const allocationTotal = CATEGORIES.reduce((sum, c) => sum + (allocations[c] ?? 0), 0);
  const allocationValid = allocationTotal === 100;

  // -- 대화형 인터뷰 상태 (챗봇형 — T-SVC8 테스트: use_llm=true로 질문 표현+답변 해석) --
  const [sessionId] = useState(() => "iv-" + Date.now());
  const [ivQid, setIvQid] = useState<string | null>(null);
  const [chatLog, setChatLog] = useState<{ role: "bot" | "user"; text: string }[]>([]);
  const [ivAnswerText, setIvAnswerText] = useState("");
  const [ivBusy, setIvBusy] = useState(false);
  const [ivDone, setIvDone] = useState(false);
  const [ivAnswers, setIvAnswers] = useState<Record<string, number> | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatLog, ivBusy]);

  async function loadNextQuestion() {
    setIvBusy(true);
    const r = await api.interviewNext(sessionId, true);
    setIvBusy(false);
    if (r.status !== "ok") return;   // 네트워크 플레이크 — 다음 클릭에서 재시도됨
    if (r.done) { setIvDone(true); setIvAnswers(r.answers ?? null); setIvQid(null); return; }
    setIvQid(r.next!.id);
    setChatLog((log) => [...log, { role: "bot", text: r.next!.text }]);
  }

  async function startChatMode() {
    setMode("chat"); setIvDone(false); setIvAnswers(null); setChatLog([]);
    await loadNextQuestion();
  }

  async function submitAnswer() {
    if (!ivQid || !ivAnswerText.trim() || ivBusy) return;
    const answerText = ivAnswerText.trim();
    setChatLog((log) => [...log, { role: "user", text: answerText }]);
    setIvAnswerText("");
    setIvBusy(true);
    const r = await api.interviewAnswer(sessionId, ivQid, answerText, true);
    setIvBusy(false);
    if (r.status !== "ok") return;   // 네트워크 플레이크 — 다음 클릭에서 재시도됨
    if (r.done) { setIvDone(true); setIvAnswers(r.answers ?? null); setIvQid(null); }
    else { setIvQid(r.next!.id); setChatLog((log) => [...log, { role: "bot", text: r.next!.text }]); }
  }

  async function handleStart() {
    setStarting(true);
    setStartError(null);
    try {
      const answers = mode === "chat" && ivAnswers ? ivAnswers : sliders;
      const gameId = newGameId();
      const r = await api.gameStart(gameId, answers, symbol, 100.0, diversify ? allocations : undefined);
      if (r.status !== "ok") {
        setStartError("서버 연결에 실패했어요. 잠시 후 다시 시도해주세요.");
        return;
      }
      setGameId(gameId);
      router.push("/play");
    } finally {
      setStarting(false);
    }
  }

  const canStart = (mode === "slider" || (mode === "chat" && ivDone)) && (!diversify || allocationValid);

  return (
    <main className="min-h-screen bg-white p-6">
      <div className="max-w-lg mx-auto">
        <h1 className="text-xl font-extrabold mb-4">🧬 복제 — 심층 인터뷰</h1>
        <PixelPanel tone="cloud" className="p-5 mb-4 animate-slide-up">
          <div className="flex gap-2 mb-4">
            <PixelButton size="sm" variant={mode === "slider" ? "primary" : "ghost"} onClick={() => setMode("slider")}>
              🎚 슬라이더 (빠름)
            </PixelButton>
            <PixelButton size="sm" variant={mode === "chat" ? "primary" : "ghost"} onClick={startChatMode}>
              🗣 대화형 인터뷰
            </PixelButton>
          </div>

          {mode === "slider" && (
            <div className="flex flex-col gap-4">
              <SliderRow label="급락장 첫 반응 (버팀 0 ↔ 손절 1)" value={sliders.q_panic}
                onChange={(v) => setSliders((s) => ({ ...s, q_panic: v }))} />
              <SliderRow label="급등장 (관망 0 ↔ 추격 1)" value={sliders.q_fomo}
                onChange={(v) => setSliders((s) => ({ ...s, q_fomo: v }))} />
              <SliderRow label="루머 (확인 0 ↔ 흔들림 1)" value={sliders.q_rumor}
                onChange={(v) => setSliders((s) => ({ ...s, q_rumor: v }))} />
              <SliderRow label="시세창 (가끔 0 ↔ 수시 1)" value={sliders.q_check}
                onChange={(v) => setSliders((s) => ({ ...s, q_check: v }))} />
            </div>
          )}

          {mode === "chat" && (
            <div>
              <div className="flex flex-col gap-2 max-h-[360px] overflow-y-auto mb-3 pr-1">
                {chatLog.map((m, i) => (
                  <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div
                      className={`max-w-[80%] text-sm rounded-lg px-3 py-2 border-2 border-black ${
                        m.role === "user" ? "bg-pixel-grass" : "bg-pixel-path"
                      }`}
                    >
                      {m.text}
                    </div>
                  </div>
                ))}
                {ivBusy && (
                  <div className="flex justify-start">
                    <div className="text-sm rounded-lg px-3 py-2 border-2 border-black bg-pixel-path text-pixel-muted">
                      …
                    </div>
                  </div>
                )}
                {ivDone && (
                  <p className="text-sm text-pixel-greenText font-bold mt-1">✓ 인터뷰 완료 — 아래에서 게임을 시작하세요.</p>
                )}
                <div ref={chatEndRef} />
              </div>
              {!ivDone && (
                <div className="flex gap-2">
                  <input
                    className="flex-1 border-2 border-black rounded-lg px-3 py-2 text-sm"
                    placeholder="자유롭게 답해주세요"
                    value={ivAnswerText}
                    disabled={ivBusy}
                    onChange={(e) => setIvAnswerText(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && submitAnswer()}
                  />
                  <PixelButton size="sm" disabled={ivBusy} onClick={submitAnswer}>답변</PixelButton>
                </div>
              )}
            </div>
          )}
        </PixelPanel>

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

function SliderRow({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <div>
      <div className="text-xs text-pixel-muted mb-1">{label}</div>
      <input
        type="range" min={0} max={1} step={0.1} value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full accent-black"
      />
    </div>
  );
}
