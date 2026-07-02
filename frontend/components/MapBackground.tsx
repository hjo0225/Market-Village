"use client";

import { useEffect, useImperativeHandle, useRef, forwardRef } from "react";

export interface MapBackgroundHandle {
  // 지도 iframe이 걷기 애니메이션을 마칠 때까지 기다린다(map.html이 끝나면
  // {type:"walked", band}를 postMessage로 보내줌). band를 주면 그 시간대
  // 구간만(T-237 §12.1b 동기화), 없으면 하루치 통재생(하위호환).
  playWalk: (band?: string) => Promise<void>;
}

// T-FE2 — the_ville 배경 지도(§12.0). 백엔드의 순수 캔버스 페이지를 iframe으로
// 깔아 서비스 전체의 "배경"으로 쓴다. 상태는 전부 Next.js가 들고, 이 iframe은
// game_id로 GameRun에 연결해 그리기만 한다(하루 진행 시 postMessage로 걷기 트리거).
const MapBackground = forwardRef<MapBackgroundHandle, { gameId: string }>(function MapBackground(
  { gameId },
  ref
) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useImperativeHandle(ref, () => ({
    playWalk: (band?: string) =>
      new Promise<void>((resolve) => {
        // T-233 — 기존엔 4초 뒤 무조건 resolve라 걷기(~50초)를 실제로 안 기다렸다
        // (순간이동 체감의 원인 중 하나). 지도가 walk-ack로 살아있음을 알리면
        // 걷기 완료(walked)까지 제대로 기다리고, ack가 없으면(지도 미로딩·프록시
        // 플레이크) 4초 폴백으로 무한 대기를 막는다.
        let done = false;
        let fallback: ReturnType<typeof setTimeout>;
        const finish = () => {
          if (done) return;
          done = true;
          clearTimeout(fallback);
          window.removeEventListener("message", onMessage);
          resolve();
        };
        const onMessage = (e: MessageEvent) => {
          if (e.data?.type === "walk-ack") {
            clearTimeout(fallback);
            // T-237 — 밴드 재생은 한 구간(≤16초+여유), 통재생은 하루치 상한.
            fallback = setTimeout(finish, band ? 30000 : 75000);
          } else if (e.data?.type === "walked" && (!band || e.data?.band === band)) {
            finish();
          }
        };
        window.addEventListener("message", onMessage);
        fallback = setTimeout(finish, 4000);
        iframeRef.current?.contentWindow?.postMessage({ type: "walk", band }, "*");
      }),
  }));

  useEffect(() => {
    // iframe이 이미 떠 있으면 postMessage 없이 URL만 바뀌어도 재부팅됨(src 변경).
  }, [gameId]);

  return (
    <iframe
      ref={iframeRef}
      src={`/map?game_id=${encodeURIComponent(gameId)}`}
      title="Market Village 배경 지도"
      className="fixed inset-0 w-full h-full border-0 z-0"
    />
  );
});

export default MapBackground;
