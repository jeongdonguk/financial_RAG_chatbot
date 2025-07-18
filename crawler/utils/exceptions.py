"""
커스텀 예외 클래스들
"""
from typing import Optional

class DocumentProcessingError(Exception):
    """문서 처리 관련 오류"""
    def __init__(self, message: str, stock_code: Optional[str] = None):
        self.stock_code = stock_code
        super().__init__(message)

class EmbeddingError(Exception):
    """임베딩 처리 관련 오류"""
    def __init__(self, message: str, stock_code: Optional[str] = None):
        self.stock_code = stock_code
        super().__init__(message)

class VectorStoreError(Exception):
    """벡터 스토어 관련 오류"""
    def __init__(self, message: str, collection_name: Optional[str] = None):
        self.collection_name = collection_name
        super().__init__(message)

class PDFDownloadError(Exception):
    """PDF 다운로드 관련 오류"""
    def __init__(self, message: str, url: Optional[str] = None):
        self.url = url
        super().__init__(message)
