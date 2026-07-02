"use client";

// T-231 — 설정 1/2단계: 인터뷰만 (한 페이지 한 목적).
// 인터뷰 완료 → 감정 성향 확정 카드 → [확정] 시 저장(await) 후 포트폴리오 단계로.
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import PixelButton from "@/components/pixel/PixelButton";
import PixelPanel from "@/components/pixel/PixelPanel";
import { api } from "@/lib/api";
import { setSetupAnswers } from "@/lib/session";

type Trait = { id: string; name: string; score: number };

export default function SetupPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"slider" | "chat">("slider");
  const [sliders, setSliders] = useState({ q_panic: 0.7, q_fomo: 0.3, q_rumor: 0.5, q_check: 0.5 });

  // -- 대화형 인터뷰 상태 (챗봇형 — T-SVC8 테스트: use_llm=true) --
  const [sessionId] = useState(() => "iv-" + Date.now());
  const [ivQid, setIvQid] = useState<string | null>(null);
  const [chatLog, setChatLog] = useState<{ role: "bot" | "user"; text: string }[]>([]);
  const [ivAnswerText, setIvAnswerText] = useState("");
  const [ivBusy, setIvBusy] = useState(false);
  const [ivDone, setIvDone] = useState(false);
  const [ivAnswers, setIvAnswers] = useState<Record<string, number> | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // -- 확정 단계 상태 --
  const [traits, setTraits] = useState<Trait[] | null>(null);
  const [previewBusy, setPreviewBusy] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatLog, ivBusy]);

  const answers = mode === "chat" ? ivAnswers : sliders;
  const interviewDone = mode === "slider" || ivDone;

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
    setMode("chat"); setIvDone(false); setIvAnswers(null); setChatLog([]); setTraits(null);
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

  // 인터뷰 산출물 → 성향 프리뷰(서버 순수 계산) — 확정 카드에 표시.
  async function loadPreview() {
    if (!answers) return;
    setPreviewBusy(true);
    setConfirmError(null);
    const r = await api.clonePreview(answers);
    setPreviewBusy(false);
    if (r.status !== "ok") { setConfirmError("성향 계산에 실패했어요. 다시 시도해주세요."); return; }
    setTraits(r.traits);
  }

  // [확정] — 저장이 끝난 뒤에만 다음 단계로 이동(비동기 유실 방지).
  function confirmAndNext() {
    if (!answers) return;
    try {
      setSetupAnswers(answers);
    } catch {
      setConfirmError("답변 저장에 실패했어요. 브라우저 저장소를 확인해주세요.");
      return;
    }
    router.push("/setup/portfolio");
  }

  return (
    <main className="min-h-screen bg-white p-6">
      <div className="max-w-lg mx-auto">
        <h1 className="text-xl font-extrabold mb-1">🧬 복제 — 심층 인터뷰 <span className="text-xs text-pixel-muted font-bold">(1/2단계)</span></h1>
        <p className="text-xs text-pixel-muted mb-4">인터뷰로 클론의 감정 성향을 확정하면, 다음 단계에서 포트폴리오를 정합니다.</p>

        <PixelPanel tone="cloud" className="p-5 mb-4 animate-slide-up">
          <div className="flex gap-2 mb-4">
            <PixelButton size="sm" variant={mode === "slider" ? "primary" : "ghost"}
              onClick={() => { setMode("slider"); setTraits(null); }}>
              🎚 슬라이더 (빠름)
            </PixelButton>
            <PixelButton size="sm" variant={mode === "chat" ? "primary" : "ghost"} onClick={startChatMode}>
              🗣 대화형 인터뷰
            </PixelButton>
          </div>

          {mode === "slider" && (
            <div className="flex flex-col gap-4">
              <SliderRow label="급락장 첫 반응 (버팀 0 ↔ 손절 1)" value={sliders.q_panic}
                onChange={(v) => { setSliders((s) => ({ ...s, q_panic: v })); setTraits(null); }} />
              <SliderRow label="급등장 (관망 0 ↔ 추격 1)" value={sliders.q_fomo}
                onChange={(v) => { setSliders((s) => ({ ...s, q_fomo: v })); setTraits(null); }} />
              <SliderRow label="루머 (확인 0 ↔ 흔들림 1)" value={sliders.q_rumor}
                onChange={(v) => { setSliders((s) => ({ ...s, q_rumor: v })); setTraits(null); }} />
              <SliderRow label="시세창 (가끔 0 ↔ 수시 1)" value={sliders.q_check}
                onChange={(v) => { setSliders((s) => ({ ...s, q_check: v })); setTraits(null); }} />
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
                  <p className="text-sm text-pixel-greenText font-bold mt-1">✓ 인터뷰 완료 — 아래에서 성향을 확인하고 확정하세요.</p>
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

        {/* 확정 카드 — 인터뷰가 끝나야 열리고, 수치를 본 뒤에만 다음 단계로 */}
        <PixelPanel tone="cloud" className="p-5 animate-slide-up">
          <h2 className="text-sm font-extrabold mb-2">🪞 클론 감정 성향 확정</h2>
          {!interviewDone ? (
            <p className="text-xs text-pixel-muted">인터뷰를 먼저 마쳐주세요.</p>
          ) : traits === null ? (
            <div className="flex items-center justify-between">
              <p className="text-xs text-pixel-muted">답변이 만들 클론의 성향을 계산해보세요.</p>
              <PixelButton size="sm" disabled={previewBusy || !answers} onClick={loadPreview}>
                {previewBusy ? "계산 중…" : "성향 보기"}
              </PixelButton>
            </div>
          ) : (
            <div>
              <div className="flex flex-col gap-2 mb-3">
                {traits.map((t) => (
                  <div key={t.id}>
                    <div className="flex justify-between text-xs mb-0.5">
                      <span className="text-pixel-muted">{t.name} 취약도</span>
                      <span className="font-bold">{Math.round(t.score)}</span>
                    </div>
                    <div className="h-2 bg-black/10 rounded">
                      <div
                        className={`h-2 rounded ${t.score >= 60 ? "bg-pixel-danger" : "bg-pixel-grass"}`}
                        style={{ width: `${Math.min(100, Math.max(0, t.score))}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <div className="flex justify-end gap-2">
                <PixelButton size="sm" variant="ghost" onClick={() => setTraits(null)}>다시 조정</PixelButton>
                <PixelButton size="sm" onClick={confirmAndNext}>이 성향으로 확정 → 포트폴리오</PixelButton>
              </div>
            </div>
          )}
          {confirmError && <p className="text-sm text-red-600 mt-2 text-right">{confirmError}</p>}
        </PixelPanel>
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
