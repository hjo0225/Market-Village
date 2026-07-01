"use client";

import React, { useEffect } from "react";
import { X } from "lucide-react";

const SIZE: Record<string, string> = {
  sm: "w-[400px]",
  md: "w-[600px]",
  lg: "w-[850px]",
};

interface Props {
  isOpen: boolean;
  title?: string;
  onClose: () => void;
  size?: "sm" | "md" | "lg";
  children: React.ReactNode;
  footer?: React.ReactNode;
  headerIcon?: React.ReactNode;
}

export default function PixelModal({
  isOpen,
  title = "",
  onClose,
  size = "md",
  children,
  footer,
  headerIcon,
}: Props) {
  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div role="dialog" aria-modal="true" className="fixed inset-0 z-[120] flex items-center justify-center">
      <div className="absolute inset-0 bg-pixel-ink/60" onClick={onClose} />
      <div
        className={`relative ${SIZE[size]} max-w-[92vw] max-h-[88vh] flex flex-col border-2 border-black rounded-2xl shadow-pixel-lg bg-white animate-pixel-pop overflow-hidden`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 px-4 py-2.5 bg-pixel-table border-b-2 border-black flex-shrink-0">
          {headerIcon}
          <span className="text-[14px] font-bold text-black truncate">{title}</span>
          <div className="flex-1" />
          <button
            onClick={onClose}
            aria-label="닫기"
            className="w-6 h-6 flex items-center justify-center border-2 border-black rounded-lg bg-pixel-wall text-black cursor-pointer hover:bg-pixel-danger hover:text-white active:translate-x-[1px] active:translate-y-[1px]"
          >
            <X size={13} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-5 min-h-[120px] bg-white">{children}</div>
        {footer && (
          <div className="flex items-center gap-2 px-4 py-3 bg-pixel-wall border-t-2 border-black flex-shrink-0">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
