"use client";

import { useEffect, useMemo, useState } from "react";
import Image from "next/image";
import { X } from "lucide-react";
import PixelButton from "@/components/pixel/PixelButton";
import PhoneFrame from "@/components/PhoneFrame";
import { CONTEXT_HEAD, PostCard, VERDICT_LABEL } from "@/components/BoardEventModal";
import { TONE_STYLE } from "@/components/NewsModal";
import { PreviewBody } from "@/components/PreviewModal";
import {
  api, BoardFeed, ChatLogDay, Designated, HistoryDay, Meetings,
  NPC_LABELS, NPC_PORTRAITS, NPC_ROLES, Picks,
} from "@/lib/api";

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

interface ChatMsg { who: "me" | "npc"; text: string; meta?: string }

interface Props {
  isOpen: boolean;
  onClose: () => void;
  gameId: string;
  day: number;
  rapport: number;
  crowdMood: number;
  onChanged: () => void;
  // T-283 — 🌙 일과 탭(구 전날밤 모달 임베드)
  meetings: Meetings;
  picks: Picks;
  designated: Designated;
  schedule: Record<string, string>;
  // T-288 — 📜 이벤트 타임라인 + 💬 메신저 연락처의 데이터 소스(발자취)
  history: HistoryDay[];
}

function Avatar({ npcId, size = 32 }: { npcId: string; size?: number }) {
  const portrait = NPC_PORTRAITS[npcId];
  return portrait ? (
    <Image
      src={`/assets/characters/profile/${portrait}.png`}
      alt={NPC_LABELS[npcId] ?? npcId} width={size} height={size}
      className="rounded-full border-2 border-black bg-pixel-grass/30 shrink-0"
      unoptimized
    />
  ) : (
    <span
      style={{ width: size, height: size }}
      className="rounded-full border-2 border-black bg-pixel-grass/40 flex items-center justify-center text-[15px] shrink-0"
    >🤖</span>
  );
}

