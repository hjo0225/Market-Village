# Market Village — 사용 규칙

**정체**: 코인 투자 라이프심 게임의 픽셀-카드 UI. 흰 베이스 + 잉크(#161616) 흑백 카드, 그린/옐로는 액센트 전용. 본문 폰트 Pretendard Variable — `styles.css`가 로드하므로 별도 설정 불요.

## 셋업 / 래핑
- **Provider 불필요.** 모든 컴포넌트는 독립 렌더 — 그대로 import해서 쓴다.
- **오버레이 컴포넌트**(`DayReport`, `StoryScene` 등 화면 전체를 덮는 계열)는 `position: relative`이고 명시적 높이가 있는 컨테이너 안에 넣어야 보인다. 예: `<div style={{position:"relative", height:560}}>`.
- 화면 기본 배경은 흰색. 다크 오버레이 위 카드 패턴은 컴포넌트가 스스로 그린다.

## 스타일링 계약 (가장 중요)
스타일시트는 **Tailwind 컴파일 서브셋**이다 — 이 앱이 실제 쓴 클래스만 존재하고, 임의의 Tailwind 유틸리티(`bg-pink-300` 등)는 대부분 **없다**. 규칙:

1. 컴포넌트가 UI의 주역이다 — 자체 스타일 완비. 레이아웃 글루(배치·간격·폭)는 **인라인 스타일**을 우선한다.
2. 아래 검증된 클래스 어휘는 자유롭게 쓴다:
   - 픽셀 마크: `pixel-border`(2px 잉크 보더) · `pixel-shadow` / `pixel-shadow-sm` / `pixel-shadow-lg`(하드 오프셋 섀도) · `shadow-pixel-sm` / `shadow-pixel-md`
   - 색: `bg-pixel-grass`(액션 그린) · `bg-pixel-danger`(경고 브라운, 흰 글자와 함께) · `text-pixel-muted`(보조 라벨) · `text-green-600`(긍정 강조) · `bg-green-500` · `bg-yellow-300`
   - 시세 방향(국내 관행): 상승/이익 = `text-rose-600`, 하락/손실 = `text-sky-600`, 중립 = `text-pixel-muted`
   - 모션: `animate-fade-in` · `animate-slide-up` · `animate-pixel-pop` · `animate-bump` · `animate-pulse-soft` · `animate-card-reveal` · `animate-bar-indeterminate`
   - 긴 글 블록: `report-markdown`(제목·리스트·인용 타이포 일괄 적용) · 숫자 열 정렬: `tabular-nums`
3. 목록에 없는 클래스를 쓰고 싶으면 먼저 `_ds_bundle.css`에서 존재를 확인하고, 없으면 인라인 스타일로 쓴다.

## 진실의 위치
- 전체 CSS(존재하는 클래스의 원전): `_ds_bundle.css` (진입점 `styles.css`), 폰트: `fonts/fonts.css`
- 컴포넌트 API 계약: `components/<group>/<Name>/<Name>.d.ts` · 사용 예: 같은 폴더 `<Name>.prompt.md`

## 관용 조합 예 (검증된 렌더에서 발췌)
```tsx
import { PixelPanel, PixelButton, TierBadge } from "market-village-frontend";

<div style={{ maxWidth: 420, display: "flex", flexDirection: "column", gap: 12 }}>
  <PixelPanel tone="cloud" className="p-6">
    <div className="text-[11px] text-pixel-muted">Day 7 · 정산</div>
    <h2 className="text-lg font-extrabold">오늘 하루</h2>
    <TierBadge tier={{ name: "평정 수련", icon: "🧘", score: 63, next_at: 72 }} />
    <PixelButton size="lg" className="w-full">다음 날 →</PixelButton>
  </PixelPanel>
</div>
```

도메인 어휘: 감정 축 = 공포·탐욕·불안·조급·평정(각 0–100, `{fear, greed, anxiety, restlessness, composure}`), 자산 카테고리 = 대형 안정형(`large_stable`)·중견 알트형(`mid_alt`)·밈형(`meme`)·스테이블(`stable`)·현금(`cash`).
