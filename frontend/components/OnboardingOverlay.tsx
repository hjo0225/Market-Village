"use client";

import { useEffect, useState } from "react";
import PixelModal from "@/components/pixel/PixelModal";
import PixelButton from "@/components/pixel/PixelButton";
import { hasSeenOnboarding, markOnboardingSeen } from "@/lib/onboarding";

const TRAPS = [
  { name: "급락 패닉", desc: "폭락에 겁먹고 던진다" },
  { name: "멘탈 마모", desc: "잔손절이 쌓여 지친다" },
  { name: "익절 거부", desc: "더 오를까봐 못 판다" },
  { name: "과대 베팅", desc: "자신감에 몰빵한다" },
  { name: "추격 매수", desc: "급등에 뒤늦게 산다" },
  { name: "막차 불안", desc: "다들 사니까 따라 산다" },
];

export default function OnboardingOverlay() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!hasSeenOnboarding()) setOpen(true);
  }, []);

  function close() {
    markOnboardingSeen();
    setOpen(false);
  }

  return (
    <PixelModal isOpen={open} onClose={close} title="🪞 처음이신가요?" size="md">
      <div className="flex flex-col gap-4 text-sm">
        <p>
          블라인드 처리된 <b>실제 과거 코인 시장</b>에서 내 투자 성격을 복제한
          <b> 거울 클론</b>이 10일을 삽니다. 당신은 클론을 직접 조종하지 않고,
          뉴스·전날밤 회피·위기 개입으로만 클론의 감정을 흔들어요.
        </p>
        <div>
          <p className="font-bold mb-2">클론이 빠질 수 있는 6가지 함정</p>
          <div className="grid grid-cols-2 gap-2">
            {TRAPS.map((t) => (
              <div key={t.name} className="border-2 border-black rounded-lg px-2 py-1.5 bg-pixel-path">
                <div className="font-bold text-xs">{t.name}</div>
                <div className="text-[11px] text-pixel-muted">{t.desc}</div>
              </div>
            ))}
          </div>
        </div>
        <div>
          <p className="font-bold mb-2">플레이 화면 조작법</p>
          <ul className="text-xs text-pixel-muted flex flex-col gap-1">
            <li>📊 상태 — 클론의 감정·스탯 확인</li>
            <li>📰 뉴스 — 아침마다 뜨는 뉴스 3지선다</li>
            <li>🌙 전날밤 — 클론의 다음 날 일과를 살짝 회피시키기</li>
            <li>📱 핸드폰 — 클론과 1:1 대화, SNS 분위기 개입</li>
            <li>하루 진행 ▶ — 하루를 흘려보내기. 위기가 실제로 터지면 그 순간 개입(A/B/C) 선택 팝업이 뜬다</li>
          </ul>
        </div>
        <p className="text-xs text-pixel-muted">
          10일 뒤 결과 카드로 클론의 투자 성향을 확인하고, 다시 플레이하며 내
          감정 패턴이 달라졌는지 비교할 수 있어요.
        </p>
        <PixelButton size="lg" onClick={close} className="self-end">
          시작하기
        </PixelButton>
      </div>
    </PixelModal>
  );
}
