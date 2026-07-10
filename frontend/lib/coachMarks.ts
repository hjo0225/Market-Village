// v3 §D2 — 코치마크(1회성 설명) 표시 여부 관리. localStorage 키 mv_coach_v1에
// 이미 본 마크 id 배열을 저장. SSR 환경(localStorage 없음) 대비 가드.
export type CoachMarkId = "emotionStrip" | "walking" | "firstBoard" | "tickerBar";

const STORAGE_KEY = "mv_coach_v1";

function readSeen(): CoachMarkId[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function hasSeenCoachMark(id: CoachMarkId): boolean {
  return readSeen().includes(id);
}

export function markCoachMarkSeen(id: CoachMarkId): void {
  if (typeof window === "undefined") return;
  try {
    const seen = readSeen();
    if (!seen.includes(id)) {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify([...seen, id]));
    }
  } catch {
    /* localStorage 접근 불가(프라이빗 모드 등) — 조용히 무시, 매번 다시 뜰 뿐 */
  }
}
