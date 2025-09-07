# 금융 RAG 챗봇 API

종목코드 기반 PDF 다운로드 및 GPT 처리를 통한 금융 데이터 분석 API

## 주요 기능

- **종목코드 기반 PDF 처리**: 종목코드만 입력하면 자동으로 PDF URL 생성 및 처리
- **페이지별 병렬 처리**: PDF를 페이지별로 분할하여 병렬로 GPT API 호출
- **GPT 통합 분석**: 각 페이지 분석 결과를 통합하여 종합적인 분석 제공
- **MongoDB 저장**: 처리된 결과를 MongoDB에 체계적으로 저장
- **벡터 임베딩**: LangChain 기반 BAAI/bge-m3 모델을 사용한 문서 임베딩 및 Qdrant 저장
- **유사 문서 검색**: LangChain VectorStore를 통한 고성능 유사 문서 검색
- **스마트 텍스트 분할**: RecursiveCharacterTextSplitter를 통한 지능적 문서 청킹
- **비동기 처리**: 고성능 비동기 API 제공
- **성공 여부 검증**: total_pages와 successful_pages 비교하여 success_yn 자동 설정
- **중복 방지**: stock_code와 chunk_number 기준으로 벡터 데이터 중복 방지

## 기술 스택

- **Backend**: FastAPI, Python 3.8+
- **Database**: Oracle (기존), MongoDB (PDF 저장), Qdrant (벡터 저장)
- **PDF 처리**: PyPDF2, aiofiles
- **LLM 프레임워크**: LangChain, LangChain Community
- **임베딩**: BAAI/bge-m3, HuggingFaceEmbeddings
- **벡터 DB**: Qdrant (LangChain VectorStore 통합)
- **비동기 처리**: asyncio, motor (MongoDB), asyncpg (Oracle)

## 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정

`crawler` 디렉토리에 `.env` 파일을 생성하고 필요한 환경변수들을 설정하세요.

**필수 환경변수:**
- 데이터베이스 연결 정보 (DATABASE_URL, MONGODB_URL, MONGODB_DATABASE, MONGODB_COLLECTION)
- OpenAI API 설정 (OPENAI_API_KEY, OPENAI_MODEL, OPENAI_MAX_TOKENS, OPENAI_TEMPERATURE)
- PDF 처리 설정 (PDF_DOWNLOAD_TIMEOUT, PDF_MAX_SIZE_MB, FUND_PDF_URL)
- Qdrant 벡터 DB 설정 (QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION_NAME)
- 임베딩 모델 설정 (EMBEDDING_MODEL_NAME, EMBEDDING_DIMENSION, CHUNK_SIZE, CHUNK_OVERLAP)

**보안 주의**: 실제 API 키나 비밀번호는 절대 공개 저장소에 커밋하지 마세요.

### 3. 데이터베이스 설정

- **Oracle**: 기존 데이터베이스 연결 정보 설정
- **MongoDB**: MongoDB 서버 실행 및 연결 정보 설정
- **Qdrant**: 벡터 데이터베이스 실행 및 연결 정보 설정

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

### MongoDB 문서 관리 (새로운 기능)

- `GET /mongodb/documents` - 문서 목록 조회
- `GET /mongodb/documents/{document_id}` - 특정 문서 조회
- `GET /mongodb/documents/stock/{stock_code}` - 종목코드로 문서 조회
- `PUT /mongodb/documents/{document_id}/status` - 문서 상태 업데이트
- `DELETE /mongodb/documents/{document_id}` - 문서 삭제
- `POST /mongodb/cleanup-duplicates` - 중복 문서 정리

### Qdrant 벡터 검색 (새로운 기능)

