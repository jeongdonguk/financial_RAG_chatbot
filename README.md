# Fund RAG Chatbot

PDF 기반 펀드 문서 분석 및 질의응답을 위한 RAG(Retrieval-Augmented Generation) 챗봇 시스템

## 프로젝트 개요

이 프로젝트는 펀드 관련 PDF 문서를 수집, 분석, 저장하여 사용자가 자연어로 질문할 수 있는 RAG 챗봇을 구축하는 것을 목표로 합니다.

### 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PDF Crawler   │───▶│    MongoDB      │───▶│     Qdrant      │───▶│   RAG Chatbot   │
│   (데이터 수집)    │    │   (문서 저장)     │    │    (벡터 저장)    │    │     (질의응답)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 프로젝트 구조

```
fund_RAG_chatbot/
├── crawler/                    # 데이터 수집 및 벡터화 모듈 (완성)
│   ├── api/                   # FastAPI 라우터
│   │   ├── middlewares/       # 미들웨어 (접근 로그)
│   │   └── routers/           # API 라우터들
│   │       ├── common_router.py    # 공통 API
│   │       ├── pdf_router.py       # PDF 관리 API
│   │       ├── stock_router.py     # 종목별 처리 API
│   │       └── embedding_router.py # 임베딩 및 벡터 검색 API
│   ├── core/                  # 핵심 설정 및 연결 관리
│   │   ├── config.py          # 환경변수 설정 관리
│   │   ├── database.py        # Oracle DB 연결
│   │   ├── mongodb.py         # MongoDB 연결
│   │   └── logging.py         # 로깅 설정
│   ├── service/               # 비즈니스 로직 서비스
│   │   ├── pdf_service.py     # PDF 처리 서비스
│   │   ├── mongodb_service.py # MongoDB 서비스
│   │   ├── langchain_embedding_service.py # LangChain 임베딩 서비스
│   │   └── prompt_service.py  # 프롬프트 관리 서비스
│   ├── utils/                 # 유틸리티 함수들
│   │   ├── document_processor.py # 문서 처리 유틸리티
│   │   └── exceptions.py      # 커스텀 예외 클래스
│   ├── schemas/               # Pydantic 스키마
│   ├── db/                    # 데이터베이스 모델
│   ├── main.py                # FastAPI 애플리케이션 진입점
│   └── Dockerfile             # Crawler 서비스 컨테이너 설정
├── config/                    # 설정 파일들
├── docker-compose.yml         # 전체 서비스 컨테이너 설정
└── README.md                  # 프로젝트 문서
```

## 현재 완성된 기능 (Crawler 모듈)

### PDF 수집 및 처리
- **PDF 다운로드**: URL을 통한 PDF 파일 자동 다운로드
- **OCR 기반 파싱**: GPT를 활용한 고품질 텍스트 추출
- **페이지별 처리**: 대용량 PDF를 페이지별로 병렬 처리
- **Markdown 변환**: 구조화된 Markdown 형태로 변환
- **유틸리티 함수**: 중복 코드 제거를 위한 공통 처리 함수

### 벡터 임베딩 및 검색
- **LangChain 통합**: 최신 LLM 프레임워크 기반 임베딩 처리
- **BAAI/bge-m3 모델**: 고성능 다국어 임베딩 모델 사용
- **Qdrant 벡터 저장**: LangChain VectorStore를 통한 벡터 데이터베이스 연동
- **유사 문서 검색**: 벡터 기반 고성능 유사 문서 검색
- **스마트 청킹**: RecursiveCharacterTextSplitter를 통한 지능적 문서 분할

### 데이터 저장 및 관리
- **MongoDB 저장**: 원본 문서 및 파싱 결과 저장
- **중복 방지**: stock_code 기준 upsert로 중복 데이터 자동 방지
- **깔끔한 데이터 구조**: 불필요한 필드 제거, 통합된 Markdown 내용 저장
- **메타데이터 관리**: 파일 정보, 처리 상태, 통계 정보 포함

### API 엔드포인트
- **공통 API**: 종목별 문서 조회 등 공통 기능
- **PDF 처리 API**: 단일 PDF 다운로드 및 처리
- **종목별 처리 API**: 종목코드 기반 자동 PDF 처리
- **임베딩 API**: 문서 임베딩 저장 및 벡터 검색
- **문서 관리 API**: 조회, 상태 업데이트, 삭제 기능
- **중복 정리 API**: stock_code 기준 중복 문서 자동 정리

