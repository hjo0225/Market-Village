"use client";

import { useEffect, useImperativeHandle, useRef, forwardRef } from "react";

export interface MapBackgroundHandle {
  // 지도 iframe이 오늘 걷기 애니메이션을 다 마칠 때까지 기다린다(map.html이
  // 끝나면 {type:"walked"}를 postMessage로 보내줌) — 호출부가 이걸 기다렸다가
  // 결과를 보여주면 "하루가 순간이동하지 않고 천천히 흐르는" 느낌이 난다.
  playWalk: () => Promise<void>;
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
    playWalk: () =>
      new Promise<void>((resolve) => {
        const onMessage = (e: MessageEvent) => {
          if (e.data?.type === "walked") {
            window.removeEventListener("message", onMessage);
            resolve();
          }
        };
        window.addEventListener("message", onMessage);
        // 지도가 못 뜨거나 응답이 없어도(Windows 프록시 플레이크) 무한정 안
        // 막히게 안전장치를 둔다.
        setTimeout(() => {
          window.removeEventListener("message", onMessage);
          resolve();
        }, 4000);
        iframeRef.current?.contentWindow?.postMessage({ type: "walk" }, "*");
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
