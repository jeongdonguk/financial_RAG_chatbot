from typing import Dict, Any, List, Optional
from datetime import datetime
from bson import ObjectId
from core.mongodb import get_database
from core.logging import get_logger

log = get_logger("mongodb_service")

class MongoDBService:
    def __init__(self, collection_name: str = None):
        self.collection_name = collection_name or "pdf_documents"
    
    async def _get_collection(self):
        """컬렉션 가져오기"""
        try:
            database = get_database()
            return database[self.collection_name]
        except Exception as e:
            log.warning(f"MongoDB 연결 실패: {str(e)}")
            return None

    async def save_pdf_document(self, pdf_data: Dict[str, Any]) -> str:
        """PDF 문서를 MongoDB에 저장 (깔끔한 데이터만 저장)"""
        collection = await self._get_collection()
        if collection is None:
            log.warning("MongoDB가 연결되지 않아 문서를 저장할 수 없습니다.")
            return "mock_document_id"
        
        # 메타데이터에서 GPT 처리 결과 추출
        metadata = pdf_data.get("metadata", {})
        gpt_processing_result = metadata.get("gpt_processing_result", {})
        
        # 페이지별 결과를 합쳐서 하나의 Markdown으로 만들기
        page_results = gpt_processing_result.get("page_results", [])
        combined_markdown = []
        
        for page_result in page_results:
            gpt_response = page_result.get("gpt_response", {})
            page_number = page_result.get("page_number", 0)
            
            # raw_response가 있으면 그것을 사용
            if isinstance(gpt_response, dict) and "raw_response" in gpt_response:
                content = gpt_response["raw_response"]
            elif isinstance(gpt_response, str):
                content = gpt_response
            else:
                content = str(gpt_response)
            
            # 페이지 헤더와 함께 추가
            combined_markdown.append(f"## 페이지 {page_number}\n\n{content}\n\n")
        
        # 깔끔한 문서 구조
        document = {
            "filename": pdf_data["filename"],
            "original_url": pdf_data["original_url"],
            "file_size": pdf_data["file_size"],
            "content_type": pdf_data["content_type"],
            "download_time": pdf_data["download_time"],
            "stock_code": pdf_data.get("stock_code"),
            "parsed_content": "\n".join(combined_markdown),  # 합쳐진 Markdown 내용
            "total_pages": gpt_processing_result.get("total_pages", 0),
            "successful_pages": gpt_processing_result.get("successful_pages", 0),
            "failed_pages": gpt_processing_result.get("failed_pages", []),
            "prompt_type": metadata.get("prompt_type", "default"),
            "status": "processed",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        # 문서 저장
        result = await collection.insert_one(document)
        return str(result.inserted_id)
    
    async def save_processed_document(self, stock_code: str, gpt_result: Dict[str, Any], pdf_metadata: Dict[str, Any]) -> str:
        """처리된 문서를 MongoDB에 저장 (깔끔한 데이터만 저장)"""
        collection = await self._get_collection()
        if collection is None:
            log.warning("MongoDB가 연결되지 않아 문서를 저장할 수 없습니다.")
            return "mock_document_id"
        
        # 페이지별 결과를 합쳐서 하나의 Markdown으로 만들기
        page_results = gpt_result.get("page_results", [])
        combined_markdown = []
        
        for page_result in page_results:
            gpt_response = page_result.get("gpt_response", {})
            page_number = page_result.get("page_number", 0)
            
            # raw_response가 있으면 그것을 사용
            if isinstance(gpt_response, dict) and "raw_response" in gpt_response:
                content = gpt_response["raw_response"]
            elif isinstance(gpt_response, str):
                content = gpt_response
            else:
                content = str(gpt_response)
            
            # 페이지 헤더와 함께 추가
            combined_markdown.append(f"## 페이지 {page_number}\n\n{content}\n\n")
        
        # 깔끔한 문서 구조
        document = {
            "stock_code": stock_code,
            "filename": pdf_metadata.get("filename", f"{stock_code}_report.pdf"),
            "original_url": pdf_metadata.get("original_url"),
            "file_size": pdf_metadata.get("file_size", 0),
            "content_type": pdf_metadata.get("content_type", "application/pdf"),
            "download_time": pdf_metadata.get("download_time", datetime.now()),
            "parsed_content": "\n".join(combined_markdown),  # 합쳐진 Markdown 내용
            "total_pages": gpt_result.get("total_pages", 0),
            "successful_pages": gpt_result.get("successful_pages", 0),
            "failed_pages": gpt_result.get("failed_pages", []),
            "status": "completed",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        # 문서 저장
        result = await collection.insert_one(document)
        return str(result.inserted_id)
    
    async def _read_file_content(self, file_path: str) -> bytes:
        """파일 내용을 읽어서 반환"""
        import aiofiles
        async with aiofiles.open(file_path, 'rb') as f:
            content = await f.read()
        return content
    
    async def _save_file_to_gridfs(self, file_path: str, filename: str) -> str:
        """파일을 GridFS에 저장 (사용하지 않음)"""
        # GridFS를 사용하지 않고 파일 내용을 직접 저장
        return "no_gridfs"
    
    async def get_pdf_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """PDF 문서 조회"""
        collection = await self._get_collection()
        if collection is None:
            return None
        document = await collection.find_one({"_id": ObjectId(document_id)})
        if document:
            document["_id"] = str(document["_id"])
        return document
    
    async def list_pdf_documents(
        self, 
        skip: int = 0, 
        limit: int = 10,
        status: str = None
    ) -> List[Dict[str, Any]]:
        """PDF 문서 목록 조회"""
        collection = await self._get_collection()
        if collection is None:
            return []
        
        filter_query = {}
        if status:
            filter_query["status"] = status
        
        cursor = collection.find(filter_query).skip(skip).limit(limit).sort("created_at", -1)
        documents = await cursor.to_list(length=limit)
        
        # ObjectId를 문자열로 변환
        for doc in documents:
            doc["_id"] = str(doc["_id"])
        
        return documents
    
    async def update_document_status(self, document_id: str, status: str) -> bool:
        """문서 상태 업데이트"""
        collection = await self._get_collection()
        if collection is None:
            return False
        result = await collection.update_one(
            {"_id": ObjectId(document_id)},
            {
                "$set": {
                    "status": status,
                    "updated_at": datetime.now()
                }
            }
        )
        return result.modified_count > 0
    
    async def delete_document(self, document_id: str) -> bool:
        """문서 삭제"""
        # 먼저 문서 정보 조회
        document = await self.get_pdf_document(document_id)
        if not document:
            return False
        
        # GridFS에서 파일 삭제
        if "file_id" in document:
            await self._delete_file_from_gridfs(document["file_id"])
        
        # 문서 삭제
        collection = await self._get_collection()
        if collection is None:
            return False
        result = await collection.delete_one({"_id": ObjectId(document_id)})
        return result.deleted_count > 0
    
    async def _download_file_from_gridfs(self, file_id: str) -> bytes:
        """GridFS에서 파일 다운로드 (사용하지 않음)"""
        # GridFS를 사용하지 않음
        return b""

    async def _delete_file_from_gridfs(self, file_id: str) -> bool:
        """GridFS에서 파일 삭제 (사용하지 않음)"""
        # GridFS를 사용하지 않음
        return True

# 서비스 인스턴스
mongodb_service = MongoDBService()


