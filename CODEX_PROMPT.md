# Codex 작업 지시문 — M1-2 전용

**중요: 이번 저장소는 `https://github.com/hdahye1130/codyssey-M1-2`입니다.**
`codyssey-M1-1`은 첫 과제의 원본 데이터 출처일 뿐입니다. **절대 M1-1 저장소에 커밋하거나 푸시하지 마세요.**

현재 VS Code에서 열어 둔 폴더는 완성된 `solar_ai_assistant` 소스 폴더입니다. 새 코드를 처음부터 작성하지 말고 기존 파일을 우선 확인하세요.

## 지금 한 번에 진행할 작업

1. 현재 열려 있는 폴더가 태양광 AI 비서 프로젝트 루트이며 `README.md`, `backend/`, `frontend/`, `data/daily_solar.csv`, `render.yaml`이 있는지 확인하세요.
2. `data/daily_solar.csv`의 날짜가 2025-01-01~2025-12-31이며 총 365개인 것을 검증하세요. 출처는 M1-1의 KPX 발전량 분석이며 `energy_mwh` 합계 약 12,522,309.071856 MWh를 확인하세요. 가짜 데이터를 생성하거나 임의로 값을 수정하지 마세요.
3. Python 3.10+ 환경을 사용할 수 있다면 `cd backend && python -m pip install -r requirements.txt && python -m pip install pytest httpx && python -m pytest -q`를 실행하고 오류는 최소한으로 수정하세요. `frontend`에서 `npm run build`도 확인하세요. 설치·실행이 불가한 환경이라면 가능한 검증까지만 수행하고 이유를 보고하세요.
4. 기능을 확인하세요: FastAPI + `/docs`, 데이터 CRUD + `/api/data/summary`, Firestore 컬렉션 두 개, OpenAI 기반 `/api/chat`, 대화 저장/조회/불러오기, 바닐라 HTML/CSS/JavaScript 화면, 로딩 표시, 단일 사용자 접근 코드. 이미 동작하는 코드는 불필요하게 재작성하지 마세요.
5. 현재 GitHub 저장소 `hdahye1130/codyssey-M1-2`가 비어 있으므로, 이 폴더의 파일이 새 저장소 **루트**에 올라가도록 Git 초기화 및 원격 연결 후 `main` 브랜치에 commit+push하세요. 원격 주소: `https://github.com/hdahye1130/codyssey-M1-2.git`. Git 설정/인증 문제로 push가 실패하면 사용자에게 필요한 버튼과 로그인 절차만 알려주고 멈추세요. 다른 저장소로 대신 올리지 마세요.
6. `.env`, Firebase 서비스 계정 키, OpenAI API 키 등 비밀정보와 `.venv`, `dist`, 캐시를 GitHub에 올리지 마세요. 실제 Firebase·OpenAI 키가 현재 제공되지 않았다면 채팅/배포 실연동이 완료됐다고 쓰지 마세요.
7. `SUBMISSION_CHECKLIST.md`와 `README.md`의 테스트·GitHub 업로드 상태를 실제 결과에 맞게 갱신하세요. Render와 Vercel 서비스 배포는 **실제 계정/키가 설정되어 있고 명시적 승인과 접근이 가능한 경우에만** 진행하세요. 실계정 연결이 없는 상태는 나중에 사용자가 설정할 단계로 남겨두세요.

## 완료 보고 (간단한 한국어)
- GitHub에 실제 올라간 URL과 커밋
- 테스트 통과 결과 또는 오류
- 지금 다음으로 사용자가 해야 할 일(예: Firebase 생성 → OpenAI API 키 → Render/Vercel 배포)
- 어떤 키도 채팅 답변, 로그, GitHub에 노출하지 말 것
