# Fund RAG Chatbot

PDF 기반 펀드 문서 분석 및 질의응답을 위한 RAG(Retrieval-Augmented Generation) 챗봇 시스템

## 🎯 프로젝트 개요

이 프로젝트는 펀드 관련 PDF 문서를 수집, 분석, 저장하여 사용자가 자연어로 질문할 수 있는 RAG 챗봇을 구축하는 것을 목표로 합니다.

### 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PDF Crawler   │───▶│   MongoDB       │───▶│   Qdrant        │───▶│   RAG Chatbot   │
│   (데이터 수집)  │    │   (문서 저장)   │    │   (벡터 저장)   │    │   (질의응답)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📁 프로젝트 구조

```
fund_RAG_chatbot/
├── crawler/                    # 데이터 수집 모듈 (현재 완성)
│   ├── api/                   # FastAPI 라우터
│   │   └── routers/           # PDF 및 종목별 처리 API
│   ├── core/                  # 핵심 설정 및 연결 관리
│   ├── service/               # 비즈니스 로직 서비스
│   ├── schemas/               # API 응답 스키마
│   └── main.py               # FastAPI 애플리케이션 진입점
├── vector_store/              # Qdrant 벡터 저장소 (예정)
├── chatbot/                   # RAG 챗봇 모듈 (예정)
├── docker-compose.yml         # MongoDB 컨테이너 설정
└── README.md                  # 프로젝트 문서
```

## 🚀 현재 완성된 기능 (Crawler 모듈)

### ✅ PDF 수집 및 처리
- **PDF 다운로드**: URL을 통한 PDF 파일 자동 다운로드
- **OCR 기반 파싱**: GPT를 활용한 고품질 텍스트 추출
- **페이지별 처리**: 대용량 PDF를 페이지별로 병렬 처리
- **Markdown 변환**: 구조화된 Markdown 형태로 변환

### ✅ 데이터 저장
- **MongoDB 저장**: 원본 문서 및 파싱 결과 저장
- **깔끔한 데이터 구조**: 불필요한 필드 제거, 통합된 Markdown 내용 저장
- **메타데이터 관리**: 파일 정보, 처리 상태, 통계 정보 포함

### ✅ API 엔드포인트
- **PDF 처리 API**: 단일 PDF 다운로드 및 처리
- **종목별 처리 API**: 종목코드 기반 자동 PDF 처리
- **문서 관리 API**: 조회, 상태 업데이트, 삭제 기능

## 🛠 기술 스택

### 현재 구현된 기술
- **Backend**: FastAPI (Python 3.8+)
- **Database**: MongoDB (비동기 연결)
- **AI/ML**: OpenAI GPT API
- **PDF 처리**: PyMuPDF (fitz)
- **비동기 처리**: asyncio, aiohttp, aiofiles

### 예정된 기술
- **벡터 DB**: Qdrant
- **임베딩**: OpenAI Embeddings API
- **챗봇**: LangChain 또는 LlamaIndex

## 📋 API 사용법

### 1. PDF 다운로드 및 처리
```bash
POST /pdf/download
{
  "url": "https://example.com/fund-report.pdf",
  "prompt_type": "fund_document"
}
```

### 2. 종목별 PDF 처리
```bash
POST /stock/process/005930
{
  "prompt_type": "fund_document"
}
```

### 3. 저장된 문서 조회
```bash
GET /pdf/documents?skip=0&limit=10
GET /pdf/documents/{document_id}
```

## 🚀 실행 방법

### 1. 환경 설정
```bash
# 의존성 설치
pip install -r crawler/requirements.txt

# 환경변수 설정
export OPENAI_API_KEY="your-api-key"
export MONGODB_URL="mongodb://localhost:27017"
```

### 2. MongoDB 실행
```bash
# Docker Compose로 MongoDB 실행
docker-compose up -d
```

### 3. 애플리케이션 실행
```bash
# Crawler 서버 실행
cd crawler
python main.py
```

### 4. API 문서 확인
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📊 데이터 구조

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

## 🔄 다음 단계 (예정)

### 1. 벡터 저장소 구축
- [ ] Qdrant 클러스터 설정
- [ ] 문서 임베딩 생성 및 저장
- [ ] 벡터 검색 인덱스 구축

### 2. RAG 챗봇 개발
- [ ] 질의 처리 및 검색 로직
- [ ] 컨텍스트 생성 및 프롬프트 최적화
- [ ] 대화 세션 관리

### 3. 웹 인터페이스
- [ ] 사용자 친화적 채팅 UI
- [ ] 문서 관리 대시보드
- [ ] 실시간 처리 상태 모니터링

## 🔒 보안 고려사항

- **프롬프트 템플릿**: 민감한 프롬프트는 Git에서 제외
- **API 키 관리**: 환경변수를 통한 안전한 키 관리
- **데이터 암호화**: 민감한 데이터 암호화 저장

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

**현재 상태**: Crawler 모듈 완성 ✅  
**다음 목표**: Qdrant 벡터 저장소 구축 🎯