// T-288 — 📜 지난 이벤트: 발자취를 폰 타임라인으로(뉴스 톤·위기·만남).
function EventsTab({ history }: { history: HistoryDay[] }) {
  const days = [...history].reverse();   // 최신 위로
  if (days.length === 0) {
    return <p className="text-[12px] text-pixel-muted py-8 text-center">아직 지나온 날이 없어요.</p>;
  }
  return (
    <div className="flex flex-col gap-2 overflow-y-auto max-h-[340px] pr-1">
      {days.map((d) => {
        const tone = TONE_STYLE[d.news_tone] ?? null;
        return (
          <div key={d.day} className="shrink-0 rounded-xl border-2 border-black bg-white p-2.5 shadow-pixel-sm">
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-extrabold">Day {d.day}</span>
              {tone && (
                <span className={`text-[10px] font-bold rounded px-1 ${tone.chip} ${tone.text}`}>
                  {tone.icon} {tone.label} 뉴스
                </span>
              )}
              {d.trap && (
                <span className={`text-[10px] font-bold rounded px-1 ${
                  d.swayed ? "bg-rose-100 text-rose-700" : "bg-emerald-100 text-emerald-700"}`}>
                  ⚡ 위기 — {d.swayed ? "휩쓸림" : "버팀"}
                </span>
              )}
            </div>
            {d.met.length > 0 && (
              <p className="text-[11px] text-pixel-muted mt-1">
                🤝 {d.met.map((m) => NPC_LABELS[m] ?? m).join(", ")}와 만남
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

// T-288 — 💬 메시지: 그동안 대화한 NPC 목록 → 누르면 대화방(지난 로그+권유).
function MessengerTab({ gameId, history, rapport, busy, setBusy, onChanged }: {
  gameId: string; history: HistoryDay[]; rapport: number;
  busy: boolean; setBusy: (b: boolean) => void; onChanged: () => void;
}) {
  const [openNpc, setOpenNpc] = useState<string | null>(null);
  const [log, setLog] = useState<ChatLogDay[] | null>(null);
  const [live, setLive] = useState<ChatMsg[]>([]);

  // 연락처 = 발자취의 만남 + 권유 상대(최근 대화가 위로).
  const contacts = useMemo(() => {
    const lastDay = new Map<string, number>();
    for (const d of history) {
      for (const m of d.met) lastDay.set(m, d.day);
      for (const s of d.social) {
        if (s.npc_id) lastDay.set(s.npc_id, d.day);
      }
    }
    return Array.from(lastDay.entries()).sort((a, b) => b[1] - a[1]);
  }, [history]);

  useEffect(() => {
    if (!openNpc) return;
    setLog(null);
    setLive([]);
    void api.gameChatLog(gameId, openNpc).then((r) => {
      if (r.status === "ok") setLog(r.days);
      else setLog([]);
    }).catch(() => setLog([]));
  }, [openNpc, gameId]);

  async function doPersuade(direction: "calm" | "escalate") {
    if (!openNpc || busy) return;
    setBusy(true);
    setLive((c) => [...c, { who: "me", text: MY_LINE[direction] }]);
    try {
      // 진짜 난수 roll(사용자 피드백 2026-07-01 — 고정 roll이면 결정론 실패).
      const r = await api.persuade(gameId, openNpc, direction, Math.random() * 100);
      const reply = NPC_REPLY[openNpc] ?? { ok: "…그래, 알았어.", no: "…글쎄, 난 잘 모르겠는데." };
      if (r.status === "ok") {
        setLive((c) => [...c, {
          who: "npc",
          text: r.npc_line ?? (r.accepted ? reply.ok : reply.no),
          meta: `${r.accepted ? "통했다" : "씹혔다"} · 래포 ${Math.round(r.rapport)}`,
        }]);
        onChanged();
      } else {
        setLive((c) => [...c, { who: "npc", text: "…(연결이 끊겼다)", meta: "다시 시도해 주세요" }]);
      }
    } catch {
      setLive((c) => [...c, { who: "npc", text: "…(연결이 끊겼다)", meta: "다시 시도해 주세요" }]);
    } finally {
      setBusy(false);
    }
  }

  if (!openNpc) {
    return contacts.length === 0 ? (
      <p className="text-[12px] text-pixel-muted py-8 text-center">
        아직 대화한 사람이 없어요.<br />마을에서 누군가와 마주치면 여기 쌓여요.
      </p>
    ) : (
      <div className="flex flex-col overflow-y-auto max-h-[340px]">
        {contacts.map(([npc, day]) => (
          <button
            key={npc}
            onClick={() => setOpenNpc(npc)}
            className="flex items-center gap-2.5 px-1 py-2 border-b border-black/10 text-left cursor-pointer hover:bg-slate-50"
          >
            <Avatar npcId={npc} size={36} />
            <span className="flex-1 min-w-0">
              <span className="block text-[13px] font-extrabold leading-tight">
                {NPC_LABELS[npc] ?? npc}
                <span className="ml-1 text-[10px] text-pixel-muted font-bold">{NPC_ROLES[npc] ?? ""}</span>
              </span>
              <span className="block text-[11px] text-pixel-muted">Day {day}에 마지막 대화</span>
            </span>
            <span className="text-pixel-muted text-xs">›</span>
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <button
        onClick={() => setOpenNpc(null)}
        className="text-left text-[12px] font-extrabold cursor-pointer hover:underline underline-offset-2"
      >← 대화 목록</button>
      <div className="flex items-center gap-2">
        <Avatar npcId={openNpc} size={30} />
        <span className="text-[13px] font-extrabold">{NPC_LABELS[openNpc] ?? openNpc}</span>
        <span className="text-[10px] text-pixel-muted font-bold">{NPC_ROLES[openNpc] ?? ""}</span>
        <span className="ml-auto text-[10px] text-pixel-muted">래포 {Math.round(rapport)}</span>
      </div>
      <div className="flex flex-col gap-1.5 overflow-y-auto max-h-[240px] pr-1 bg-slate-50 rounded-lg p-2 border border-black/10">
        {log === null ? (
          <p className="text-[11px] text-pixel-muted text-center py-4 animate-pulse">대화 불러오는 중…</p>
        ) : log.length === 0 && live.length === 0 ? (
          <p className="text-[11px] text-pixel-muted text-center py-4">아직 나눈 대화가 없어요 — 아래에서 말을 걸어보세요.</p>
        ) : (
          log.map((d) => (
            <div key={d.day} className="flex flex-col gap-1.5">
              <p className="text-center text-[9px] font-bold text-pixel-muted">— Day {d.day} —</p>
              {d.entries.map((e, i) =>
                e.kind === "meeting" ? (
                  (e.lines ?? []).map((l, j) =>
                    l.who === "clone" ? (
                      <div key={`${i}-${j}`} className="self-end max-w-[85%] bg-pixel-grass/60 border border-black/20 rounded-xl rounded-br-sm px-2.5 py-1.5 text-[11px]">
                        {l.text}
                      </div>
                    ) : (
                      <div key={`${i}-${j}`} className="self-start max-w-[85%] bg-slate-100 border border-black/20 rounded-xl rounded-bl-sm px-2.5 py-1.5 text-[11px]">
                        {l.text}
                      </div>
                    ))
                ) : (
                  <p key={i} className="text-center text-[10px] font-bold text-pixel-muted">
                    {e.direction === "calm" ? "🕊 안정 권유" : "🔥 격화 부추김"} — {e.accepted ? "통했다" : "씹혔다"}
                  </p>
                ))}
            </div>
          ))
        )}
        {live.map((m, i) => m.who === "me" ? (
          <div key={`live-${i}`} className="self-end max-w-[85%] bg-pixel-grass/60 border border-black/20 rounded-xl rounded-br-sm px-2.5 py-1.5 text-[11px] animate-fade-in">
            {m.text}
          </div>
        ) : (
          <div key={`live-${i}`} className="self-start max-w-[85%] animate-fade-in">
            <div className="bg-slate-100 border border-black/20 rounded-xl rounded-bl-sm px-2.5 py-1.5 text-[11px]">{m.text}</div>
            {m.meta && <p className="text-[9px] font-bold text-pixel-muted mt-0.5">{m.meta}</p>}
          </div>
        ))}
      </div>
      {/* 클론의 마음을 흔드는 유일한 개입 창구(§9.2.2) — 위기개입과 같은 래포 풀 */}
      <div className="flex gap-2">
        <PixelButton size="sm" disabled={busy} onClick={() => doPersuade("calm")}>안정으로</PixelButton>
        <PixelButton size="sm" variant="secondary" disabled={busy} onClick={() => doPersuade("escalate")}>격화로</PixelButton>
      </div>
    </div>
  );
}

// T-288(사용자 지시) — 헤더 📱핸드폰을 게시판 이벤트와 같은 폰 프레임으로 통일.
// 탭: 🪧 게시판(라이브/아카이브) · 📜 이벤트(발자취 타임라인, 구 FGI 피드 대체 —
// 🙋 사용자 결정) · 💬 메시지(진짜 메신저: 연락처→대화방) · 🌙 일과(T-283).
export default function PhoneModal({ isOpen, onClose, gameId, day, rapport, crowdMood, onChanged,
                                      meetings, picks, designated, schedule, history }: Props) {
  const [tab, setTab] = useState<"board" | "events" | "dm" | "plan">("board");
  const [busy, setBusy] = useState(false);
  const [board, setBoard] = useState<BoardFeed | null>(null);
  const [boardError, setBoardError] = useState(false);
  const [boardTry, setBoardTry] = useState(0);

  useEffect(() => {
    if (!isOpen || tab !== "board") return;
    let alive = true;
    setBoardError(false);
    api.gameBoard(gameId).then((r) => {
      if (!alive) return;
      if (r.status === "ok") setBoard(r);
      else setBoardError(true);
    }).catch(() => { if (alive) setBoardError(true); });
    return () => { alive = false; };
  }, [isOpen, tab, gameId, boardTry]);

  if (!isOpen) return null;

  const TABS: { key: typeof tab; label: string }[] = [
    { key: "board", label: "🪧 게시판" },
    { key: "events", label: "📜 이벤트" },
    { key: "dm", label: "💬 메시지" },
    { key: "plan", label: "🌙 일과" },
  ];

  return (
    <div role="dialog" aria-modal="true" className="fixed inset-0 z-[120] flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="absolute inset-0 bg-pixel-ink/70" onClick={onClose} />
      <PhoneFrame day={day}>
        <button
          onClick={onClose}
          aria-label="닫기"
          className="absolute right-4 top-3 z-10 w-7 h-7 rounded-full bg-white border-2 border-black flex items-center justify-center cursor-pointer"
        >
          <X size={13} />
        </button>
        {/* 탭 바 */}
        <div className="flex border-b-2 border-black">
          {TABS.map((t, i) => (
            <button
              key={t.key}
              className={`flex-1 py-2 text-[12px] font-bold cursor-pointer ${i > 0 ? "border-l-2 border-black" : ""} ${
                tab === t.key ? "bg-pixel-grass" : "bg-white"}`}
              onClick={() => setTab(t.key)}
            >{t.label}</button>
          ))}
        </div>

        <div className="p-3 flex flex-col gap-3 min-h-[300px]">
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
                  <b className="ml-2 text-black">군중온도 {Math.round(crowdMood)}</b>
                </div>
                <div className="flex flex-col gap-2 max-h-[320px] overflow-y-auto">
                  {board.posts.map((p, i) => <PostCard key={i} post={p} index={i} />)}
                </div>
              </>
            ) : board.recent ? (
              <>
                <div className="text-[11px] text-pixel-muted">
                  오늘은 조용해요. 아래는 <b className="text-black">Day {board.recent.day}</b>의 수다(지난 기록) —
                  시장이 크게 흔들리거나 큰 뉴스가 뜨는 날 새 글이 올라와요.
                </div>
                <div className="flex flex-col gap-2 max-h-[320px] overflow-y-auto">
                  {board.recent.posts.map((p, i) => <PostCard key={i} post={p} index={i} />)}
                </div>
              </>
            ) : (
              <div className="text-[11px] text-pixel-muted py-6 text-center">
                아직 게시판에 글이 없어요.<br />
                시장이 크게 흔들리거나(급등락) 큰 뉴스가 뜨는 날, 마을 사람들이 여기 모여 수다를 떨어요.
              </div>
            )
          ) : tab === "events" ? (
            <EventsTab history={history} />
          ) : tab === "dm" ? (
            <MessengerTab
              gameId={gameId} history={history} rapport={rapport}
              busy={busy} setBusy={setBusy} onChanged={onChanged}
            />
          ) : (
            <div className="max-h-[340px] overflow-y-auto pr-1">
              <PreviewBody
                gameId={gameId} meetings={meetings} picks={picks}
                designated={designated} schedule={schedule} onChanged={onChanged}
              />
            </div>
          )}
        </div>
      </PhoneFrame>
    </div>
  );
}
