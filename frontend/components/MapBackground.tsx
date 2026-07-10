"use client";

import { useEffect, useImperativeHandle, useRef, forwardRef } from "react";

export interface MapBackgroundHandle {
  // 지도 iframe이 걷기 애니메이션을 마칠 때까지 기다린다(map.html이 끝나면
  // {type:"walked", band}를 postMessage로 보내줌). band를 주면 그 시간대
  // 구간만(T-237 §12.1b 동기화), 없으면 하루치 통재생(하위호환).
  playWalk: (band?: string, speedup?: number) => Promise<void>;
  // T-255/T-256 — 단방향 연출 신호(응답 없음): board_gather/board_release/trade_fx.
  signal: (payload: Record<string, unknown>) => void;
}

// T-FE2 — the_ville 배경 지도(§12.0). 백엔드의 순수 캔버스 페이지를 iframe으로
// 깔아 서비스 전체의 "배경"으로 쓴다. 상태는 전부 Next.js가 들고, 이 iframe은
// game_id로 GameRun에 연결해 그리기만 한다(하루 진행 시 postMessage로 걷기 트리거).
const MapBackground = forwardRef<MapBackgroundHandle, {
  gameId: string;
  // T-292 — 맵의 활동 서술(말풍선은 이모지만, 텍스트는 발자취 패널로).
  onActivity?: (text: string | null) => void;
  // 맵 브릿지 경로 종류. T-15 컷오버 후 유일 게임은 emo(감정 4축).
  game?: string;
  // true면 부모 컨테이너를 채움(PM식 장면 창), false면 뷰포트 고정 배경.
  contained?: boolean;
}>(function MapBackground(
  { gameId, onActivity, game = "emo", contained = false },
  ref
) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    if (!onActivity) return;
    const onMsg = (e: MessageEvent) => {
      if (e.data?.type === "activity") onActivity(e.data.text ?? null);
    };
    window.addEventListener("message", onMsg);
    return () => window.removeEventListener("message", onMsg);
  }, [onActivity]);

  useImperativeHandle(ref, () => ({
    playWalk: (band?: string, speedup?: number) =>
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
          if (e.data?.type === "walk-ack" || e.data?.type === "walk-tick") {
            // T-287 — 고정 상한이 아니라 **유휴 타임아웃**: 맵이 밴드 재생 중
            // 4초마다 walk-tick을 보내므로 살아있는 한 계속 기다린다(긴 걷기·
            // 만남 채팅). 신호가 30초 끊기면(죽은 iframe) 포기. 예전 고정 30초
            // 상한이 저녁 걷기 도중 만료돼 정산이 귀가 전에 뜨던 문제의 수정.
            clearTimeout(fallback);
            fallback = setTimeout(finish, band ? 30000 : 75000);
          } else if (e.data?.type === "walked" && (!band || e.data?.band === band)) {
            finish();
          }
        };
        window.addEventListener("message", onMessage);
        fallback = setTimeout(finish, 4000);
        iframeRef.current?.contentWindow?.postMessage({ type: "walk", band, speedup }, "*");
      }),
    signal: (payload: Record<string, unknown>) => {
      iframeRef.current?.contentWindow?.postMessage(payload, "*");
    },
  }));

  useEffect(() => {
    // iframe이 이미 떠 있으면 postMessage 없이 URL만 바뀌어도 재부팅됨(src 변경).
  }, [gameId]);

  return (
    <iframe
      ref={iframeRef}
      src={`/map.html?game_id=${encodeURIComponent(gameId)}&game=${encodeURIComponent(game)}`}
      title="Market Village 배경 지도"
      className={contained
        ? "absolute inset-0 w-full h-full border-0"
        : "fixed inset-0 w-full h-full border-0 z-0"}
    />
  );
});

export default MapBackground;
