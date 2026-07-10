# design-sync NOTES — Market Village

## 저장소 특성
- 이 저장소는 디자인 시스템 패키지가 아니라 **Next.js 게임 앱**(`frontend/`). 컴포넌트는 `frontend/components/**` (30 파일 + Term.tsx의 named export `TermText` = 31 컴포넌트).
- 컴포넌트가 거의 전부 **default export** → 변환기의 synth-entry(`export *`)로는 번들 글로벌에 안 실린다. 해결: `.design-sync/gen-entry.mjs`가 `frontend/.ds-entry.ts`(named 재수출 엔트리)를 생성, `cfg.entry`로 공급.
- `.d.ts` 트리가 없음 → `frontend/tsconfig.dssync.json`으로 `tsc --emitDeclarationOnly` 실행해 `frontend/.ds-types/` 생성. `frontend/package.json`에 `"types": ".ds-types/.ds-entry.d.ts"` 필드 추가(앱 동작 무영향)가 이 트리를 변환기에 노출하는 배선.
- 스타일은 Tailwind(JIT) — 컴파일된 CSS가 없으므로 `.design-sync/tailwind.sync.config.js`(앱 테마 재사용 + `.design-sync/previews/` content 포함)로 `frontend/.ds-tailwind.css` 생성 → `cfg.cssEntry`.
- 위 세 산출물은 전부 gitignore — **`cfg.buildCmd`(`node .design-sync/build-ds.mjs`)가 매 sync 전에 재생성**한다.
- `cfg.srcDir: "components"` 필수 — 기본 휴리스틱(src|lib|components 순)이 `frontend/lib/`(유틸 디렉터리)를 먼저 집는다.
- 새 컴포넌트 추가 시: gen-entry가 자동 포착(default export + PascalCase 파일명 규칙만 지키면 config 수정 불요).

## 설치/환경
- 의존성 설치: `frontend/package-lock.json` → `npm ci`가 정석이나, 첫 sync 시점에 dev 서버(next.pid)가 떠 있을 수 있어 node_modules 삭제가 위험 → react/react-dom/@types/react 존재 확인으로 대체함 (프로세스 우회 1건, 사유: 라이브 dev 서버 보호).
- 렌더 체크: playwright는 `.ds-sync/`에 **1.58.2** 고정 설치 — 캐시된 chromium-1208과 매칭 (버전 올리면 브라우저 재다운로드 ~200MB).
- 백엔드 파이썬과 무관 (프론트 전용 sync).

## 프리뷰 작성 노하우 (wave1 병합)
- **package-capture/validate는 로컬 소켓 listen 필요** — 샌드박스 셸에서 `listen EFAULT`로 즉사할 수 있고, 일반 셸에서도 간헐 발생(환경 플레이크). 격리 재실행으로 해결 — 회귀로 단정하지 말 것.
- **팝오버류(Term/InfoHint) 열린 상태 박제**: 캡처가 networkidle까지 기다리므로 useEffect에서 트리거를 click()하는 AutoOpen 래퍼로 열린 팝오버가 찍힌다. 셀에 `position:relative` + height(~150-190px) + 좌측 여백 필요.
- **주석만 고쳐도 srcSha가 바뀌어 전체 재캡처** — 렌더 무영향 편집은 grade 전에 몰아서.
- **AdvDialogue 초상 404 회피**: `speakerId` 대신 `speakerName`만 주면 이니셜 폴백이 결정론적으로 렌더.
- **TickerBar는 빈 ticker면 null 렌더** — empty 변형 불가. **TradeFlashBadge**는 pulse가 opacity 1 시작이라 t=0 정적 캡처 가능.
- **EmotionStrip 배경 투명** — 앱 헤더 톤(#fdf6e3) 래퍼를 깔 것.
- **min-h-screen 컴포넌트(DiagnosisCard)는 그대로 렌더 안전** (셀이 커질 뿐).
- **토큰 사실**: pixel.wall == pixel.cloud == #FFFFFF (의도), pixel.path = #F2F4F7.
- **리얼 데이터 소스**: 티어 backend/sim/tier.py · 티커 심볼 backend/sim/coins.py(BTC/XRP/DOGE/USDT) · verdict "과열/위축/중립" · 진단 테이블 backend/sim/disposition.py · 감정 축/카테고리 frontend/lib/emoApi.ts.

## Re-sync risks (다음 실행이 지켜볼 것)
- **`.design-sync/fonts/pretendard/PretendardVariable.woff2`(2MB)가 커밋 안 되면** fresh clone에서 `extraFonts` 스킵 → [FONT_MISSING] 재발. durable 세트에 포함해 커밋할 것 (OFL 라이선스, pretendard.css에 표기).
- **conventions.md의 클래스 목록은 컴파일된 Tailwind 서브셋에 종속** — 앱 코드가 어떤 클래스를 더 이상 안 쓰면 CSS에서 조용히 사라진다. re-sync의 컨벤션 검증 단계에서 grep 재확인 필수.
- **`.ds-sync/` 재설치 시**: `npm i esbuild ts-morph @types/react typescript@5 playwright@1.58.2`. typescript@7(네이티브)은 validate의 d.ts 파스 체크가 조용히 스킵됨(JS API 없음) — 반드시 @5. playwright 1.58.2 = 캐시된 chromium-1208 매칭.
- **`listen EFAULT` 소켓 플레이크(Windows/libuv)** — validate/capture/드라이버의 렌더 체크 서버가 간헐 즉사. 컴포넌트 문제 아님, 격리 재실행으로 해결(이번 실행에서 3회 발생·전부 재실행으로 통과).
- **props 계약은 매 빌드 tsc로 재생성**(frontend/.ds-types) — 드리프트 위험 없음. 단 앱 tsconfig의 타입 에러가 생기면 declaration emit이 경고를 내므로 buildCmd 출력 확인.
- **부분 검증 없음** — 31개 전부 렌더 체크 통과, 16개 프리뷰 작성·그레이딩 완료(2026-07-10 업로드 앵커 기준).

## 디자인 언어 출처
- `frontend/tailwind.config.ts` 주석이 "DESIGN.md"를 인용하나 **그 파일은 이 저장소에 없음** (market_aquarium 프로젝트에서 토큰만 이식했다고 함). 사용자가 경로를 주면 conventions.md/guidelines에 반영할 것.
- 토큰 요지: 흰 베이스, 흑백 카드(#161616 잉크), green/yellow는 액센트 전용, 픽셀 보더(2px solid #161616)·픽셀 섀도(2/3/5px 하드 오프셋), 폰트 Pretendard Variable(CDN @import — 원격 폰트, 번들에 파일 없음).
