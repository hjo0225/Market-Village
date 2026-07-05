"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import PixelButton from "@/components/pixel/PixelButton";
import { CONTEXT_HEAD, PostCard, VERDICT_LABEL } from "@/components/BoardEventModal";
import { api, BoardFeed, NPC_LABELS, NPC_ROLES } from "@/lib/api";

const FGI_TONES = [
  { value: "calm", label: "휩쓸리지 마" },
  { value: "clarify", label: "사실 차분히 짚기" },
  { value: "fear_join", label: "같이 무서워하기" },
];

// §9.5.3 매매 에이전트 8종(T-221/T-246) — 이름·역할은 api.ts 단일 소스에서.
// 순서 = 도움 4 → 자극 4.
const NPC_ORDER = [
  "value_investor", "quant_trader", "macro_whale", "contrarian",
  "panic_ant", "fomo_scalper", "conspiracy_influencer", "jackpot_gambler",
];
const NPCS = NPC_ORDER.map((value) => (
  { value, label: `${NPC_LABELS[value] ?? value} (${NPC_ROLES[value] ?? ""})` }));

// T-262 — 1:1은 결과 한 줄이 아니라 대화 왕복(채팅 버블). 내 발화·NPC 응답은
// 표현 계층 오프라인 고정 문구(페르소나 톤, personas.py style 참조해 작성).
const MY_LINE: Record<"calm" | "escalate", string> = {
  calm: "요즘 시장에 너무 휩쓸리는 것 같아서. 오늘은 좀 차분하게 가자.",
  escalate: "지금 이 흐름 안 보여? 이럴 때 세게 가야지.",
};
const NPC_REPLY: Record<string, { ok: string; no: string }> = {
  panic_ant: { ok: "…그래, 손 떨렸는데 네 말 들으니 좀 낫다. 오늘은 안 던질게.",
               no: "아니야, 이번엔 진짜 떨어진다니까. 나 먼저 나간다." },
  fomo_scalper: { ok: "하긴… 매번 꼭지에서 샀지. 오늘은 좀 참아본다.",
                  no: "야, 지금 올라타야 돼. 늦으면 국물도 없어." },
  conspiracy_influencer: { ok: "흠, 네가 그렇게까지 말하면… 오늘은 조용히 있어보지.",
                           no: "이거 다 세력이 흔드는 거라니까? 내 말 들어." },
  value_investor: { ok: "동의하네. 원칙대로 가는 게 맞지.",
                    no: "글쎄, 난 내 계산을 믿겠네." },
  quant_trader: { ok: "데이터도 비슷한 말을 하네. 반영할게.",
                  no: "감정 얘기는 됐고. 시그널은 아직이야." },
  macro_whale: { ok: "자네 말에도 일리가 있군. 참고하지.",
                 no: "큰 그림은 안 바뀌었어. 난 그대로 간다." },
  contrarian: { ok: "…다들 반대로 말하는 걸 보니 오히려 네 말이 맞을지도.",
                no: "다들 그렇게 말할 때가 제일 위험한 거야." },
  jackpot_gambler: { ok: "쩝, 알았어. 오늘은 판돈 좀 줄인다.",
                     no: "인생 한 방이지! 말리지 마라." },
};

interface ChatMsg { who: "me" | "npc"; npcId?: string; text: string; meta?: string }

interface Props {
  isOpen: boolean;
  onClose: () => void;
  gameId: string;
  rapport: number;
  crowdMood: number;
  onChanged: () => void;
}

