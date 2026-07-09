"use client";

import { useEffect, useState } from "react";
import PixelPanel from "@/components/pixel/PixelPanel";
import PixelButton from "@/components/pixel/PixelButton";
import { CoachMarkId, hasSeenCoachMark, markCoachMarkSeen } from "@/lib/coachMarks";

// v3 §D2 — 작은 말풍선 코치마크. 각 id는 localStorage(mv_coach_v1)에 1회만 기록,
// 이후 재방문 시 다시 뜨지 않는다. PixelPanel 재사용, "알겠어" 버튼으로 닫음.
export default function CoachMark({
  id, text, className = "",
}: { id: CoachMarkId; text: string; className?: string }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!hasSeenCoachMark(id)) setVisible(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (!visible) return null;

  const dismiss = () => {
    markCoachMarkSeen(id);
    setVisible(false);
  };

  return (
    <div className={`z-40 ${className}`}>
      <PixelPanel tone="cloud" className="max-w-[240px] p-3 shadow-pixel-md">
        <p className="text-[12px] leading-relaxed">{text}</p>
        <div className="mt-2 flex justify-end">
          <PixelButton size="sm" onClick={dismiss}>알겠어</PixelButton>
        </div>
      </PixelPanel>
    </div>
  );
}
