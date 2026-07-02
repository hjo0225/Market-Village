"use client";

import Image from "next/image";
import PixelButton from "@/components/pixel/PixelButton";
import { BoardFeed, BoardPost } from "@/lib/api";

// 게시판(SNS형 FGI) 이벤트 — PRD_SOCIAL_NPC_BOARD §3.0/§3.2 (D1·D3·D6).
// T-255(플레이테스트 리포트 ③) — 단순 모달이 아니라 **핸드폰이 올라오는** 연출:
// 마을이 걸음을 멈추고(❗, map board_gather 신호) 폰 프레임이 슬라이드업,
// 글이 트위터 피드처럼 순차 등장. 관찰 전용(개입은 핸드폰 피드 탭, D6).
const CONTEXT_HEAD: Record<string, string> = {
  fear: "⚡ 마을이 공포에 술렁인다",
  greed: "🍾 마을이 축제 분위기다",
  fomo: "🔥 다들 어딘가로 몰려간다",
  unrest: "🌫 마을이 뒤숭숭하다",
};
const VERDICT_LABEL: Record<string, string> = {
  up: "📈 마을 여론: 오른다 우세", down: "📉 마을 여론: 내린다 우세",
  split: "⚖️ 마을 여론: 팽팽하다",
};
const STANCE_BADGE: Record<string, { label: string; cls: string }> = {
  up: { label: "📈 오른다", cls: "bg-emerald-100 text-emerald-700" },
  down: { label: "📉 내린다", cls: "bg-rose-100 text-rose-700" },
};

interface Props {
  day: number;
  board: BoardFeed | null;   // null = 아직 로딩("모여드는 중…")
  onClose: () => void;
}

function Stance({ stance }: { stance?: string | null }) {
  const b = stance ? STANCE_BADGE[stance] : undefined;
  if (!b) return null;
  return <span className={`text-[9px] font-bold rounded px-1 ${b.cls}`}>{b.label}</span>;
}

function PostCard({ post, index }: { post: BoardPost; index: number }) {
  const isClone = post.author_kind === "clone";
  return (
    <div
      className={`rounded-xl border p-3 bg-white animate-pixel-pop ${
        isClone ? "border-pixel-grass shadow-[0_0_0_2px_rgba(74,222,128,0.4)]" : "border-black/20"}`}
      style={{ animationDelay: `${index * 0.28}s`, animationFillMode: "backwards" }}
    >
      <div className="flex items-center gap-2 mb-1.5">
        {post.portrait ? (
          <Image
            src={`/assets/characters/profile/${post.portrait}.png`}
            alt={post.author} width={24} height={24}
            className="rounded-full border border-black bg-pixel-grass/30"
            unoptimized
          />
        ) : (
          <span className="w-6 h-6 rounded-full border border-black bg-pixel-grass/40 flex items-center justify-center text-[12px]">🤖</span>
        )}
        <span className="text-[12px] font-extrabold">{post.author}</span>
        {/* T-246 — 이름 옆에 역할 부기(이름만으론 성격을 모르니). */}
        <span className="text-[10px] text-pixel-muted">· {post.author_role ?? "오늘"}</span>
        <Stance stance={post.stance} />
        {isClone && <span className="text-[10px] font-bold text-pixel-grass-dark bg-pixel-grass/20 rounded px-1">내 클론</span>}
      </div>
      <p className="text-[12px] leading-snug">{post.text}</p>
      {post.comments.length > 0 && (
        <div className="mt-2 pl-3 border-l-2 border-black/15 flex flex-col gap-1.5">
          {post.comments.map((c, i) => (
            <p key={i} className={`text-[11px] ${
              c.author_id === "clone" ? "bg-pixel-grass/15 rounded px-1 py-0.5" : "text-pixel-muted"}`}>
              <b className="text-black">{c.author}</b>{" "}
              {c.author_id === "clone" && (
                <span className="text-[9px] font-bold text-pixel-grass-dark">내 클론</span>
              )}{" "}
              <Stance stance={c.stance} /> {c.text}
            </p>
          ))}
          <p className="text-[9px] text-pixel-muted">댓글 {post.comments.length}개</p>
        </div>
      )}
    </div>
  );
}

export default function BoardEventModal({ day, board, onClose }: Props) {
  const delta = board ? Math.round(board.crowd_mood_delta) : 0;
  return (
    <div role="dialog" aria-modal="true" className="fixed inset-0 z-[135] flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="absolute inset-0 bg-pixel-ink/70" />
      {/* T-255 — 핸드폰 프레임: 하단에서 슬라이드업, 노치·상태바·피드 헤더. */}
      <div className="relative w-full max-w-sm bg-slate-900 border-2 border-black rounded-t-[28px] sm:rounded-[32px] shadow-pixel-md pt-2 pb-4 px-2 animate-[phoneup_0.45s_ease-out]">
        <style>{`@keyframes phoneup { from { transform: translateY(60%); opacity: 0.4; } to { transform: translateY(0); opacity: 1; } }`}</style>
        <div className="mx-auto w-24 h-1.5 rounded-full bg-slate-700 mb-1.5" />
        <div className="flex items-center justify-between px-4 text-[10px] text-slate-400 font-bold mb-1">
          <span>Day {day}</span><span>마을넷 📶 🔋</span>
        </div>
        <div className="bg-white rounded-2xl overflow-hidden">
          <div className="px-4 py-2.5 border-b border-black/10">
            <h2 className="text-sm font-extrabold">💬 마을 게시판</h2>
            <p className="text-[11px] text-pixel-muted">
              {board ? CONTEXT_HEAD[board.context ?? ""] ?? "오늘 마을이 시끄럽다" : "다들 게시판에 모여드는 중…"}
              {board?.verdict && <b className="ml-1 text-black">{VERDICT_LABEL[board.verdict]}</b>}
            </p>
          </div>

          {board === null ? (
            <div className="py-12 text-center text-[12px] text-pixel-muted animate-pulse">💬 글이 올라오고 있어요…</div>
          ) : (
            <div className="flex flex-col gap-2 max-h-[52vh] overflow-y-auto p-2.5 bg-slate-50">
              {board.posts.map((p, i) => <PostCard key={i} post={p} index={i} />)}
            </div>
          )}

          {board && (
            <p className="text-[11px] text-pixel-muted px-4 py-2 border-t border-black/10">
              군중 과열도 <b className="text-black">{delta > 0 ? `+${delta}` : delta}</b>
              {" · "}클론을 진정시키고 싶다면 📱 핸드폰의 피드 탭에서.
            </p>
          )}

          <div className="px-3 pb-3 flex justify-end">
            <PixelButton size="sm" disabled={board === null} onClick={onClose}>닫고 계속 ▶</PixelButton>
          </div>
        </div>
      </div>
    </div>
  );
}
