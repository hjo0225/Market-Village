"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Board } from "@/lib/emoApi";
import AdvDialogue from "@/components/AdvDialogue";

// 게시판 여론 피드(왼쪽): "다음"마다 기존 글이 위로 밀리고 새 글이 아래에서 등장.
// 여론을 다 본 뒤에도(선택지 단계) 피드는 그대로 남는다 — 선택 완료 시 부모가 언마운트.
export default function BoardOpinionFeed({
  board, boardStep, onAdvance,
}: {
  board: Board;
  boardStep: number;
  onAdvance: () => void;
}) {
  const done = boardStep >= board.threads.length;
  return (
    <button
      type="button"
      onClick={done ? undefined : onAdvance}
      aria-label={done ? "게시판 여론" : "다음 여론 보기"}
      className={`absolute left-2 sm:left-3 inset-y-0 z-10 w-[min(24rem,85vw)] flex flex-col justify-center gap-2 text-left ${done ? "cursor-default" : "cursor-pointer"}`}
    >
      <AnimatePresence mode="popLayout" initial={false}>
        {board.threads.slice(0, boardStep + 1).map((th, idx) => {
          const isCurrent = idx === boardStep;
          return (
            <motion.div
              key={idx}
              layout
              className="relative"
              initial={{ opacity: 0, y: 48 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -48 }}
              transition={{ duration: 0.35, ease: "easeOut" }}
            >
              <AdvDialogue
                speakerId={th.author_id}
                title={`게시판 여론 · ${idx + 1}/${board.threads.length}`}
                text={th.text}
                tone="board"
              />
              {isCurrent && (
                <span className="absolute bottom-2 right-3 text-[12px] font-extrabold text-white/85 animate-pulse">
                  ▶ 클릭
                </span>
              )}
            </motion.div>
          );
        })}
      </AnimatePresence>
    </button>
  );
}
