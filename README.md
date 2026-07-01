# Market Village — 투자 감정 거울 라이프시뮬

내 투자 성격을 복제한 AI 클론이 블라인드 처리된 과거 실제 코인 시장에서 30일을
살아간다. 플레이어는 클론을 직접 조종하지 않고, 뉴스 3지선다·전날밤 회피·위기
개입(A/B/C)으로만 클론의 감정을 흔든다. 같은 30일을 회차 반복(NG+)하며
"1회차의 나 vs 2회차의 나"를 거울처럼 비교해 공포·탐욕·FOMO·확증편향 패턴을
직시하고 교정한다. 상세 설계는 `Market_Village_PRD_FINAL.md`(제품 요구사항),
조립 흐름은 `ASSEMBLY_PRD.md` 참고.

## 빠른 시작 — 서버 1개만 켜면 됩니다

MongoDB·프론트엔드 서버 **불필요**(전부 폴백/자기완결). 터미널은 **PowerShell
또는 cmd**를 쓴다 — Git Bash에서 uvicorn을 직접 돌리면 Windows 프로세스간 소켓
문제(`WinError 10014`)로 안 뜰 수 있다.

```powershell
cd backend
python -m pip install -r requirements.txt
python -m uvicorn market_live_server:app --port 8100
```

브라우저에서:

- Next.js `frontend/`의 **`/play`** — 통합 플레이 화면(권장 진입점). 인터뷰 →
  전날밤 일과+회피 → 아침 뉴스 3지선다 → 위기 개입(A/B/C) → 정산/연출 → 30일
  완주 → 결과 카드 → 새 회차 → 회차 비교(거울)까지 한 화면에서.
- `http://localhost:8100/map` — Phaser 마을 맵 뷰어. GameRun의 state를 배경
  연출로 보여주는 좌표 브릿지(§12.0) — 게임 진행은 결정 안 함.

### LLM 표현 계층 (선택)

대사·독백 표현에 LLM을 쓰려면(수치 결정에는 영향 없음 — 표현만 교체) 레포
루트의 `.env`에 키를 넣는다:

```env
OPENROUTER_API_KEY=sk-or-...
```

키가 없으면 자동으로 오프라인 결정론 템플릿으로 동작한다(플레이 가능, 과금
없음). OS 환경변수에 `OPENAI_API_KEY`가 이미 있으면 그것도 자동 인식된다.

## 아키텍처 — GameRun(정본) + 맵 배경 연출

```
[인터뷰] → clone_spec(클론 = 거울)
   │
[GameRun] ── 유일한 게임 경로(sim/game_run.py) — 하루씩 진행, 결정론, 회차 재현
   │  전날밤(회피) → 아침(뉴스 3지선다) → 위기(개입 A/B/C·저항판정) → 정산
   │  내부: news · trap_pipeline · resistance · crisis_day · 회계 · clone_stats
   │
   └─(state)→ 표현 계층(sim/presentation.py) — 연출명령 + 대사(LLM opt-in)
              Next.js `/play` UI

[/map] — Phaser 맵 뷰어. GameRun의 state를 좌표 브릿지(§12.0)로 배경 연출만
         한다(게임 진행은 결정 안 함). the_ville 타일맵 + path_finder 재사용.
```

`/control/game/*` 엔드포인트가 게임 진행 경로, `/map`은 그 state를 보여주는
배경 연출 경로다. 구 엔진(`sim.engine.GameSession`, 마을 NPC 라운드 모델)과
`/game`·`/demo` 위젯은 2026-07-01 실서비스 전환 정리에서 완전히 제거됐다.
자세한 결정 배경은 `ASSEMBLY_PRD.md`.

## 시뮬레이션 모듈 (`backend/sim/`)

| 모듈 | 기능 |
|---|---|
| `game_run.py` | 하루씩 진행 가능한 회차 세션(GameRun) — 플레이의 근간 |
| `run_loop.py` | 30일 batch 실행(회차 비교용) + `step_day` 공유 코어 |
| `crisis_day.py` | 하루치 결정 파이프라인 조립(뉴스→컨텍스트→함정→회계+스탯) |
| `traps.py` | 6함정(F1/F2/G1/G2/M1/M2) 분류 + 트리거 감지 |
| `trap_pipeline.py` | 함정 판정 STEP1~6 + 확증편향 잠금 + 격화 양날 |
| `resistance.py` | 개입 전략 A/B/C + 래포 + 4요소 저항식 |
| `news.py` | 뉴스 3지선다(가격 불변, 클론 심리만) |
| `clone_spec.py` | 인터뷰 → 6함정 취약점·뉴스톤 계수·합리화 언어·고유 이벤트 |
| `fate_line.py` | 고정 운명선(블라인드 과거 데이터) + 가격 하이브리드(90%고정+10%출렁임) |
| `trade.py` | 가격수용자 회계(평단·실현손익·자금행선지) |
| `clone_stats.py` | 클론 표시 4스탯(공포내성/탐욕제어/FOMO저항/멘탈회복) |
| `runs.py` | 회차(NG+) 3계층 저장 + 회차 비교(§13.6 거울) |
| `result_card.py` | 결과 카드 2축 평가(고수/벼락부자형/강철멘탈형/호구) |
| `day_loop.py` | 8슬롯 하루·일과 셔플·확률 외란 |
| `avoidance.py` | 전날밤 회피 + 클론의 NPC 선택(약점 끌림) |
| `social.py` | 설득/FGI(공포탐욕지수) 개입 |
| `sentiment.py` | 감정 기여도 계산 |
| `presentation.py` | 엔진 결정 → 연출명령+대사(LLM opt-in) |
| `interview.py` / `interview_llm.py` | 인터뷰 질문·클론 스펙 생성 |
| `db.py` | 게임 세션 영속화(MongoDB, 실패시 인메모리 폴백) |
| `tuning.py` | 전 수치 상수 단일 소스 |

## 테스트

```bash
cd backend
python -m pytest -q
```

전부 오프라인·결정론(LLM 키·네트워크·MongoDB 불필요). `MARKET_DISABLE_LLM=1`이
`conftest.py`에서 자동 설정돼 테스트는 절대 LLM을 실호출하지 않는다.

## 진행 상태

`PLANS.md`(작업 보드) · `CHECKLIST.md`(실행 트레이스) · `RETRO.md`(회고) ·
`HANDOFF.md`(전달 상태) 참고. 플레이 가능한 수직 슬라이스(인터뷰→하루루프→
정산→카드→회차비교)는 완성; 교류(메신저·FGI)·다자산 포트폴리오·맵 카메라
연동·LLM 대화형 인터뷰는 확장 예정.

## 크레딧

맵 에셋: [Generative Agents](https://arxiv.org/abs/2304.03442) 프로젝트 기반
- Background: PixyMoon
- Furniture: LimeZu
- Characters: pipohi
