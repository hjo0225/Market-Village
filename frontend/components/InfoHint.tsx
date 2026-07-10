"use client";

import { useEffect, useRef, useState } from "react";
import { Info } from "lucide-react";

// 코인을 모르는 사용자를 위한 친절 설명. shadcn Popover를 참고한 앵커드 팝오버
// (모달 아님): 정보 아이콘을 누르면 아이콘 아래에 설명 카드가 뜨고, 바깥 클릭·ESC로
// 닫힌다. 외부 라이브러리 없이 상태·이벤트로만.
export default function InfoHint({ title, text }: { title?: string; text: string }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLSpanElement | null>(null);

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

  return (
    <span ref={rootRef} className="relative inline-flex items-center align-middle">
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); setOpen((o) => !o); }}
        aria-expanded={open}
        aria-label={title ? `${title} 설명` : "설명"}
        className="text-black/35 hover:text-black/70 p-0 m-0 bg-transparent border-0"
      >
        <Info className="h-3.5 w-3.5" />
      </button>

      {open && (
        // PopoverContent 상당: 트리거 아래 중앙 정렬, 화면 밖으로 안 나가게 max-w 제한.
        <span
          role="dialog"
          className="absolute z-50 left-1/2 top-full mt-1.5 -translate-x-1/2 w-60 max-w-[72vw]
            rounded-lg border-2 border-black bg-white text-black shadow-pixel-md p-3
            text-left normal-case"
          onClick={(e) => e.stopPropagation()}
        >
          {title && <span className="block text-[12px] font-extrabold mb-1">{title}</span>}
          <span className="block text-[11px] leading-relaxed font-medium">{text}</span>
        </span>
      )}
    </span>
  );
}