## 기술 스택

### 현재 구현된 기술
- **Backend**: FastAPI (Python 3.8+)
- **Database**: MongoDB (비동기 연결), Oracle (기존 데이터)
- **Vector DB**: Qdrant (LangChain VectorStore 통합)
- **AI/ML**: OpenAI GPT API, LangChain, HuggingFaceEmbeddings
- **임베딩**: BAAI/bge-m3 모델
- **PDF 처리**: PyMuPDF (fitz)
- **비동기 처리**: asyncio, aiohttp, aiofiles, motor
- **컨테이너화**: Docker, Docker Compose

### 예정된 기술
- **챗봇**: LangChain 기반 RAG 챗봇
- **웹 인터페이스**: 사용자 친화적 채팅 UI

## API 사용법

### 1. 종목별 PDF 처리 및 임베딩
```bash
# 종목코드로 PDF 처리
POST /stock/process/005930

# 처리된 문서를 임베딩하여 Qdrant에 저장
POST /embedding/store/005930
```

### 2. 벡터 검색
```bash
# 유사 문서 검색
POST /embedding/search
{
  "query": "삼성전자 재무상태",
  "limit": 5
}

# 컬렉션 정보 조회
GET /embedding/collection/info
```

### 3. 문서 관리
```bash
# 공통 문서 조회
GET /common/document/005930

# PDF 문서 목록 조회
GET /pdf/documents?skip=0&limit=10

# 특정 문서 조회
GET /pdf/documents/{document_id}
```

### 4. 중복 문서 정리
```bash
POST /pdf/cleanup-duplicates
```

## 실행 방법

### 1. Docker Compose로 전체 실행
```bash
# 전체 서비스 실행 (MongoDB + Crawler)
docker-compose up -d

# 로그 확인
docker-compose logs -f crawler
```

### 2. 로컬 개발 환경
```bash
# 의존성 설치
pip install -r crawler/requirements.txt

# 환경변수 설정 (.env 파일 생성)
# crawler/.env 파일에 필요한 환경변수들을 설정하세요.
# 자세한 설정 방법은 crawler/README.md를 참고하세요.

# 전체 서비스 실행 (MongoDB + Qdrant + Crawler)
docker-compose up -d

# 또는 개별 실행
docker-compose up -d mongodb qdrant
cd crawler
python main.py
```

### 3. API 문서 확인
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 데이터 구조

### MongoDB 저장 형식
```json
{
  "stock_code": "005930",
  "filename": "005930_report.pdf",
  "original_url": "https://...",
  "file_size": 12345,
  "parsed_content": "## 페이지 1\n\n# 우리단기채권증권투자신탁...",
  "total_pages": 4,
  "successful_pages": 4,
  "failed_pages": [],
  "status": "completed",
  "created_at": "2025-01-05T...",
  "updated_at": "2025-01-05T..."
}
```

## 중복 데이터 관리

### Upsert 기능
- `stock_code`가 동일한 경우 기존 문서를 업데이트
- 새로운 `stock_code`인 경우 새 문서 생성
- `created_at`은 유지, `updated_at`은 갱신

### 중복 정리
- 기존 중복 문서들을 `updated_at` 기준으로 정리
- 최신 문서만 유지하고 나머지 삭제
- API를 통한 일괄 정리 가능

## 다음 단계 (예정)

### 1. RAG 챗봇 개발
- [ ] LangChain 기반 질의 처리 및 검색 로직
- [ ] 컨텍스트 생성 및 프롬프트 최적화
- [ ] 대화 세션 관리
- [ ] 멀티턴 대화 지원

### 2. 웹 인터페이스
- [ ] 사용자 친화적 채팅 UI
- [ ] 문서 관리 대시보드
- [ ] 실시간 처리 상태 모니터링
- [ ] 벡터 검색 결과 시각화

### 3. 성능 최적화
- [ ] 캐싱 시스템 도입 (Redis)
- [ ] 배치 처리 최적화
- [ ] 모니터링 및 알림 시스템

## 보안 고려사항

- **프롬프트 템플릿**: 민감한 프롬프트는 Git에서 제외
- **API 키 관리**: 환경변수를 통한 안전한 키 관리
- **데이터 암호화**: 민감한 데이터 암호화 저장

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

**현재 상태**: Crawler 모듈 완성 (PDF 처리 + 벡터 임베딩)  
**다음 목표**: RAG 챗봇 개발