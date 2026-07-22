# Uni-Bot

2026 ICT 한이음 드림업 프로젝트에서 개발한 대학 학사 규정 안내 챗봇 서버 코드입니다.
RAG(Retrieval-Augmented Generation)와 Self-RAG 기법을 활용하여, 학칙·규정집 기반 질의응답과 근거 조항의 원문 하이라이팅을 제공하는 듀얼 뷰 웹 애플리케이션을 구현하였습니다.


## 프로젝트 소개

대학 학칙·규정집을 학습해서 학생 질문에 답변하는 RAG 기반 챗봇입니다.
답변 근거(조항)를 원문 PDF 페이지와 함께 보여주는 듀얼 뷰 UI를 제공합니다.

## 기술 스택

- **Backend**: FastAPI, ChromaDB, sentence-transformers, pypdf
- **Frontend**: React 19, Vite, React Router, Tailwind CSS, axios
- **PDF 추출**: Upstage Document Parse API (또는 API 없이 PyMuPDF/pypdf 대체 스크립트)

## 프로젝트 구조

```
unibot/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 엔트리포인트 (라우트 정의)
│   │   ├── services/          # RAG 검색, PDF 처리 등 비즈니스 로직
│   │   ├── Core/               # 설정 등 공통 모듈
│   │   ├── api/                # (예정) 라우터 분리용
│   │   └── utils/
│   ├── scripts/                # PDF → JSON 추출 스크립트
│   ├── data/                   # 원본/전처리 데이터
│   └── requirements.txt
└── frontend/
    └── src/
        ├── pages/
        ├── components/
        ├── api/
        └── styles/
```

## 백엔드 실행 방법

```bash
cd backend
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

브라우저에서 http://localhost:8000/docs 접속

### 환경 변수

`backend/.env` 파일을 만들고 아래 값을 채워주세요.

```
OPENAI_API_KEY=       # /api/chat 답변 생성에 사용 (answer_service.py)
UPSTAGE_API_KEY=      # PDF 추출 스크립트(extract_pdf.py)에서 사용
```

- `UPSTAGE_API_KEY`는 `extract_pdf.py`에서만 필요합니다. Upstage API 없이 추출하려면 `extract_pdf_withoutAPI.py`를 사용하고 이 값은 생략 가능합니다.
- `backend/.env`는 `.gitignore`에 포함되어 커밋되지 않으니, 팀원마다 각자 로컬에 직접 만들어야 합니다.

### PDF → ChromaDB 데이터 적재

```bash
cd backend
python scripts/extract_pdf.py data/raw/<파일명>.pdf   # 또는 extract_pdf_withoutAPI.py
python app/services/rag_service.py                    # extracted.json을 ChromaDB에 적재
```

서버 시작 시 ChromaDB가 비어 있으면 `backend/data/processed/extracted.json`을 자동으로 적재합니다.

## 프론트엔드 실행 방법

```bash
cd frontend
npm install
npm run dev
```

## 주요 API

| Method | Path | 설명 |
|---|---|---|
| GET | `/health` | 서버 상태 및 적재된 청크 수 확인 |
| POST | `/api/search` | ChromaDB 검색 결과만 확인 (답변 생성 없이) |
| POST | `/api/chat` | 검색 + 답변 생성을 포함한 채팅 API |

## 팀 구성

| 담당 | 역할 |
|---|---|
| 한다영 | Frontend |
| 조한익 | Backend |
| 이지은 | AI / Self-RAG |
| 신예진 | OCR / Infra |
| 유정진 | RAG 파이프라인 |