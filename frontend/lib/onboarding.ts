// 온보딩 오버레이를 이미 봤는지 기억 — 재방문 시 다시 안 뜬다(T-SVC4).
const KEY = "mv_onboarding_seen";

export function hasSeenOnboarding(): boolean {
  if (typeof window === "undefined") return true;
  return window.localStorage.getItem(KEY) === "1";
}

export function markOnboardingSeen() {
  window.localStorage.setItem(KEY, "1");
}
