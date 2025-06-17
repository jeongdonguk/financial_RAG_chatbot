from pydantic import BaseModel, HttpUrl
from typing import Any, Optional, Generic, TypeVar, List
from datetime import datetime

# 제네릭 타입 변수
T = TypeVar('T')

class BaseResponse(BaseModel, Generic[T]):
    """기본 응답 스키마"""
    success: bool
    message: str
    data: Optional[T] = None
    timestamp: datetime = datetime.now()
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }



class CountResponse(BaseModel):
    """카운트 응답 스키마"""
    count: int




class PDFDownloadRequest(BaseModel):
    """PDF 다운로드 요청 스키마"""
    url: HttpUrl
    filename: Optional[str] = None

class PDFMetadata(BaseModel):
    """PDF 메타데이터 스키마 (깔끔한 구조)"""
    parsed_content: str = ""  # 합쳐진 Markdown 내용
    total_pages: int = 0
    successful_pages: int = 0
    failed_pages: List[int] = []
    prompt_type: str = "default"

class PDFDocument(BaseModel):
    """PDF 문서 스키마"""
    id: str
    filename: str
    original_url: str
    file_size: int
    content_type: str
    download_time: datetime
    metadata: PDFMetadata
    status: str
    created_at: datetime
    updated_at: datetime

class PDFDocumentList(BaseModel):
    """PDF 문서 목록 스키마"""
    documents: List[PDFDocument]
    total_count: int
    skip: int
    limit: int
