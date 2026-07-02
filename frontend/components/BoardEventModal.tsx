"use client";

import Image from "next/image";
import PixelButton from "@/components/pixel/PixelButton";
import { BoardFeed, BoardPost } from "@/lib/api";

// 게시판(SNS형 FGI) 이벤트 모달 — PRD_SOCIAL_NPC_BOARD §3.0/§3.2 (D1·D3·D6).
// 이벤트 있는 날 하루진행 아침 단계에서만 뜨는 블로킹 관찰 이벤트 — 개입 버튼 없음
// (개입은 기존 핸드폰 피드 탭, D6). 닫아야 하루가 계속된다.
const CONTEXT_HEAD: Record<string, string> = {
  fear: "⚡ 마을이 공포에 술렁인다",
  greed: "🍾 마을이 축제 분위기다",
  fomo: "🔥 다들 어딘가로 몰려간다",
  unrest: "🌫 마을이 뒤숭숭하다",
};

interface Props {
  day: number;
  board: BoardFeed | null;   // null = 아직 로딩("모여드는 중…")
  onClose: () => void;
}

function PostCard({ post }: { post: BoardPost }) {
  const isClone = post.author_kind === "clone";
  return (
    <div className={`rounded-xl border-2 p-3 bg-white ${
      isClone ? "border-pixel-grass shadow-[0_0_0_2px_rgba(74,222,128,0.4)]" : "border-black"}`}>
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
        {isClone && <span className="text-[10px] font-bold text-pixel-grass-dark bg-pixel-grass/20 rounded px-1">내 클론</span>}
      </div>
      <p className="text-[12px] leading-snug">{post.text}</p>
      {post.comments.length > 0 && (
        <div className="mt-2 pl-3 border-l-2 border-black/20 flex flex-col gap-1">
          {post.comments.map((c, i) => (
            <p key={i} className="text-[11px] text-pixel-muted">
              <b className="text-black">{c.author}</b> {c.text}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

export default function BoardEventModal({ day, board, onClose }: Props) {
  return (
    <div role="dialog" aria-modal="true" className="fixed inset-0 z-[135] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-pixel-ink/70" />
      <div className="relative w-full max-w-md bg-white border-2 border-black rounded-2xl shadow-pixel-md p-4 animate-pixel-pop">
        <h2 className="text-sm font-extrabold mb-0.5">📱 마을 게시판 — Day {day}</h2>
        <p className="text-[11px] text-pixel-muted mb-3">
          {board ? CONTEXT_HEAD[board.context ?? ""] ?? "오늘 마을이 시끄럽다" : "다들 게시판에 모여드는 중…"}
        </p>

        {board === null ? (
          <div className="py-10 text-center text-[12px] text-pixel-muted animate-pulse">💬 글이 올라오고 있어요…</div>
        ) : (
          <div className="flex flex-col gap-2 max-h-[46vh] overflow-y-auto pr-1">
            {board.posts.map((p, i) => <PostCard key={i} post={p} />)}
          </div>
        )}

        {board && (
          <p className="text-[11px] text-pixel-muted mt-3">
            군중 과열도 <b className="text-black">+{Math.round(board.crowd_mood_delta)}</b>
            {" · "}클론을 진정시키고 싶다면 📱 핸드폰의 피드 탭에서.
          </p>
        )}

        <div className="mt-3 flex justify-end">
          <PixelButton size="sm" disabled={board === null} onClick={onClose}>닫고 계속 ▶</PixelButton>
        </div>
      </div>
    </div>
  );
}