// DESIGN.md §2 "진짜 휴대폰" — 검정 베젤+노치+상태바+흰 화면+홈 인디케이터(§9.1b 핸드폰).
export default function PhoneModal({ isOpen, onClose, gameId, rapport, crowdMood, onChanged }: Props) {
  const [tab, setTab] = useState<"board" | "feed" | "dm">("board");
  const [fgiTone, setFgiTone] = useState("calm");
  const [fgiResult, setFgiResult] = useState("");
  const [npc, setNpc] = useState(NPCS[0].value);
  const [chat, setChat] = useState<ChatMsg[]>([]);   // T-262 — 대화 로그
  const [busy, setBusy] = useState(false);
  // T-257 — 게시판 상시 진입점(발견성): 이벤트 날이 아니어도 지난 수다를 읽는다.
  const [board, setBoard] = useState<BoardFeed | null>(null);
  // /review — 조회 실패 시 무한 스피너 방지: 에러 상태+재시도 버튼.
  const [boardError, setBoardError] = useState(false);
  const [boardTry, setBoardTry] = useState(0);

  useEffect(() => {
    if (!isOpen || tab !== "board") return;
    let alive = true;
    setBoardError(false);
    api.gameBoard(gameId).then((b) => {
      if (!alive) return;
      if (b.status === "ok") setBoard(b);
      else setBoardError(true);
    });
    return () => { alive = false; };
  }, [isOpen, tab, gameId, boardTry]);

  if (!isOpen) return null;

  async function doFgi() {
    setBusy(true);
    // roll은 매번 진짜 난수여야 한다 — 고정값을 쓰면 결과가 항상 같아진다
    // (버그: 이전엔 roll=50 고정이라 초기 래포50/성공률50%에서 1:1이 항상
    // 실패했다. 사용자 피드백 2026-07-01 "1:1대화·FGI가 제대로 진행이 안돼").
    const r = await api.fgi(gameId, fgiTone, Math.random() * 100);
    // /review — POST는 재시도가 없으므로(T-258 멱등성) 실패를 결과로 위장하면
    // NaN이 노출된다: 실패는 실패라고 말한다.
    if (r.status !== "ok") {
      setFgiResult("⚠️ 전송이 안 됐어요 — 다시 눌러주세요");
      setBusy(false); return;
    }
    setFgiResult(r.absorbed ? "🌊 묻힘(군중 극단)" : `📣 군중온도 ${Math.round(r.crowd_mood)}로 이동`);
    setBusy(false); onChanged();
  }

  async function doPersuade(direction: "calm" | "escalate") {
    setBusy(true);
    setChat((c) => [...c, { who: "me", text: MY_LINE[direction] }]);
    const r = await api.persuade(gameId, npc, direction, Math.random() * 100);
    if (r.status !== "ok") {
      // /review — 실패를 "씹힘(NaN)"으로 위장하지 않는다: 대화는 안 일어난 것.
      setChat((c) => [...c, { who: "npc", npcId: npc,
        text: "…(연결이 끊겼다. 메시지가 전달되지 않았다)",
        meta: "⚠️ 전송 실패 — 다시 시도해주세요" }]);
      setBusy(false); return;
    }
    const reply = NPC_REPLY[npc] ?? { ok: "…그래, 알았어.", no: "…글쎄, 난 잘 모르겠는데." };
    setChat((c) => [...c, {
      who: "npc", npcId: npc,
      // T-c — 서버가 기억·개별 래포를 반영한 응답(npc_line)을 주면 우선.
      text: r.npc_line ?? (r.accepted ? reply.ok : reply.no),
      meta: `${r.accepted ? "✅ 먹힘" : "❌ 씹힘"} · 성공률 ${Math.round(r.success_prob)}% · 래포 ${Math.round(r.rapport)}`,
    }]);
    setBusy(false); onChanged();
  }

  return (
    <div role="dialog" aria-modal="true" className="fixed inset-0 z-[130] flex items-center justify-center">
      <div className="absolute inset-0 bg-pixel-ink/60" onClick={onClose} />
      <div className="relative w-[300px] bg-pixel-ink rounded-[36px] p-3 shadow-phone border-2 border-black animate-pixel-pop">
        {/* 다이내믹 아일랜드 */}
        <div className="absolute left-1/2 -translate-x-1/2 top-4 w-20 h-5 bg-black rounded-full z-10" />
        <button
          onClick={onClose}
          aria-label="닫기"
          className="absolute -right-3 -top-3 w-7 h-7 rounded-full bg-white border-2 border-black flex items-center justify-center"
        >
          <X size={13} />
        </button>
        {/* 화면 */}
        <div className="bg-white rounded-[26px] overflow-hidden border-2 border-black min-h-[420px] flex flex-col">
          {/* 상태바 */}
          <div className="flex items-center justify-between px-4 pt-6 pb-1 text-[10px] font-bold text-black">
            <span>9:41</span>
            <span>📶 🔋</span>
          </div>
          {/* 탭 */}
          <div className="flex border-b-2 border-black">
            <button
              className={`flex-1 py-2 text-[12px] font-bold ${tab === "board" ? "bg-pixel-grass" : "bg-white"}`}
              onClick={() => setTab("board")}
            >🪧 게시판</button>
            <button
              className={`flex-1 py-2 text-[12px] font-bold border-l-2 border-black ${tab === "feed" ? "bg-pixel-grass" : "bg-white"}`}
              onClick={() => setTab("feed")}
            >💬 피드</button>
            <button
              className={`flex-1 py-2 text-[12px] font-bold border-l-2 border-black ${tab === "dm" ? "bg-pixel-grass" : "bg-white"}`}
              onClick={() => setTab("dm")}
            >📱 1:1</button>
          </div>

          <div className="flex-1 p-3 flex flex-col gap-3">
            {tab === "board" ? (
              boardError && board === null ? (
                <div className="py-8 text-center flex flex-col items-center gap-2">
                  <p className="text-[12px] text-pixel-muted">⚠️ 게시판을 못 불러왔어요.</p>
                  <PixelButton size="sm" onClick={() => setBoardTry((n) => n + 1)}>다시 시도</PixelButton>
                </div>
              ) : board === null ? (
                <div className="py-10 text-center text-[12px] text-pixel-muted animate-pulse">💬 게시판 여는 중…</div>
              ) : board.open ? (
                <>
                  {/* T-260 — 이벤트 모달과 같은 헤더(컨텍스트+여론)로 두 화면 정합 */}
                  <div className="text-[11px] text-pixel-muted">
                    {CONTEXT_HEAD[board.context ?? ""] ?? "오늘 마을이 시끄럽다"}
                    {board.verdict && <b className="ml-1 text-black">{VERDICT_LABEL[board.verdict]}</b>}
                  </div>
                  <div className="flex flex-col gap-2 max-h-[300px] overflow-y-auto">
                    {board.posts.map((p, i) => <PostCard key={i} post={p} index={i} />)}
                  </div>
                </>
              ) : board.recent ? (
                <>
                  <div className="text-[11px] text-pixel-muted">
                    오늘은 조용해요. 아래는 <b className="text-black">Day {board.recent.day}</b>의 수다(지난 기록) —
                    시장이 크게 흔들리거나 큰 뉴스가 뜨는 날 새 글이 올라와요.
                  </div>
                  <div className="flex flex-col gap-2 max-h-[300px] overflow-y-auto">
                    {board.recent.posts.map((p, i) => <PostCard key={i} post={p} index={i} />)}
                  </div>
                </>
              ) : (
                <div className="text-[11px] text-pixel-muted py-6 text-center">
                  아직 게시판에 글이 없어요.<br />
                  시장이 크게 흔들리거나(급등락) 큰 뉴스가 뜨는 날, 마을 사람들이 여기 모여 수다를 떨어요.
                </div>
              )
            ) : tab === "feed" ? (
              <>
                <div className="text-[11px] text-pixel-muted">FGI 단톡방 · 군중온도 <b>{Math.round(crowdMood)}</b> (0 공포↔100 탐욕 · 래포 무관, 약함)</div>
                <select className="border-2 border-black rounded-lg px-2 py-1.5 text-[12px]" value={fgiTone} onChange={(e) => setFgiTone(e.target.value)}>
                  {FGI_TONES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
                <PixelButton size="sm" disabled={busy} onClick={doFgi}>글 올리기</PixelButton>
                {fgiResult && <div className="text-[11px] font-bold animate-fade-in">{fgiResult}</div>}
              </>
            ) : (
              <>
                <div className="text-[11px] text-pixel-muted">1:1 대화 · 래포 <b>{Math.round(rapport)}</b> (위기개입과 같은 풀)</div>
                <select className="border-2 border-black rounded-lg px-2 py-1.5 text-[12px]" value={npc}
                  onChange={(e) => { setNpc(e.target.value); setChat([]); }}>
                  {NPCS.map((n) => <option key={n.value} value={n.value}>{n.label}</option>)}
                </select>
                {/* T-262 — 대화 로그(채팅 버블): 내 발화 → 상대 응답 왕복 */}
                {chat.length > 0 && (
                  <div className="flex flex-col gap-1.5 max-h-[200px] overflow-y-auto pr-1">
                    {chat.map((m, i) => m.who === "me" ? (
                      <div key={i} className="self-end max-w-[85%] bg-pixel-grass/60 border border-black/20 rounded-xl rounded-br-sm px-2.5 py-1.5 text-[11px] animate-fade-in">
                        {m.text}
                      </div>
                    ) : (
                      <div key={i} className="self-start max-w-[85%] animate-fade-in">
                        <p className="text-[9px] font-bold text-pixel-muted mb-0.5">
                          {NPC_LABELS[m.npcId ?? ""] ?? m.npcId} · {NPC_ROLES[m.npcId ?? ""] ?? ""}
                        </p>
                        <div className="bg-slate-100 border border-black/20 rounded-xl rounded-bl-sm px-2.5 py-1.5 text-[11px]">
                          {m.text}
                        </div>
                        {m.meta && <p className="text-[9px] font-bold text-pixel-muted mt-0.5">{m.meta}</p>}
                      </div>
                    ))}
                  </div>
                )}
                <div className="flex gap-2">
                  <PixelButton size="sm" disabled={busy} onClick={() => doPersuade("calm")}>안정으로</PixelButton>
                  <PixelButton size="sm" variant="secondary" disabled={busy} onClick={() => doPersuade("escalate")}>격화로</PixelButton>
                </div>
              </>
            )}
          </div>
          {/* 홈 인디케이터 */}
          <div className="flex justify-center pb-2">
            <div className="w-24 h-1 bg-black/70 rounded-full" />
          </div>
        </div>
      </div>
    </div>
  );
}
