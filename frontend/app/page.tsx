import { redirect } from "next/navigation";

// 루트 진입점 = 신 감정게임(/emo). 레거시 /play 흐름(setup·play·report·history·compare)은
// 은퇴(2026-07-08, 사용자 결정). 백엔드 인프라(personas·fate_line·_banded_route 등)는
// /emo 맵 브릿지가 재사용하므로 유지 — 프론트 레거시 '페이지'만 제거한다.
export default function Home() {
  redirect("/emo");
}
