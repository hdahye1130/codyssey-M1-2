# 솔라 인사이트 — 태양광 발전량 AI 비서 (M1-2)

첫 번째 M1-1 과제의 2025년 한국전력거래소(KPX) 태양광 **전력시장 거래량** 일별 CSV 365개로 만드는 데이터 기반 AI 채팅 웹 서비스입니다. 기존 데이터와 분석 결과를 재사용하고, 서비스에서 통계·데이터 수정·대화 기록 관리까지 수행합니다.

**주의**: M1-1 데이터는 전국 모든 설비의 총발전량이 아닙니다. 한전 직접 거래와 자가용 발전은 범위 밖이며, 관측값만으로 날씨의 인과관계를 확정할 수 없습니다.

**GitHub 제출 저장소:** https://github.com/hdahye1130/codyssey-M1-2 (M1-1 저장소와 별도)

## 구성 및 핵심 기능

| 요구사항 | 구현 위치 |
|---|---|
| FastAPI + Swagger `/docs` | `backend/app/main.py` |
| Firestore `data`, `conversations` | `backend/app/store.py` |
| 입력 검증 (Pydantic) | `backend/app/models.py` |
| 통계·AI 컨텍스트 주입 | `backend/app/service.py` |
| M1-1 365일 데이터 중복 없이 자동 시드 | `backend/seed_data.py` |
| 채팅·로딩·데이터 CRUD·대화 목록/불러오기 | `frontend/index.html`, `frontend/app.js` |
| Vercel 환경변수 `API_SERVER_URL` | `frontend/build.mjs` |

## 데이터 출처

- 데이터명: 한국전력거래소_지역별 시간별 태양광 및 풍력 발전량_20251231
- 원본 페이지: https://www.data.go.kr/data/15065269/fileData.do
- 기존 분석 저장소: https://github.com/hdahye1130/codyssey-M1-1
- 기존 CSV 재사용본: [`data/daily_solar.csv`](data/daily_solar.csv) (M1-1 원본에서 `date`, `energy_mwh`만 복사)
- 날짜: **2025-01-01~2025-12-31** (365일), 단위: MWh/일
- 수집/가공: 첫 과제의 `analysis.py`로 지역별 태양광 전력거래량을 일별 합산, 7일/30일 이동평균 등 계산. 본 앱은 `date`, `energy_mwh`만 Firestore에 복사합니다.
- 재현 방법: 이 M1-2 저장소에 `data/daily_solar.csv`가 포함되어 있습니다. M1-1 원본 자료와 수치 일치 여부를 확인할 수 있습니다. 별도 경로를 사용하려면 `SOLAR_CSV_PATH`로 지정합니다.

## 데이터 흐름

```text
M1-1: data/daily_solar.csv (365일)
    ↓ seed_data.py (날짜를 고유 ID로 사용, 기존 자료 변경 없이 누락만 추가)
Firestore: data 컬렉션
    ↓ GET /api/data/summary (기간·개수·평균·최대·최소·최근 7일 추세·월별 평균)
AI 질문 → 서버에서 최근 대화 + 데이터 요약을 시스템 프롬프트에 주입 → COPA API
    ↓
답변 + Firestore conversations 컬렉션에 자동 저장 → 웹 화면에 표시
```

## API 명세

- `POST /api/data` : `date`, `value`, `memo` 새 기록 추가 (같은 날짜 중복 금지)
- `GET /api/data` : 전체 기록 조회
- `PUT /api/data/{id}` : 수치·메모 수정 (날짜 변경은 삭제 후 재등록)
- `DELETE /api/data/{id}` : 기록 삭제
- `GET /api/data/summary` : 최신 데이터의 전체·월별 통계
- `POST /api/conversations` : 빈 대화/메시지 저장
- `GET /api/conversations` : 대화 목록
- `GET /api/conversations/{id}` : 메시지를 포함한 대화 불러오기
- `DELETE /api/conversations/{id}` : 대화 삭제
- `POST /api/chat` : 질문 → AI 답변 → 대화 자동 저장
- `GET /health` : 서버 상태
- `GET /docs` : Swagger API 문서

API는 `/health`와 `/docs`를 제외하고 `X-App-Token` 헤더로 접근 코드를 확인합니다. 단일 사용자 교육 과제용이며 다중 사용자 로그인 시스템은 아닙니다.

