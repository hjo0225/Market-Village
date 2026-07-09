"use client";

import { useEffect, useRef, useState } from "react";
import { GLOSSARY, WrappedSegment, wrapTerms } from "@/lib/glossary";

// §2 — 용어 설명 인라인 컴포넌트. 데스크톱은 hover 시 툴팁, 모바일은 탭 시 팝오버
// (외부 탭에서 닫힘). 외부 라이브러리 금지 — 순수 상태 + 이벤트로만 구현.

function TermPopover({ term }: { term: string }) {
  const entry = GLOSSARY[term];
  if (!entry) return null;
  return (
    <span
      role="tooltip"
      className="absolute z-50 left-1/2 -translate-x-1/2 bottom-full mb-1.5 w-56 max-w-[70vw]
        rounded-lg border-2 border-black bg-white text-black shadow-pixel-md p-2.5
        text-left pointer-events-none"
    >
      <span className="block text-[12px] font-extrabold mb-1">{term}</span>
      <span className="block text-[11px] leading-relaxed mb-1">{entry.short}</span>
      <span className="block text-[11px] leading-relaxed text-pixel-muted">{entry.effect}</span>
    </span>
  );
}

export default function Term({ term, children }: { term: string; children?: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLSpanElement | null>(null);
  const entry = GLOSSARY[term];

  // 모바일 탭 팝오버 — 바깥 탭에서 닫힘.
  useEffect(() => {
    if (!open) return;
    const onOutside = (e: MouseEvent | TouchEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onOutside);
    document.addEventListener("touchstart", onOutside);
    return () => {
      document.removeEventListener("mousedown", onOutside);
      document.removeEventListener("touchstart", onOutside);
    };
  }, [open]);

  if (!entry) return <>{children ?? term}</>;

  return (
    <span
      ref={rootRef}
      className="relative inline-block group"
    >
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); setOpen((o) => !o); }}
        className="underline decoration-dotted decoration-2 underline-offset-2 decoration-black/40
          font-inherit text-inherit bg-transparent border-0 p-0 m-0 cursor-help align-baseline"
        aria-label={`${term} 뜻 보기`}
      >
        {children ?? term}
      </button>
      {/* 데스크톱: hover 시 표시(group-hover). 모바일: 탭 상태(open)로 표시. */}
      <span className="hidden sm:group-hover:block">
        <TermPopover term={term} />
      </span>
      {open && (
        <span className="sm:hidden block">
          <TermPopover term={term} />
        </span>
      )}
    </span>
  );
}

// wrapTerms(text) 결과를 실제 <Term> 노드 배열로 렌더. 데이터 문자열(선택지 라벨 등)에
// 사전 키가 있으면 첫 등장만(최대 2개) 감싼다.
export function TermText({ text, maxTerms = 2 }: { text: string; maxTerms?: number }) {
  const segments: WrappedSegment[] = wrapTerms(text, maxTerms);
  if (segments.length === 1 && segments[0].term === null) return <>{text}</>;
  return (
    <>
      {segments.map((seg, i) =>
        seg.term ? <Term key={i} term={seg.term}>{seg.text}</Term> : <span key={i}>{seg.text}</span>
      )}
    </>
  );
}
