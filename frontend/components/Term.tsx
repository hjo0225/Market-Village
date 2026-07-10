"use client";

import { useEffect, useRef, useState } from "react";
import { GLOSSARY, WrappedSegment, wrapTerms } from "@/lib/glossary";

// §2 — 용어 설명 인라인 컴포넌트. InfoHint와 같은 앵커드 팝오버(모달 아님):
// 클릭/탭으로 토글, 바깥 클릭·ESC로 닫힘. 외부 라이브러리 금지 — 순수 상태 + 이벤트로만 구현.

export default function Term({ term, children }: { term: string; children?: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLSpanElement | null>(null);
  const entry = GLOSSARY[term];

  useEffect(() => {
    if (!open) return;
    const onOutside = (e: MouseEvent | TouchEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onOutside);
    document.addEventListener("touchstart", onOutside);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onOutside);
      document.removeEventListener("touchstart", onOutside);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  if (!entry) return <>{children ?? term}</>;

  return (
    <span ref={rootRef} className="relative inline-block">
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); setOpen((o) => !o); }}
        aria-expanded={open}
        className="underline decoration-dotted decoration-2 underline-offset-2 decoration-black/40
          font-inherit text-inherit bg-transparent border-0 p-0 m-0 align-baseline"
        aria-label={`${term} 뜻 보기`}
      >
        {children ?? term}
      </button>
      {open && (
        <span
          role="dialog"
          className="absolute z-50 left-1/2 top-full mt-1.5 -translate-x-1/2 w-60 max-w-[72vw]
            rounded-lg border-2 border-black bg-white/100 text-black shadow-pixel-md p-3
            text-left normal-case"
          onClick={(e) => e.stopPropagation()}
        >
          <span className="block text-[12px] font-extrabold mb-1">{term}</span>
          <span className="block text-[11px] leading-relaxed font-medium mb-1">{entry.short}</span>
          <span className="block text-[11px] leading-relaxed text-pixel-muted">{entry.effect}</span>
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