## 로컬 실행 (Python 3.10 이상, Node.js는 프론트 빌드에만 필요)

1. 이 저장소의 `data/daily_solar.csv`(365개)가 포함되어 있으므로 CSV를 별도로 내려받을 필요가 없습니다.
2. `backend`에서 `python -m venv .venv`로 가상환경을 만들고 Windows의 경우 `.venv\\Scripts\\activate`, macOS/Linux의 경우 `source .venv/bin/activate`를 실행합니다.
3. `python -m pip install -r requirements.txt`를 실행합니다.
4. `.env.example`을 `.env`로 복사합니다. **LOCAL_DEMO=1**로 시작하면 Firebase 없이 JSON 파일로 CRUD·통계·대화 기록을 시험할 수 있습니다. 실제 COPA 채팅은 로컬 모드에서도 `COPA_API_KEY`가 있어야 합니다.
5. `python seed_data.py`로 365일 데이터를 넣고, `uvicorn app.main:app --reload`로 API를 실행합니다. http://localhost:8000/docs 에 접속해 API 문서를 확인합니다.
6. 다른 터미널에서 `frontend`로 이동해 `npm run build`, `python -m http.server 5173 -d dist`를 실행합니다. http://localhost:5173 에서 접근 코드를 입력합니다.

**로컬 데모 한계:** `LOCAL_DEMO=1`은 Firebase 대신 로컬 파일을 사용하므로 Firebase 연동 시연으로 제출하면 안 됩니다. 실제 과제 제출 시 Firebase 연결과 클라우드 배포를 확인해야 합니다.

## 실제 Firestore 연동 및 배포

