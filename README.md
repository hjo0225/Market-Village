# Market Village — 투자 감정 거울 라이프시뮬

> 내 투자 성격을 복제한 AI 클론이 블라인드 처리된 **과거 실제 코인 시장**에서
> 10일을 살아간다. 나는 클론을 조종할 수 없다 — 지켜보고, 흔들 수만 있다.

## 문제 정의 — 왜 만들었나

초보~중급 투자자의 손실 주범은 정보 부족이 아니라 **감정 패턴**이다. 급락에
던지는 공포, 급등에 올라타는 FOMO, 익절 못 하는 탐욕, 듣고 싶은 뉴스만 믿는
확증편향. 이 패턴에는 세 가지 고약한 성질이 있다:

1. **자기 눈에는 안 보인다.** "나는 안 그래"가 기본값이고, 매매 순간에는 그게
   감정인지 판단인지 구분이 안 된다.
2. **실전에서 배우면 수업료가 실제 돈이다.** 그리고 잃고 나서도 "시장이
   이상했다"로 합리화되며 패턴은 살아남는다.
3. **차트 공부로는 안 고쳐진다.** 지식의 문제가 아니라 행동의 문제라서.

즉 필요한 것은 "내 감정 패턴을 **내 돈을 걸지 않고**, **제3자의 눈으로**,
**반복 관찰**할 수 있는 장치"다.

## 해결 — 설계 원칙 4가지

| 문제 | 해결 |
|---|---|
| 내 패턴이 내 눈에 안 보임 | **클론 관찰자 시점** — 인터뷰로 내 성향(6가지 감정 함정 취약점)을 복제한 클론이 대신 산다. 조종 불가, 뉴스 선택·만남·위기 개입으로 감정만 흔들 수 있다. 내 못난 매매를 남 일처럼 지켜보게 된다. |
| 실전 수업료가 실제 돈 | **블라인드 과거 실제 데이터(운명선)** — 실제 업비트 일봉의 한 구간을 종목·시기를 가린 채 재생. 가격은 이미 정해져 있고(§가격 불변) 클론의 감정만 결과를 가른다. 예측 게임으로 변질될 수 없는 구조. |
| "왜 잃었는지" 복기가 안 됨 | **매매 서사** — 매일 밤 "「패닉 셀」의 감정에 휩쓸려 전량 매도했어요 → 시세 -3.2% → 내 자산 -1.1%"처럼 **감정 원인→행동→시세→수익률**을 문장으로 정산. 발자취·이벤트 타임라인에 일별로 쌓인다. |
| 한 번 봐선 안 고쳐짐 | **거울 회차(NG+)** — 같은 운명선을 다시 산다. 1회차의 나 vs 2회차의 나를 같은 날짜로 겹쳐 비교해, 행동이 갈린 날(개입이 패턴을 바꾼 날)만 짚어준다. |

여기에 감정 **자극 장치**로 마을을 얹었다: 성격이 다른 트레이더 NPC 8종(패닉
개미, FOMO 단타, 음모론 인플루언서, 가치투자자…)이 같은 시장을 살며 클론과
마주치고(1:1 대화), 이벤트 날엔 마을 게시판에 모여 떠든다. 게시판 여론은
"오른다/내린다 힌트"가 아니라 **군중 쏠림 경고**로 프레임한다 — 쏠림을 따라가는
것 자체가 함정이라는 게 이 게임의 교훈이므로.

## 구현 현황 — 무엇이 어떻게 돌아가나

- **클론 생성**: 대화형 인터뷰(LLM opt-in) → `clone_spec`(6함정 취약점·뉴스톤
  계수·합리화 언어) + 시작 포트폴리오 4유형 배분 + 에이전트 이름 짓기.
- **하루 루프(10일)**: 전날밤 일과·회피 → 아침 뉴스 3지선다(가격 불변, 심리만)
  → 마을 걷기·만남(포켓몬식 — 옆 칸까지 와서 마주보고 대화) → 위기 발동 시
  개입 A/B/C(저항 판정) → 밤 정산(매매 서사 모달).
- **표현 계층 분리**: 게임 수치는 전부 순수·결정론(`sim/`), LLM은 대사 표현만
  (키 없으면 오프라인 템플릿 폴백, 과금 0). 조회 GET은 멱등 — 새로고침·리로드에
  안전.
- **완주 후**: 결과 카드(2축 평가) → 새 회차 → 회차 비교(거울).

## 빠른 시작 (로컬)

MongoDB·LLM 키 **불필요**(전부 폴백/자기완결). 터미널은 **PowerShell 또는
cmd** — Git Bash에서 uvicorn을 직접 돌리면 Windows 소켓 문제(`WinError
10014`)로 안 뜰 수 있다.

```powershell
cd backend
python -m pip install -r requirements.txt
python -m uvicorn market_live_server:app --port 8100
```

```powershell
cd frontend
npm ci
npm run dev   # http://localhost:3000/play — 유일한 게임 진입점
```

- **`/play`** — 인터뷰 → 하루 루프 → 10일 완주 → 결과 카드 → 회차 비교까지 한 화면.
- `http://localhost:8100/map` — Phaser 마을 맵 뷰어(배경 연출 전용, 게임 진행은 결정 안 함).

### LLM 표현 계층 (선택)

