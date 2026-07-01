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
