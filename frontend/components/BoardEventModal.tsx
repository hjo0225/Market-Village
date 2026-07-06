"use client";

import { useState } from "react";
import Image from "next/image";
import PixelButton from "@/components/pixel/PixelButton";
import PhoneFrame from "@/components/PhoneFrame";
import { TONE_STYLE } from "@/components/NewsModal";
import { BoardFeed, BoardPost, NewsItem } from "@/lib/api";

// 게시판(SNS형 FGI) 이벤트 — PRD_SOCIAL_NPC_BOARD §3.0/§3.2 (D1·D3·D6).
// T-255(플레이테스트 리포트 ③) — 단순 모달이 아니라 **핸드폰이 올라오는** 연출:
// 마을이 걸음을 멈추고(❗, map board_gather 신호) 폰 프레임이 슬라이드업,
// 글이 트위터 피드처럼 순차 등장. 관찰 전용(개입은 핸드폰 피드 탭, D6).
// T-279(사용자 지시) — market_aquarium BoardFeed 구조 이식: 그날 NEWS 카드가
// 피드 최상단에 고정되고, 댓글은 카드에서 인라인 펼침(T-276 목록↔상세 2뷰 대체).
// 유저 글쓰기/투표는 이식하지 않음(관찰 전용 유지 — 사용자 결정).
export const CONTEXT_HEAD: Record<string, string> = {
  fear: "⚡ 마을이 공포에 술렁인다",
  greed: "🍾 마을이 축제 분위기다",
  fomo: "🔥 다들 어딘가로 몰려간다",
  unrest: "🌫 마을이 뒤숭숭하다",
};
// T-307(사용자 승인) — "여론 우세"는 다수 의견을 시장 힌트처럼 읽게 만든다(확증
// 편향 강화 — 게임 의도와 정반대). 방향 예측이 아니라 **쏠림의 세기 경고**로 프레임.
export const VERDICT_LABEL: Record<string, string> = {
  up: "🔥 온통 “오른다”는 말뿐 — 쏠릴수록 한 발 물러서서",
  down: "🧊 온통 “내린다”는 말뿐 — 쏠릴수록 한 발 물러서서",
  split: "⚖️ 의견이 반반 — 어느 쪽에 끌리는지 스스로를 지켜보자",
};

// T-260 — SNS 어포던스(좋아요·상대시각)는 표현 전용 결정론 파생값: 텍스트 해시
// 기반이라 서버 상태·랜덤 없음(하이드레이션 안전, 같은 글=같은 수치).
function seedNum(s: string, mod: number, salt = 0): number {
  let h = salt >>> 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return h % mod;
}
const STANCE_BADGE: Record<string, { label: string; cls: string }> = {
  up: { label: "📈 오른다", cls: "bg-emerald-100 text-emerald-700" },
  down: { label: "📉 내린다", cls: "bg-rose-100 text-rose-700" },
};

interface Props {
  day: number;
  board: BoardFeed | null;   // null = 아직 로딩("모여드는 중…")
  news?: NewsItem | null;    // T-279 — 그날 선택한 뉴스(피드 최상단 NEWS 카드)
  onClose: () => void;
}

function Stance({ stance }: { stance?: string | null }) {
  const b = stance ? STANCE_BADGE[stance] : undefined;
  if (!b) return null;
  return <span className={`text-[11px] font-bold rounded px-1 ${b.cls}`}>{b.label}</span>;
}

// T-279 — 그날 뉴스 카드(aquarium BoardFeed의 NEWS 카드 이식). 이전 날 뉴스
// 줄은 스냅샷에 headline이 없어(HistoryDay=news_id/tone만) 제외 — 오늘 1건만.
export function NewsCard({ news }: { news: NewsItem }) {
  const s = TONE_STYLE[news.tone] ?? TONE_STYLE.uncertain;
  // shrink-0 — 스크롤 flex 컬럼에서 카드가 눌려 내용이 잘리는 것 방지(PostCard 동일).
  return (
    <div className="shrink-0 rounded-xl border-2 border-black bg-white overflow-hidden shadow-pixel-sm">
      <div className="flex items-center gap-2 px-3 py-1.5 border-b-2 border-black">
        <span className="text-[11px] font-extrabold tracking-wide">📰 NEWS</span>
        <span className={`ml-auto text-[11px] font-bold rounded px-1.5 py-[1px] ${s.chip} ${s.text}`}>
          {s.icon} {s.label}
        </span>
      </div>
      <p className="px-3 py-2.5 text-sm font-bold leading-snug">{news.headline}</p>
    </div>
  );
}