대사 표현에 LLM을 쓰려면 레포 루트 `.env`에 `OPENROUTER_API_KEY=sk-or-...`
(또는 OS 환경변수 `OPENAI_API_KEY`). 없으면 오프라인 결정론 템플릿으로 동작.
서버 게이트 `MV_ALLOW_LLM`·일일 한도 `MV_LLM_DAILY_MAX`로 과금 방어.

## 배포 · CI/CD (2026-07-06 라이브)

**main에 머지하면 서버에 자동 반영된다.**

```
PR 열기 → ci.yml (pytest + tsc, 테스트만)
main 머지 → deploy.yml: 테스트 게이트 → EC2에 SSH → docker compose 재빌드 (~5-10분)
```

- 인프라: AWS EC2 1대(서울) + Docker Compose 4컨테이너 — mongo(인증·외부
  미노출) / backend / frontend / caddy(:80). 접속 주소·인스턴스 정보는
  `HANDOFF.md` 전달 환경 참고.
- 테스트가 깨지면 배포가 자동으로 막힌다. 수동 재배포는 Actions 탭 →
  Deploy → Run workflow.
- 맵 에셋 `environment/`는 gitignore — 서버에 수동 업로드(변경 시 재복사 필요).

## 아키텍처

```
[인터뷰] → clone_spec(클론 = 거울)
   │
[GameRun] ── 유일한 게임 경로(sim/game_run.py) — 하루씩 진행, 결정론, 회차 재현
   │  전날밤(회피) → 아침(뉴스 3지선다) → 위기(개입 A/B/C·저항판정) → 정산
   │  내부: news · trap_pipeline · resistance · crisis_day · 회계 · clone_stats
   │
   └─(state)→ 표현 계층(sim/presentation.py) — 연출명령 + 대사(LLM opt-in)
              Next.js `/play` UI + Phaser `/map` 배경(좌표 브릿지 §12.0)
```

`/control/game/*`가 게임 진행 경로, `/map`은 그 state를 보여주는 배경 연출
경로다. 상세 설계는 `Market_Village_PRD_FINAL.md`, 조립 흐름은 `ASSEMBLY_PRD.md`.

## 시뮬레이션 모듈 (`backend/sim/`)

| 모듈 | 기능 |
|---|---|
| `game_run.py` | 하루씩 진행 가능한 회차 세션(GameRun) — 플레이의 근간 |
| `run_loop.py` | 전체 회차 batch 실행(회차 비교용) + `step_day` 공유 코어 |
| `crisis_day.py` | 하루치 결정 파이프라인 조립(뉴스→컨텍스트→함정→회계+스탯) |
| `traps.py` | 6함정(F1/F2/G1/G2/M1/M2) 분류 + 트리거 감지 |
| `trap_pipeline.py` | 함정 판정 STEP1~6 + 확증편향 잠금 + 격화 양날 |
| `resistance.py` | 개입 전략 A/B/C + 래포 + 4요소 저항식 |
| `news.py` | 뉴스 3지선다(가격 불변, 클론 심리만) |
| `clone_spec.py` | 인터뷰 → 6함정 취약점·뉴스톤 계수·합리화 언어·고유 이벤트 |
| `fate_line.py` | 고정 운명선(블라인드 과거 데이터) + 가격 하이브리드(90%고정+10%출렁임) |
| `trade.py` | 가격수용자 회계(평단·실현손익·자금행선지) |
| `clone_stats.py` | 클론 7스탯(6함정 개별 저항 + 멘탈회복) |
| `runs.py` | 회차(NG+) 3계층 저장 + 회차 비교(§13.6 거울) |
| `result_card.py` | 결과 카드 2축 평가(고수/벼락부자형/강철멘탈형/호구) |
| `day_loop.py` | 8슬롯 하루·일과 셔플·확률 외란 |
| `avoidance.py` | 전날밤 회피 + 클론의 NPC 선택(약점 끌림) |
| `personas.py` | 트레이더 NPC 8종(자극 4 + 도움 4) + 마을 프리셋 |
| `social.py` | 설득/FGI 개입 + 게시판 문구 풀 |
| `board_v2.py` | 이벤트 게시판 대화 생성(오프라인 결정론 + LLM opt-in) |
| `meeting_talk.py` | 1:1 만남 대사(결정론, 폰 채팅 연출용) |
| `agent_state.py` | NPC 감정 누적·개별 래포·기억 발화 |
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

전부 오프라인·결정론(LLM 키·네트워크·MongoDB 불필요). `conftest.py`가
LLM 실호출을 자동 차단한다. 프론트는 `cd frontend && npx tsc --noEmit`.

## 진행 상태

`PLANS.md`(작업 보드) · `CHECKLIST.md`(실행 트레이스) · `RETRO.md`(회고 규칙) ·
`HANDOFF.md`(전달 상태 — coded/merged/live) 참고. 수직 슬라이스(인터뷰→하루
루프→정산→카드→회차비교)와 마을 표현 계층(맵 걷기·만남·게시판·폰 UI·매매
서사), AWS CI/CD까지 **live**. 확장 예정: 1:1 대화 LLM 다양화, 10일 밸런스
튜닝, IAM 유저 전환, 도메인+TLS.

## 크레딧

맵 에셋: [Generative Agents](https://arxiv.org/abs/2304.03442) 프로젝트 기반
- Background: PixyMoon
- Furniture: LimeZu
- Characters: pipohi
