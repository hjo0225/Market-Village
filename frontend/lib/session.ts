// game_id를 localStorage에 보관해 라우트 이동 간(설정→플레이→리포트) 세션을 유지한다.
const KEY = "mv_game_id";

export function getGameId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(KEY);
}

export function setGameId(id: string) {
  window.localStorage.setItem(KEY, id);
}

export function clearGameId() {
  window.localStorage.removeItem(KEY);
}

export function newGameId(): string {
  return "web-" + Date.now().toString(36) + "-" + Math.floor(Math.random() * 1e6).toString(36);
}

// T-231 — 인터뷰 "확정" 산출물. /setup에서 확정 후 저장 → /setup/portfolio가 소비.
// 라우트가 분리돼도(새로고침 포함) 답변이 유실되지 않게 localStorage에 둔다.
const SETUP_KEY = "mv_setup_answers";

export function setSetupAnswers(answers: Record<string, number>) {
  window.localStorage.setItem(SETUP_KEY, JSON.stringify(answers));
}

export function getSetupAnswers(): Record<string, number> | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(SETUP_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : null;
  } catch {
    return null;
  }
}

export function clearSetupAnswers() {
  window.localStorage.removeItem(SETUP_KEY);
}