- `POST /qdrant/store/{stock_code}` - 종목별 문서 임베딩 저장
- `POST /qdrant/search/vector` - 벡터 유사도 검색
- `POST /qdrant/search/keywords` - 키워드 검색
- `POST /qdrant/search/hybrid` - 하이브리드 검색
- `GET /qdrant/collection/info` - 컬렉션 정보 조회
- `GET /qdrant/documents/{stock_code}/exists` - 문서 존재 여부 확인
- `DELETE /qdrant/documents/{stock_code}` - 종목별 문서 삭제

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
│   ├── middlewares/          # 미들웨어 (접근 로그)
│   └── routers/             # API 라우터
│       ├── common_router.py    # 공통 API
│       ├── pdf_router.py       # PDF 관리 API
│       ├── stock_router.py     # 종목별 처리 API
│       ├── mongodb_router.py   # MongoDB 문서 관리 API
│       ├── qdrant_router.py    # Qdrant 벡터 검색 API
│       └── finance_data.py     # 금융 데이터 API
├── core/
│   ├── config.py            # 환경변수 설정 관리
│   ├── database.py          # Oracle DB 연결
│   ├── mongodb.py           # MongoDB 연결
│   └── logging.py           # 로깅 설정
├── service/                 # 비즈니스 로직 서비스
│   ├── pdf_service.py       # PDF 처리 서비스
│   ├── mongodb_service.py   # MongoDB 서비스
│   ├── langchain_embedding_service.py # LangChain 임베딩 서비스
│   ├── prompt_service.py    # 프롬프트 관리 서비스
│   └── count_service.py     # 카운트 서비스
├── utils/                   # 유틸리티 함수들
│   ├── document_processor.py # 문서 처리 유틸리티
│   └── exceptions.py        # 커스텀 예외 클래스
├── db/
│   ├── models/              # SQLAlchemy 모델
│   └── crud/                # CRUD 작업
├── schemas/                 # Pydantic 스키마
├── main.py                  # 애플리케이션 진입점
└── Dockerfile               # 컨테이너 설정
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
# 공통 문서 조회 (새로운 기능)
curl -X GET "http://localhost:8000/common/document/005930"

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

## 사용 예시

### 1. 종목별 PDF 처리 및 임베딩 저장

```bash
# 1. 종목코드로 PDF 처리
curl -X POST "http://localhost:8000/stock/process/005930"

# 2. 처리된 문서를 임베딩하여 Qdrant에 저장
curl -X POST "http://localhost:8000/qdrant/store/005930"
```

### 2. 벡터 검색

```bash
# 벡터 유사도 검색
curl -X POST "http://localhost:8000/qdrant/search/vector" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "삼성전자 재무상태",
    "limit": 5
  }'

# 키워드 검색
curl -X POST "http://localhost:8000/qdrant/search/keywords" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "삼성전자",
    "limit": 5
  }'

# 하이브리드 검색
curl -X POST "http://localhost:8000/qdrant/search/hybrid" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "삼성전자 재무상태",
    "limit": 5,
    "vector_weight": 0.7,
    "keyword_weight": 0.3
  }'
```

### 3. MongoDB 문서 관리

```bash
# 문서 목록 조회
curl -X GET "http://localhost:8000/mongodb/documents?skip=0&limit=10&status=completed"

# 종목코드로 문서 조회
curl -X GET "http://localhost:8000/mongodb/documents/stock/005930"

# 중복 문서 정리
curl -X POST "http://localhost:8000/mongodb/cleanup-duplicates"
```

### 4. 컬렉션 정보 조회

```bash
# Qdrant 컬렉션 상태 확인
curl -X GET "http://localhost:8000/qdrant/collection/info"
```

## 리팩토링 개선사항

### **코드 품질 향상**
- **중복 코드 제거**: `utils/document_processor.py`로 공통 로직 통합
- **API 구조 개선**: MongoDB와 Qdrant 전용 라우터로 기능 분리
- **미사용 코드 정리**: GridFS 관련 불필요한 코드 제거
- **유틸리티 모듈**: 재사용 가능한 함수들을 별도 모듈로 분리
- **서비스 레이어 강화**: 모든 데이터베이스 작업을 서비스 메서드로 통합

### **설정 관리 개선**
- **환경변수 기반**: 모든 설정을 `.env` 파일로 관리
- **보안 강화**: API 키 등 민감한 정보를 코드에서 분리
- **환경별 설정**: 개발/운영 환경에 따른 유연한 설정 지원

### **LangChain 기반 벡터 처리**
- **현대적 프레임워크**: LangChain을 통한 표준화된 임베딩 처리
- **BAAI/bge-m3 모델**: 고성능 다국어 임베딩 모델 사용
- **Qdrant 통합**: LangChain VectorStore를 통한 벡터 데이터베이스 연동
- **스마트 청킹**: RecursiveCharacterTextSplitter로 지능적 문서 분할

### **성능 및 유지보수성**
- **비동기 처리**: 모든 벡터 연산이 비동기로 처리
- **에러 처리**: 커스텀 예외 클래스로 명확한 에러 관리
- **로깅 개선**: 구조화된 JSON 로깅으로 디버깅 용이성 향상
- **성공 여부 검증**: total_pages와 successful_pages 비교하여 success_yn 자동 설정
- **중복 방지 강화**: stock_code와 chunk_number 기준으로 벡터 데이터 중복 방지
- **배치 처리 최적화**: MongoDB 중복 정리 시 배치 삭제로 성능 향상

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
