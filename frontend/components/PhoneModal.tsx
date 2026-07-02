"use client";

import { useState } from "react";
import { X } from "lucide-react";
import PixelButton from "@/components/pixel/PixelButton";
import { api, NPC_LABELS } from "@/lib/api";

const FGI_TONES = [
  { value: "calm", label: "휩쓸리지 마" },
  { value: "clarify", label: "사실 차분히 짚기" },
  { value: "fear_join", label: "같이 무서워하기" },
];

// §9.5.3 매매 에이전트 8종(T-221) — 표시명은 api.ts NPC_LABELS 단일 소스에서.
// 역할 태그(도움/자극)만 이 화면 전용. 순서 = 도움 4 → 자극 4.
const NPC_ROLES: [string, string][] = [
  ["value_investor", "도움·차분"], ["quant_trader", "도움·냉정"],
  ["macro_whale", "도움·대범"], ["contrarian", "도움·독립"],
  ["panic_ant", "자극·공포"], ["fomo_scalper", "자극·추격"],
  ["conspiracy_influencer", "자극·루머"], ["jackpot_gambler", "자극·탐욕"],
];
const NPCS = NPC_ROLES.map(([value, role]) => (
  { value, label: `${NPC_LABELS[value] ?? value} (${role})` }));

interface Props {
  isOpen: boolean;
  onClose: () => void;
  gameId: string;
  rapport: number;
  crowdMood: number;
  onChanged: () => void;
}

// DESIGN.md §2 "진짜 휴대폰" — 검정 베젤+노치+상태바+흰 화면+홈 인디케이터(§9.1b 핸드폰).
export default function PhoneModal({ isOpen, onClose, gameId, rapport, crowdMood, onChanged }: Props) {
  const [tab, setTab] = useState<"feed" | "dm">("feed");
  const [fgiTone, setFgiTone] = useState("calm");
  const [fgiResult, setFgiResult] = useState("");
  const [npc, setNpc] = useState(NPCS[0].value);
  const [dmResult, setDmResult] = useState("");
  const [busy, setBusy] = useState(false);

  if (!isOpen) return null;

  async function doFgi() {
    setBusy(true);
    // roll은 매번 진짜 난수여야 한다 — 고정값을 쓰면 결과가 항상 같아진다
    // (버그: 이전엔 roll=50 고정이라 초기 래포50/성공률50%에서 1:1이 항상
    // 실패했다. 사용자 피드백 2026-07-01 "1:1대화·FGI가 제대로 진행이 안돼").
    const r = await api.fgi(gameId, fgiTone, Math.random() * 100);
    setFgiResult(r.absorbed ? "🌊 묻힘(군중 과열)" : `📣 과열도 ${Math.round(r.crowd_mood)}로 이동`);
    setBusy(false); onChanged();
  }

  async function doPersuade(direction: "calm" | "escalate") {
    setBusy(true);
    const r = await api.persuade(gameId, npc, direction, Math.random() * 100);
    setDmResult(r.accepted
      ? `✅ 먹힘 (성공률 ${Math.round(r.success_prob)}%) · 래포 ${Math.round(r.rapport)}`
      : `❌ 씹힘 (성공률 ${Math.round(r.success_prob)}%) · 래포 ${Math.round(r.rapport)}`);
    setBusy(false); onChanged();
  }

  return (
    <div role="dialog" aria-modal="true" className="fixed inset-0 z-[130] flex items-center justify-center">
      <div className="absolute inset-0 bg-pixel-ink/60" onClick={onClose} />
      <div className="relative w-[300px] bg-pixel-ink rounded-[36px] p-3 shadow-phone border-2 border-black animate-pixel-pop">
        {/* 다이내믹 아일랜드 */}
        <div className="absolute left-1/2 -translate-x-1/2 top-4 w-20 h-5 bg-black rounded-full z-10" />
        <button
          onClick={onClose}
          aria-label="닫기"
          className="absolute -right-3 -top-3 w-7 h-7 rounded-full bg-white border-2 border-black flex items-center justify-center"
        >
          <X size={13} />
        </button>
        {/* 화면 */}
        <div className="bg-white rounded-[26px] overflow-hidden border-2 border-black min-h-[420px] flex flex-col">
          {/* 상태바 */}
          <div className="flex items-center justify-between px-4 pt-6 pb-1 text-[10px] font-bold text-black">
            <span>9:41</span>
            <span>📶 🔋</span>
          </div>
          {/* 탭 */}
          <div className="flex border-b-2 border-black">
            <button
              className={`flex-1 py-2 text-[12px] font-bold ${tab === "feed" ? "bg-pixel-grass" : "bg-white"}`}
              onClick={() => setTab("feed")}
            >💬 피드</button>
            <button
              className={`flex-1 py-2 text-[12px] font-bold border-l-2 border-black ${tab === "dm" ? "bg-pixel-grass" : "bg-white"}`}
              onClick={() => setTab("dm")}
            >📱 1:1</button>
          </div>

          <div className="flex-1 p-3 flex flex-col gap-3">
            {tab === "feed" ? (
              <>
                <div className="text-[11px] text-pixel-muted">FGI 단톡방 · 과열도 <b>{Math.round(crowdMood)}</b> (래포 무관, 약함)</div>
                <select className="border-2 border-black rounded-lg px-2 py-1.5 text-[12px]" value={fgiTone} onChange={(e) => setFgiTone(e.target.value)}>
                  {FGI_TONES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
                <PixelButton size="sm" disabled={busy} onClick={doFgi}>글 올리기</PixelButton>
                {fgiResult && <div className="text-[11px] font-bold animate-fade-in">{fgiResult}</div>}
              </>
            ) : (
              <>
                <div className="text-[11px] text-pixel-muted">1:1 대화 · 래포 <b>{Math.round(rapport)}</b> (위기개입과 같은 풀)</div>
                <select className="border-2 border-black rounded-lg px-2 py-1.5 text-[12px]" value={npc} onChange={(e) => setNpc(e.target.value)}>
                  {NPCS.map((n) => <option key={n.value} value={n.value}>{n.label}</option>)}
                </select>
                <div className="flex gap-2">
                  <PixelButton size="sm" disabled={busy} onClick={() => doPersuade("calm")}>안정으로</PixelButton>
                  <PixelButton size="sm" variant="secondary" disabled={busy} onClick={() => doPersuade("escalate")}>격화로</PixelButton>
                </div>
                {dmResult && <div className="text-[11px] font-bold animate-fade-in">{dmResult}</div>}
              </>
            )}
          </div>
          {/* 홈 인디케이터 */}
          <div className="flex justify-center pb-2">
            <div className="w-24 h-1 bg-black/70 rounded-full" />
          </div>
        </div>
      </div>
    </div>
  );
}
