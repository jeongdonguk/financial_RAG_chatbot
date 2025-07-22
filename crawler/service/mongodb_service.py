from typing import Dict, Any, List, Optional
from datetime import datetime
from bson import ObjectId
from core.mongodb import get_database
from core.logging import get_logger
from utils.document_processor import combine_page_results

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
        combined_markdown = combine_page_results(page_results)
        
        # 깔끔한 문서 구조
        document = {
            "filename": pdf_data["filename"],
            "original_url": pdf_data["original_url"],
            "file_size": pdf_data["file_size"],
            "content_type": pdf_data["content_type"],
            "download_time": pdf_data["download_time"],
            "stock_code": pdf_data.get("stock_code"),
            "parsed_content": combined_markdown,  # 합쳐진 Markdown 내용
            "total_pages": gpt_processing_result.get("total_pages", 0),
            "successful_pages": gpt_processing_result.get("successful_pages", 0),
            "failed_pages": gpt_processing_result.get("failed_pages", []),
            "prompt_type": metadata.get("prompt_type", "default"),
            "status": "processed",
            "updated_at": datetime.now()
        }
        
        # stock_code가 있으면 upsert, 없으면 일반 insert
        if pdf_data.get("stock_code"):
            filter_query = {"stock_code": pdf_data["stock_code"]}
            update_data = {
                "$set": document,
                "$setOnInsert": {"created_at": datetime.now()}
            }
            
            result = await collection.update_one(
                filter_query,
                update_data,
                upsert=True
            )
            
            if result.upserted_id:
                return str(result.upserted_id)
            else:
                existing_doc = await collection.find_one(filter_query)
                return str(existing_doc["_id"])
        else:
            # stock_code가 없으면 일반 insert
            document["created_at"] = datetime.now()
            result = await collection.insert_one(document)
            return str(result.inserted_id)
    
    async def save_processed_document(self, stock_code: str, gpt_result: Dict[str, Any], pdf_metadata: Dict[str, Any]) -> str:
        """처리된 문서를 MongoDB에 저장 (stock_code 기준 upsert)"""
        collection = await self._get_collection()
        if collection is None:
            log.warning("MongoDB가 연결되지 않아 문서를 저장할 수 없습니다.")
            return "mock_document_id"
        
        # 페이지별 결과를 합쳐서 하나의 Markdown으로 만들기
        page_results = gpt_result.get("page_results", [])
        combined_markdown = combine_page_results(page_results)
        
        # 깔끔한 문서 구조
        document = {
            "stock_code": stock_code,
            "filename": pdf_metadata.get("filename", f"{stock_code}_report.pdf"),
            "original_url": pdf_metadata.get("original_url"),
            "file_size": pdf_metadata.get("file_size", 0),
            "content_type": pdf_metadata.get("content_type", "application/pdf"),
            "download_time": pdf_metadata.get("download_time", datetime.now()),
            "parsed_content": combined_markdown,  # 합쳐진 Markdown 내용
            "total_pages": gpt_result.get("total_pages", 0),
            "successful_pages": gpt_result.get("successful_pages", 0),
            "failed_pages": gpt_result.get("failed_pages", []),
            "status": "completed",
            "updated_at": datetime.now()
        }
        
        # stock_code 기준으로 upsert (기존 문서가 있으면 업데이트, 없으면 삽입)
        filter_query = {"stock_code": stock_code}
        update_data = {
            "$set": document,
            "$setOnInsert": {"created_at": datetime.now()}  # 새로 생성될 때만 created_at 설정
        }
        
        result = await collection.update_one(
            filter_query,
            update_data,
            upsert=True
        )
        
        # 업데이트된 문서의 ID 반환
        if result.upserted_id:
            return str(result.upserted_id)
        else:
            # 기존 문서가 업데이트된 경우, 해당 문서의 ID를 조회해서 반환
            existing_doc = await collection.find_one(filter_query)
            return str(existing_doc["_id"])
    
    
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
        
        # 파일 관련 정리 (GridFS 사용하지 않음)
        
        # 문서 삭제
        collection = await self._get_collection()
        if collection is None:
            return False
        result = await collection.delete_one({"_id": ObjectId(document_id)})
        return result.deleted_count > 0
    

    async def cleanup_duplicate_documents(self) -> Dict[str, int]:
        """중복 문서 정리 (stock_code 기준)"""
        collection = await self._get_collection()
        if collection is None:
            return {"error": "MongoDB 연결 실패"}
        
        # stock_code별로 그룹화하여 중복 확인
        pipeline = [
            {"$match": {"stock_code": {"$exists": True, "$ne": None}}},
            {"$group": {
                "_id": "$stock_code",
                "count": {"$sum": 1},
                "docs": {"$push": {"id": "$_id", "updated_at": "$updated_at"}}
            }},
            {"$match": {"count": {"$gt": 1}}}
        ]
        
        duplicates = await collection.aggregate(pipeline).to_list(length=None)
        
        total_removed = 0
        for duplicate in duplicates:
            stock_code = duplicate["_id"]
            docs = duplicate["docs"]
            
            # updated_at 기준으로 최신 문서만 남기고 나머지 삭제
            docs.sort(key=lambda x: x["updated_at"], reverse=True)
            docs_to_remove = docs[1:]  # 첫 번째(최신) 제외한 나머지
            
            for doc in docs_to_remove:
                await collection.delete_one({"_id": doc["id"]})
                total_removed += 1
            
            log.info(f"종목코드 {stock_code}: {len(docs_to_remove)}개 중복 문서 삭제")
        
        return {
            "duplicate_stock_codes": len(duplicates),
            "total_removed": total_removed
        }

    async def get_document_by_stock_code(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """종목코드로 문서 조회"""
        collection = await self._get_collection()
        if collection is None:
            return None
        
        document = await collection.find_one({"stock_code": stock_code})
        if document:
            document["_id"] = str(document["_id"])
        return document

# 서비스 인스턴스
mongodb_service = MongoDBService()