// T-257 — PhoneModal 게시판 탭에서도 재사용(export).
// T-279 — 댓글 인라인 펼침(aquarium식): 기본 접힘, 💬을 누르면 그 자리에서 펼침.
export function PostCard({ post, index }: { post: BoardPost; index: number }) {
  const [open, setOpen] = useState(false);
  const isClone = post.author_kind === "clone";
  const nComments = post.comments.length;
  return (
    <div
      className={`shrink-0 rounded-xl border-2 p-3 bg-white shadow-pixel-sm animate-pixel-pop ${
        isClone ? "border-pixel-grass shadow-[0_0_0_2px_rgba(74,222,128,0.4)]" : "border-black"}`}
      style={{ animationDelay: `${index * 0.28}s`, animationFillMode: "backwards" }}
    >
      <div className="flex items-center gap-2 mb-1.5">
        {post.portrait ? (
          <Image
            src={`/assets/characters/profile/${post.portrait}.png`}
            alt={post.author} width={32} height={32}
            className="rounded-full border-2 border-black bg-pixel-grass/30"
            unoptimized
          />
        ) : (
          <span className="w-8 h-8 rounded-full border-2 border-black bg-pixel-grass/40 flex items-center justify-center text-[15px]">🤖</span>
        )}
        <div className="min-w-0">
          <div className="text-sm font-extrabold leading-tight flex items-center gap-1.5">
            {post.author}
            {isClone && <span className="text-[11px] font-bold text-pixel-grass-dark bg-pixel-grass/20 rounded px-1">내 클론</span>}
            <Stance stance={post.stance} />
          </div>
          {/* T-246 역할 부기 + T-260 결정론 시각 칩 */}
          <div className="text-[11px] text-pixel-muted leading-tight">
            {post.author_role ?? "오늘"} · {seedNum(post.text, 50, 7) + 2}분 전
          </div>
        </div>
      </div>
      <p className="text-sm leading-snug">{post.text}</p>

      {/* T-260 리액션 바 — 💬는 인라인 펼침 토글(T-279) */}
      <div className="mt-2 pt-1.5 border-t border-black/10 flex items-center gap-4 text-[12px] text-pixel-muted">
        <span>❤ {seedNum(post.text, 38, 1) + 3}</span>
        <button
          type="button"
          disabled={nComments === 0}
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-label={`댓글 ${nComments}개 ${open ? "접기" : "펼치기"}`}
          className={`flex items-center gap-1 ${
            nComments > 0 ? "font-bold text-black cursor-pointer" : ""}`}
        >
          💬 {nComments}
        </button>
        <span>🔁 {seedNum(post.text, 9, 5)}</span>
      </div>

      {open && nComments > 0 && (
        <div className="mt-2 pl-3 border-l-2 border-black/15 flex flex-col gap-1.5">
          {post.comments.map((c, i) => (
            <p key={i} className={`text-[13px] ${
              c.author_id === "clone" ? "bg-pixel-grass/15 rounded px-1 py-0.5" : "text-pixel-muted"}`}>
              <b className="text-black">{c.author}</b>{" "}
              {c.author_id === "clone" && c.author !== "내 클론" && (
                <span className="text-[11px] font-bold text-pixel-grass-dark">내 클론</span>
              )}{" "}
              <Stance stance={c.stance} /> {c.text}
              <span className="text-[11px] text-pixel-muted"> · ❤ {seedNum(c.text, 18, 3)}</span>
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

export default function BoardEventModal({ day, board, news, onClose }: Props) {
  return (
    <div role="dialog" aria-modal="true" className="fixed inset-0 z-[135] flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="absolute inset-0 bg-pixel-ink/70" />
      {/* T-255 폰 연출 · T-268 max-w-lg · T-288 프레임을 PhoneFrame으로 공용화 */}
      <PhoneFrame day={day}>
          <div className="px-4 py-2.5 border-b-2 border-black">
            <h2 className="text-base font-extrabold">💬 마을 게시판</h2>
            <p className="text-[13px] text-pixel-muted">
              {board ? CONTEXT_HEAD[board.context ?? ""] ?? "오늘 마을이 시끄럽다" : "다들 게시판에 모여드는 중…"}
              {board?.verdict && <b className="ml-1 text-black">{VERDICT_LABEL[board.verdict]}</b>}
            </p>
          </div>

          {board === null ? (
            <div className="py-12 text-center text-sm text-pixel-muted animate-pulse">💬 글이 올라오고 있어요…</div>
          ) : (
            /* T-279 — 단일 피드: 그날 NEWS 카드 + 게시글(댓글 인라인 펼침) */
            <div className="flex flex-col gap-2 max-h-[70vh] overflow-y-auto p-2.5 bg-slate-50">
              {news && <NewsCard news={news} />}
              {board.posts.map((p, i) => (
                <PostCard key={i} post={p} index={i} />
              ))}
            </div>
          )}

          <div className="px-3 pb-3 pt-2 flex justify-end">
            <PixelButton size="sm" disabled={board === null} onClick={onClose}>닫고 계속 ▶</PixelButton>
          </div>
      </PhoneFrame>
    </div>
  );
}
