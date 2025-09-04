# 금융 RAG 챗봇 API

종목코드 기반 PDF 다운로드 및 GPT 처리를 통한 금융 데이터 분석 API

## 주요 기능

- **종목코드 기반 PDF 처리**: 종목코드만 입력하면 자동으로 PDF URL 생성 및 처리
- **페이지별 병렬 처리**: PDF를 페이지별로 분할하여 병렬로 GPT API 호출
- **GPT 통합 분석**: 각 페이지 분석 결과를 통합하여 종합적인 분석 제공
- **MongoDB 저장**: 처리된 결과를 MongoDB에 체계적으로 저장
- **비동기 처리**: 고성능 비동기 API 제공

## 기술 스택

- **Backend**: FastAPI, Python 3.8+
- **Database**: Oracle (기존), MongoDB (PDF 저장)
- **PDF 처리**: PyPDF2, aiofiles
- **비동기 처리**: asyncio, motor (MongoDB), asyncpg (Oracle)

## 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정

`env.example` 파일을 참고하여 `.env` 파일을 생성하고 필요한 설정을 입력하세요.

```bash
cp env.example .env
```

### 3. 데이터베이스 설정

- **Oracle**: 기존 데이터베이스 연결 정보 설정
- **MongoDB**: MongoDB 서버 실행 및 연결 정보 설정

### 4. 애플리케이션 실행

```bash
# 개발 모드
uvicorn crawler.main:app --reload --host 0.0.0.0 --port 8000

# 프로덕션 모드
uvicorn crawler.main:app --host 0.0.0.0 --port 8000
```

## API 문서

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API 엔드포인트

### 종목별 PDF 처리 (새로운 기능)

- `POST /stock/process/{stock_code}` - 종목코드로 PDF 처리
- `GET /stock/documents/{stock_code}` - 종목별 문서 목록 조회
- `GET /stock/documents/{stock_code}/{document_id}` - 특정 문서 조회
- `DELETE /stock/documents/{stock_code}/{document_id}` - 문서 삭제

### 기존 PDF 관리 (MongoDB)

- `POST /pdf/download` - PDF 다운로드 및 저장
- `GET /pdf/documents` - PDF 문서 목록 조회
- `GET /pdf/documents/{document_id}` - 특정 PDF 문서 조회
- `PUT /pdf/documents/{document_id}/status` - 문서 상태 업데이트
- `DELETE /pdf/documents/{document_id}` - PDF 문서 삭제

### 금융 데이터 (Oracle)

- `GET /finance_data/count` - 금융 데이터 개수 조회

## 프로젝트 구조

```
crawler/
├── api/
│   ├── middlewares/          # 미들웨어
│   └── routers/             # API 라우터
├── core/
│   ├── config.py            # 설정 관리
│   ├── database.py          # Oracle DB 연결
│   ├── mongodb.py           # MongoDB 연결
│   └── logging.py           # 로깅 설정
├── db/
│   ├── models/              # SQLAlchemy 모델
│   └── crud/                # CRUD 작업
├── service/                 # 비즈니스 로직
├── schemas/                 # Pydantic 스키마
└── main.py                  # 애플리케이션 진입점
```

## 사용 예시

### 종목 PDF 처리 (새로운 기능)

```bash
# 삼성전자(005930) PDF 처리
curl -X POST "http://localhost:8000/stock/process/005930"

# 특정 프롬프트 타입으로 처리
curl -X POST "http://localhost:8000/stock/process/005930?prompt_type=fund_document"
```

### 종목별 문서 조회

```bash
# 삼성전자 문서 목록 조회
curl -X GET "http://localhost:8000/stock/documents/005930"

# 특정 문서 조회
curl -X GET "http://localhost:8000/stock/documents/005930/{document_id}"
```

### 기존 PDF 다운로드 및 저장

```bash
curl -X POST "http://localhost:8000/pdf/download" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://example.com/document.pdf",
       "filename": "custom_name.pdf"
     }'
```

## 로깅

- **형식**: JSON 로그
- **위치**: `./logs/app.log`
- **회전**: 일별 로그 파일 생성 (10일 보관)

## 개발 가이드

### 코드 스타일

- Python PEP 8 준수
- 타입 힌트 사용
- 비동기 함수 활용

### 에러 처리

- 모든 API는 표준화된 에러 응답 제공
- 로깅을 통한 에러 추적
- HTTP 상태 코드 적절히 사용

## 라이선스

이 프로젝트는 내부 사용을 위한 것입니다.