1. [Firebase Console](https://console.firebase.google.com/)에서 프로젝트 생성 → **Build → Firestore Database → Create database**를 선택합니다. 이 서버만 데이터에 접근하도록 Firestore 웹 클라이언트 직접 접근은 차단합니다.
2. Firebase 프로젝트 설정(톱니바퀴) → **서비스 계정** → **새 비공개 키 생성**에서 JSON 키를 발급합니다. 키 파일을 GitHub나 채팅에 올리지 마세요.
3. COPA에서 발급받은 **virtual key**를 `COPA_API_KEY`로 설정합니다. API 주소는 `https://copa.codyssey.kr/v1/chat/completions`입니다.
4. [Render](https://dashboard.render.com/)에 GitHub 저장소를 연결해 Web Service를 생성하거나 이 폴더의 `render.yaml` Blueprint를 사용합니다. Blueprint `rootDir=backend`. 환경 변수는 `LOCAL_DEMO=0`, `COPA_API_KEY`, `FIREBASE_CREDENTIALS_JSON`(키 JSON 전체), `APP_ACCESS_TOKEN`(길고 임의적인 비밀번호), `ALLOWED_ORIGINS`(Vercel 배포 주소)를 설정합니다. Firestore 데이터가 비어 있으면 시작 시 `seed_data.py`가 누락된 CSV 행을 추가합니다. 이후 재시작에는 기존 수정값을 유지합니다.
5. Render에서 `https://<서비스명>.onrender.com/health`와 `https://<서비스명>.onrender.com/docs`를 확인합니다. 무료 인스턴스는 처음 요청에 지연이 발생할 수 있습니다.
6. [Vercel](https://vercel.com/)에서 동일 GitHub 저장소를 가져오되 **Root Directory**를 `frontend`, Framework Preset은 `Other`, Build Command는 `npm run build`, Output Directory는 `dist`로 지정합니다. 환경 변수 `API_SERVER_URL`을 Render의 `https://...onrender.com` 주소로 설정합니다.
7. Vercel URL을 Render의 `ALLOWED_ORIGINS`에 추가하고 재배포합니다. 웹의 **접근 코드** 칸에 `APP_ACCESS_TOKEN` 값을 넣으면 연결됩니다.

중요: `FIREBASE_CREDENTIALS_JSON`, `COPA_API_KEY`, `APP_ACCESS_TOKEN`은 웹 프론트 코드나 저장소에 넣지 않습니다. 프론트의 `API_SERVER_URL`만 공개되어도 괜찮습니다. AI 호출은 항상 서버에서만 합니다.

## 환경 변수

| 변수 | 위치 | 용도 |
|---|---|---|
| `COPA_API_KEY` | Render 백엔드 | COPA 호출 (필수) |
| `COPA_MODEL` | 백엔드(선택) | 기본 `gpt-5-mini` |
| `FIREBASE_CREDENTIALS_JSON` | Render 백엔드 | Firestore 서비스 계정 JSON (필수) |
| `APP_ACCESS_TOKEN` | Render 백엔드 | 단일 사용자 접근 코드 (필수) |
| `LOCAL_DEMO` | 백엔드 | 로컬 시험은 `1`, 배포는 `0` |
| `ALLOWED_ORIGINS` | Render 백엔드 | Vercel 웹 URL 허용 목록 |
| `API_SERVER_URL` | Vercel 프론트 빌드 | Render API 기본 URL |
| `SOLAR_CSV_PATH` | 백엔드(선택) | CSV 파일을 직접 지정할 때만 사용 |

## 테스트 및 과제 검증

`cd backend && python -m pytest -q` — 샘플 CSV 101행 입력/중복 시드, 입력값 검증, CRUD, 요약, 대화 생성/조회/삭제, 채팅(mock AI), COPA 요청 형식·응답 처리, 접근코드 확인. 2026-10-29 Python 3.12.13 환경에서 **6 passed**를 확인했습니다. Starlette TestClient의 httpx 사용 중단 예고 경고 1건이 있으며 테스트 실패는 없습니다. 이 테스트는 외부 Firestore/COPA/Render/Vercel 실연동을 대신하지 않습니다.

**제출 시 캡처해야 할 화면**: ① 데이터 요약과 AI 질문·실제 답변 ② 데이터 관리에서 추가/수정/삭제 중 1개 ③ 저장된 대화 불러오기 ④ Render `/docs` ⑤ Vercel 배포 화면. 실제로 배포 및 테스트한 뒤 캡처하세요.

## AI 활용 로그와 한계

- AI 활용: 앱 구조 설계, API·프론트 코드 작성, 테스트 코드·배포 문서 작성 보조.
- 목적: 반복 작업 절감, 시계열 분석 결과를 질의응답 서비스로 재활용.
- 검증: `pytest` 자동화와 실제 외부 서비스 연동 점검은 구분하여 기록. 키가 없는 환경에서는 외부 COPA/Firebase/배포 성공을 주장하지 않습니다.
- 한계: 무료 Render 콜드스타트, COPA 사용량·비용, 365일 단일 연도 관측만을 사용하는 분석 한계, Firestore 단일 사용자 토큰 보호(세밀한 사용자별 권한 없음).

## 배포 URL (실제 배포 후 기록)

- 프론트엔드 Vercel: **미배포**
- 백엔드 Render: **미배포**
- Swagger UI: **미확인**

## 실행 검증 결과 (2026-10-29)

- M1-1 원본 CSV(blob `04e97c175a0e90817e61fa30724116e3b4298dc6`)를 읽기 전용으로 조회하여 날짜·발전량 365행 모두 일치 확인. 원본 저장소는 수정하지 않았습니다.
- 2025-01-01~2025-12-31 연속 365일, 합계 **12,522,309.071856 MWh**. CSV 값은 변경하지 않았습니다.
- Python 3.12.13 가상환경에서 requirements 및 pytest/httpx 설치 후 `python -m pytest -q`: **5 passed, 1 warning**.
- 실제 CSV 시드: 신규 365개 등록. 테스트에서 중복 시드 방지, CRUD, 요약, mock 채팅 및 대화 저장/조회/삭제, 접근 코드, `/docs`와 OpenAPI 응답 확인.
- Node.js 22.16.0 임시 실행 환경으로 `npm run build` 성공, JavaScript 구문 검사 성공. 산출물 `dist` 및 가상환경은 Git에서 제외합니다.
- 수정: CSV 탐색 시 현재 프로젝트 우선 선택, 한글 접근 코드 비교 시 서버 예외 방지.
- GitHub: M1-2 원격 연결 및 로컬 main 커밋 완료. HTTPS Git 인증정보가 없어 push 실패(`could not read Username`). **GitHub 업로드 미완료**. VS Code의 소스 제어 → 변경 내용 게시/동기화에서 GitHub 로그인을 완료한 뒤 `git push -u origin main`을 실행하세요.
- 실제 Firebase/COPA 인증정보가 제공되지 않아 실연동 및 Render/Vercel 배포는 미검증·미배포입니다. 브라우저 UI 실조작 및 제출 캡처도 남아 있습니다.
