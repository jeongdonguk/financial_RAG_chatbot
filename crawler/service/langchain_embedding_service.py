from typing import List, Dict, Any, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain.schema import Document
from qdrant_client import QdrantClient
from service.mongodb_service import mongodb_service
from core.config import Settings
from core.logging import get_logger

log = get_logger("langchain_embedding_service")

class LangChainEmbeddingService:
    def __init__(self):
        self.settings = Settings()
        self.qdrant_client = None
        self.embeddings = None
        self.text_splitter = None
        self.vector_store = None
        self._initialize_components()
    
    def _initialize_components(self):
        """LangChain 컴포넌트 초기화"""
        try:
            # Qdrant 클라이언트 초기화
            self.qdrant_client = QdrantClient(
                url=self.settings.QDRANT_URL,
                api_key=self.settings.QDRANT_API_KEY if self.settings.QDRANT_API_KEY else None
            )
            
            # HuggingFace 임베딩 모델 초기화
            self.embeddings = HuggingFaceEmbeddings(
                model_name=self.settings.EMBEDDING_MODEL_NAME,
                model_kwargs={'device': 'cpu'},  # GPU 사용 시 'cuda'로 변경
                encode_kwargs={'normalize_embeddings': True}
            )
            
            # 텍스트 분할기 초기화 (토큰 기반이 아닌 문자 기반)
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.settings.CHUNK_SIZE,
                chunk_overlap=self.settings.CHUNK_OVERLAP,
                length_function=len,  # 문자 수 기준
                separators=["\n\n", "\n", " ", ""]  # 한국어에 적합한 구분자
            )
            
            # 컬렉션 존재 여부 확인 및 생성
            self._ensure_collection_exists()
            
            # Qdrant 벡터 스토어 초기화
            self.vector_store = QdrantVectorStore(
                client=self.qdrant_client,
                collection_name=self.settings.QDRANT_COLLECTION_NAME,
                embedding=self.embeddings
            )
            
            log.info("LangChain 컴포넌트 초기화 완료")
            
        except Exception as e:
            log.error(f"LangChain 컴포넌트 초기화 실패: {str(e)}")
            raise
    
    def _ensure_collection_exists(self):
        """컬렉션이 존재하지 않으면 생성"""
        try:
            # 컬렉션 존재 여부 확인
            collections = self.qdrant_client.get_collections()
            existing_collections = [col.name for col in collections.collections]
            
            if self.settings.QDRANT_COLLECTION_NAME not in existing_collections:
                log.info(f"컬렉션 '{self.settings.QDRANT_COLLECTION_NAME}'이 존재하지 않아 생성합니다")
                
                # 컬렉션 생성 (벡터 설정만)
                from qdrant_client.http.models import VectorParams, Distance
                
                self.qdrant_client.create_collection(
                    collection_name=self.settings.QDRANT_COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=self.settings.EMBEDDING_DIMENSION,
                        distance=Distance.COSINE
                    )
                )
                
                # 텍스트 인덱스 추가
                self._add_text_index_if_needed()
                
                log.info(f"컬렉션 '{self.settings.QDRANT_COLLECTION_NAME}' 생성 완료")
            else:
                log.info(f"컬렉션 '{self.settings.QDRANT_COLLECTION_NAME}'이 이미 존재합니다")
                # 기존 컬렉션에 텍스트 인덱스 추가 시도
                self._add_text_index_if_needed()
                
        except Exception as e:
            log.error(f"컬렉션 확인/생성 실패: {str(e)}")
            raise
    
    def _add_text_index_if_needed(self):
        """기존 컬렉션에 텍스트 인덱스 추가"""
        try:
            from qdrant_client.http.models import PayloadSchemaType
            
            # 현재 컬렉션의 인덱스 정보 확인
            collection_info = self.qdrant_client.get_collection(self.settings.QDRANT_COLLECTION_NAME)
            
            # payload_schema가 비어있거나 page_content 인덱스가 없으면 텍스트 인덱스 추가
            if not collection_info.payload_schema or "page_content" not in collection_info.payload_schema:
                log.info("기존 컬렉션에 텍스트 인덱스 추가 중...")
                
                # page_content 필드에 대한 텍스트 인덱스 추가
                self.qdrant_client.create_payload_index(
                    collection_name=self.settings.QDRANT_COLLECTION_NAME,
                    field_name="page_content",
                    field_schema=PayloadSchemaType.TEXT
                )
                
                log.info("텍스트 인덱스 추가 완료")
            else:
                log.info("텍스트 인덱스가 이미 설정되어 있습니다")
                
        except Exception as e:
            log.warning(f"텍스트 인덱스 추가 실패: {str(e)}")
            # 인덱스 추가 실패해도 계속 진행
    
    async def get_document_by_stock_code(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """종목코드로 MongoDB에서 문서 조회"""
        try:
            document = await mongodb_service.get_document_by_stock_code(stock_code)
            if not document:
                log.warning(f"종목코드 {stock_code}에 해당하는 문서를 찾을 수 없습니다")
                return None
            
            log.info(f"종목코드 {stock_code} 문서 조회 완료")
            return document
            
        except Exception as e:
            log.error(f"문서 조회 실패: {str(e)}")
            return None
    
    def create_langchain_documents(self, document: Dict[str, Any]) -> List[Document]:
        """MongoDB 문서를 LangChain Document 객체로 변환"""
        try:
            stock_code = document.get("stock_code", "")
            parsed_content = document.get("parsed_content", "")
            filename = document.get("filename", "")
            document_id = str(document.get("_id", ""))
            
            if not parsed_content.strip():
                log.warning(f"종목코드 {stock_code}의 문서에 내용이 없습니다")
                return []
            
            # 메타데이터 구성
            metadata = {
                "stock_code": stock_code,
                "filename": filename,
                "document_id": document_id,
                "total_pages": document.get("total_pages", 0),
                "successful_pages": document.get("successful_pages", 0),
                "source": f"mongodb://{stock_code}"
            }
            
            # LangChain Document 생성
            langchain_doc = Document(
                page_content=parsed_content,
                metadata=metadata
            )
            
            log.info(f"종목코드 {stock_code} LangChain 문서 생성 완료")
            return [langchain_doc]
            
        except Exception as e:
            log.error(f"LangChain 문서 생성 실패: {str(e)}")
            return []
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """문서를 청크로 분할"""
        try:
            split_docs = self.text_splitter.split_documents(documents)
            log.info(f"문서 분할 완료: {len(split_docs)}개 청크")
            return split_docs
            
        except Exception as e:
            log.error(f"문서 분할 실패: {str(e)}")
            return []
    
    def add_chunk_numbers(self, documents: List[Document], stock_code: str) -> List[Document]:
        """청크에 청크 넘버 추가"""
        try:
            for i, doc in enumerate(documents, 1):
                # 기존 메타데이터에 청크 넘버 추가
                doc.metadata.update({
                    "chunk_number": i,
                    "stock_code": stock_code,
                    "chunk_id": f"{stock_code}_{i:04d}"  # 4자리 패딩으로 고유 ID 생성
                })
            
            log.info(f"종목코드 {stock_code}: {len(documents)}개 청크에 청크 넘버 추가 완료")
            return documents
            
        except Exception as e:
            log.error(f"청크 넘버 추가 실패: {str(e)}")
            return documents
    
    async def add_documents_to_vectorstore(self, documents: List[Document], deduplicate: bool = True) -> bool:
        """문서들을 벡터 스토어에 추가 (중복 방지 옵션 포함)"""
        try:
            if not documents:
                log.warning("추가할 문서가 없습니다")
                return False
            
            if deduplicate:
                # 중복 제거 후 추가
                documents = await self._deduplicate_documents(documents)
                if not documents:
                    log.info("중복 제거 후 추가할 문서가 없습니다")
                    return True
            
            # 벡터 스토어에 문서 추가
            doc_ids = await self.vector_store.aadd_documents(documents)
            
            log.info(f"{len(doc_ids)}개 청크를 벡터 스토어에 추가 완료")
            return True
            
        except Exception as e:
            log.error(f"벡터 스토어에 문서 추가 실패: {str(e)}")
            return False
    
    async def _deduplicate_documents(self, documents: List[Document]) -> List[Document]:
        """문서 중복 제거 (stock_code + chunk_number 기준)"""
        try:
            seen_chunks = set()
            unique_documents = []
            
            for doc in documents:
                # stock_code와 chunk_number를 조합하여 고유 키 생성
                stock_code = doc.metadata.get("stock_code", "")
                chunk_number = doc.metadata.get("chunk_number", 0)
                chunk_key = f"{stock_code}_{chunk_number}"
                
                if chunk_key not in seen_chunks:
                    seen_chunks.add(chunk_key)
                    unique_documents.append(doc)
                else:
                    log.debug(f"중복 청크 제거: {stock_code} 청크 {chunk_number}")
            
            log.info(f"중복 제거 완료: {len(documents)} -> {len(unique_documents)}개 청크")
            return unique_documents
            
        except Exception as e:
            log.error(f"문서 중복 제거 실패: {str(e)}")
            return documents
    
    async def check_document_exists(self, stock_code: str) -> bool:
        """특정 종목코드의 문서가 벡터 스토어에 존재하는지 확인"""
        try:
            from qdrant_client.http import models
            
            log.info(f"종목코드 {stock_code} 문서 존재 여부 확인 시작")
            log.info(f"사용 중인 컬렉션: {self.settings.QDRANT_COLLECTION_NAME}")
            
            # 먼저 컬렉션의 모든 데이터 구조 확인
            all_data = self.qdrant_client.scroll(
                collection_name=self.settings.QDRANT_COLLECTION_NAME,
                limit=10,
                with_payload=True,
                with_vectors=False
            )
            
            log.info(f"컬렉션에 {len(all_data[0])}개의 포인트가 있습니다")
            
            # 모든 포인트에서 stock_code 관련 필드 찾기
            found_stock_codes = set()
            for point in all_data[0]:
                if 'metadata' in point.payload:
                    metadata = point.payload['metadata']
                    if 'stock_code' in metadata:
                        found_stock_codes.add(metadata['stock_code'])
                        log.info(f"발견된 stock_code: {metadata['stock_code']} (포인트 ID: {point.id})")
                    else:
                        log.info(f"metadata에 stock_code 없음: {list(metadata.keys())}")
                else:
                    log.info(f"payload에 metadata 없음: {list(point.payload.keys())}")
            
            log.info(f"발견된 모든 stock_code: {list(found_stock_codes)}")
            
            # 1. metadata.stock_code로 검색 시도
            search_result = self.qdrant_client.scroll(
                collection_name=self.settings.QDRANT_COLLECTION_NAME,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.stock_code",
                            match=models.MatchValue(value=stock_code)
                        )
                    ]
                ),
                limit=10,
                with_payload=True,
                with_vectors=False
            )
            
            if len(search_result[0]) > 0:
                log.info(f"metadata.stock_code로 {stock_code} 찾음: {len(search_result[0])}개")
                return True
            
            # 2. stock_code로 직접 검색 시도
            search_result2 = self.qdrant_client.scroll(
                collection_name=self.settings.QDRANT_COLLECTION_NAME,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="stock_code",
                            match=models.MatchValue(value=stock_code)
                        )
                    ]
                ),
                limit=10,
                with_payload=True,
                with_vectors=False
            )
            
            if len(search_result2[0]) > 0:
                log.info(f"stock_code로 {stock_code} 찾음: {len(search_result2[0])}개")
                return True
            
            # 3. 문자열로 변환해서 검색 시도
            search_result3 = self.qdrant_client.scroll(
                collection_name=self.settings.QDRANT_COLLECTION_NAME,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.stock_code",
                            match=models.MatchValue(value=str(stock_code))
                        )
                    ]
                ),
                limit=10,
                with_payload=True,
                with_vectors=False
            )
            
            if len(search_result3[0]) > 0:
                log.info(f"문자열 변환 후 metadata.stock_code로 {stock_code} 찾음: {len(search_result3[0])}개")
                return True
            
            # 4. 모든 데이터에서 직접 검색
            for point in all_data[0]:
                if 'metadata' in point.payload:
                    metadata = point.payload['metadata']
                    if metadata.get('stock_code') == stock_code or metadata.get('stock_code') == str(stock_code):
                        log.info(f"직접 검색으로 {stock_code} 찾음: {point.payload}")
                        return True
            
            log.info(f"종목코드 {stock_code} 문서를 찾을 수 없습니다")
            return False
            
        except Exception as e:
            log.error(f"문서 존재 여부 확인 실패: {str(e)}")
            return False
    
    async def delete_documents_by_stock_code(self, stock_code: str) -> int:
        """특정 종목코드의 모든 문서를 벡터 스토어에서 삭제"""
        try:
            from qdrant_client.http import models
            
            log.info(f"종목코드 {stock_code} 문서 삭제 시작")
            log.info(f"사용 중인 컬렉션: {self.settings.QDRANT_COLLECTION_NAME}")
            
            # 먼저 존재 여부 확인
            exists = await self.check_document_exists(stock_code)
            if not exists:
                log.info(f"종목코드 {stock_code}에 해당하는 문서가 없습니다")
                return 0
            
            # 삭제 전 해당 종목코드의 문서 수 확인 (여러 방법으로 시도)
            before_count = 0
            
            # 1. metadata.stock_code로 검색
            search_result = self.qdrant_client.scroll(
                collection_name=self.settings.QDRANT_COLLECTION_NAME,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.stock_code",
                            match=models.MatchValue(value=stock_code)
                        )
                    ]
                ),
                limit=1000,
                with_payload=True,
                with_vectors=False
            )
            before_count = len(search_result[0])
            
            # 2. stock_code로 직접 검색
            if before_count == 0:
                search_result2 = self.qdrant_client.scroll(
                    collection_name=self.settings.QDRANT_COLLECTION_NAME,
                    scroll_filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="stock_code",
                                match=models.MatchValue(value=stock_code)
                            )
                        ]
                    ),
                    limit=1000,
                    with_payload=True,
                    with_vectors=False
                )
                before_count = len(search_result2[0])
            
            # 3. 문자열로 변환해서 검색
            if before_count == 0:
                search_result3 = self.qdrant_client.scroll(
                    collection_name=self.settings.QDRANT_COLLECTION_NAME,
                    scroll_filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="metadata.stock_code",
                                match=models.MatchValue(value=str(stock_code))
                            )
                        ]
                    ),
                    limit=1000,
                    with_payload=True,
                    with_vectors=False
                )
                before_count = len(search_result3[0])
            
            log.info(f"삭제 전 종목코드 {stock_code} 문서 수: {before_count}")
            
            if before_count == 0:
                log.info(f"종목코드 {stock_code}에 해당하는 문서가 없습니다")
                return 0
            
            # 삭제 실행 (여러 방법으로 시도)
            deleted_count = 0
            
            # 1. metadata.stock_code로 삭제 시도
            try:
                delete_result = self.qdrant_client.delete(
                    collection_name=self.settings.QDRANT_COLLECTION_NAME,
                    points_selector=models.FilterSelector(
                        filter=models.Filter(
                            must=[
                                models.FieldCondition(
                                    key="metadata.stock_code",
                                    match=models.MatchValue(value=stock_code)
                                )
                            ]
                        )
                    )
                )
                log.info(f"metadata.stock_code로 삭제 시도: {delete_result.operation_id}")
            except Exception as e:
                log.warning(f"metadata.stock_code로 삭제 실패: {str(e)}")
            
            # 2. stock_code로 직접 삭제 시도
            try:
                delete_result2 = self.qdrant_client.delete(
                    collection_name=self.settings.QDRANT_COLLECTION_NAME,
                    points_selector=models.FilterSelector(
                        filter=models.Filter(
                            must=[
                                models.FieldCondition(
                                    key="stock_code",
                                    match=models.MatchValue(value=stock_code)
                                )
                            ]
                        )
                    )
                )
                log.info(f"stock_code로 삭제 시도: {delete_result2.operation_id}")
            except Exception as e:
                log.warning(f"stock_code로 삭제 실패: {str(e)}")
            
            # 3. 문자열로 변환해서 삭제 시도
            try:
                delete_result3 = self.qdrant_client.delete(
                    collection_name=self.settings.QDRANT_COLLECTION_NAME,
                    points_selector=models.FilterSelector(
                        filter=models.Filter(
                            must=[
                                models.FieldCondition(
                                    key="metadata.stock_code",
                                    match=models.MatchValue(value=str(stock_code))
                                )
                            ]
                        )
                    )
                )
                log.info(f"문자열 변환 후 삭제 시도: {delete_result3.operation_id}")
            except Exception as e:
                log.warning(f"문자열 변환 후 삭제 실패: {str(e)}")
            
            # 삭제 후 확인
            exists_after = await self.check_document_exists(stock_code)
            if not exists_after:
                deleted_count = before_count
                log.info(f"종목코드 {stock_code} 문서 {deleted_count}개 삭제 완료")
            else:
                log.warning(f"삭제 후에도 종목코드 {stock_code} 문서가 여전히 존재합니다")
                deleted_count = 0
            
            return deleted_count
            
        except Exception as e:
            log.error(f"종목코드 {stock_code} 문서 삭제 실패: {str(e)}")
            return 0
    
    async def embed_and_store_document(self, stock_code: str) -> Dict[str, Any]:
        """종목코드로 문서를 조회하여 임베딩하고 Qdrant에 저장"""
        try:
            log.info(f"종목코드 {stock_code} LangChain 임베딩 처리 시작")
            
            # 1. MongoDB에서 문서 조회
            document = await self.get_document_by_stock_code(stock_code)
            if not document:
                return {
                    "success": False,
                    "message": f"종목코드 {stock_code}에 해당하는 문서를 찾을 수 없습니다",
                    "stock_code": stock_code
                }
            
            # 2. success_yn 체크 - Y인 경우만 진행
            success_yn = document.get("success_yn")
            if success_yn != "Y":
                return {
                    "success": False,
                    "message": f"종목코드 {stock_code}의 문서 처리 상태가 완료되지 않았습니다 (success_yn: {success_yn}). 모든 페이지가 성공적으로 처리된 경우에만 벡터화를 진행합니다.",
                    "stock_code": stock_code,
                    "success_yn": success_yn
                }
            
            # 3. 기존 Qdrant 데이터 삭제 (stock_code 기준)
            log.info(f"종목코드 {stock_code}의 기존 Qdrant 데이터 삭제 시작")
            deleted_count = await self.delete_documents_by_stock_code(stock_code)
            log.info(f"종목코드 {stock_code}의 기존 Qdrant 데이터 {deleted_count}개 삭제 완료")
            
            # 4. LangChain Document 객체로 변환
            langchain_docs = self.create_langchain_documents(document)
            if not langchain_docs:
                return {
                    "success": False,
                    "message": f"종목코드 {stock_code}의 문서 내용이 비어있습니다",
                    "stock_code": stock_code
                }
            
            # 5. 문서를 청크로 분할
            split_docs = self.split_documents(langchain_docs)
            if not split_docs:
                return {
                    "success": False,
                    "message": f"종목코드 {stock_code}의 문서 분할에 실패했습니다",
                    "stock_code": stock_code
                }
            
            # 6. 청크에 청크 넘버 추가
            split_docs = self.add_chunk_numbers(split_docs, stock_code)
            
            # 7. 벡터 스토어에 추가 (중복 제거 불필요 - 이미 기존 데이터 삭제됨)
            success = await self.add_documents_to_vectorstore(split_docs, deduplicate=False)
            if not success:
                return {
                    "success": False,
                    "message": f"종목코드 {stock_code}의 임베딩 저장에 실패했습니다",
                    "stock_code": stock_code
                }
            
            log.info(f"종목코드 {stock_code} LangChain 임베딩 처리 완료: {len(split_docs)}개 청크")
            
            return {
                "success": True,
                "message": f"종목코드 {stock_code}의 임베딩이 성공적으로 저장되었습니다",
                "stock_code": stock_code,
                "chunks_count": len(split_docs),
                "document_info": {
                    "filename": document.get("filename", ""),
                    "total_pages": document.get("total_pages", 0),
                    "successful_pages": document.get("successful_pages", 0)
                }
            }
            
        except Exception as e:
            log.error(f"종목코드 {stock_code} LangChain 임베딩 처리 실패: {str(e)}")
            return {
                "success": False,
                "message": f"종목코드 {stock_code} 임베딩 처리 실패: {str(e)}",
                "stock_code": stock_code
            }
    
    async def search_similar_documents(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """유사한 문서 검색 (벡터 검색만)"""
        try:
            # 벡터 스토어에서 유사 문서 검색
            docs = await self.vector_store.asimilarity_search_with_score(query, k=limit)
            
            # 결과 변환
            results = []
            for doc, score in docs:
                results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score),
                    "search_type": "vector"
                })
            
            log.info(f"LangChain 검색 완료: '{query}' - {len(results)}개 결과")
            return results
            
        except Exception as e:
            log.error(f"LangChain 검색 실패: {str(e)}")
            return []
    
    async def search_keywords(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """키워드 기반 문서 검색 (Qdrant Payload 필터링)"""
        try:
            # Qdrant에서 payload 필터링으로 키워드 검색
            from qdrant_client.http import models
            
            # 정규식으로 키워드 검색 (대소문자 무시)
            import re
            keyword_pattern = re.compile(query, re.IGNORECASE)
            
            # Qdrant에서 payload 필터링 검색 (MatchText 대신 Match 사용)
            search_result = self.qdrant_client.scroll(
                collection_name=self.settings.QDRANT_COLLECTION_NAME,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="page_content",
                            match=models.Match(text=query)
                        )
                    ]
                ),
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            
            results = []
            for point in search_result[0]:  # scroll 결과의 첫 번째 요소
                content = point.payload.get("page_content", "")
                if keyword_pattern.search(content):
                    # 키워드 주변 텍스트 추출
                    sentences = content.split('\n')
                    relevant_sentences = [s for s in sentences if keyword_pattern.search(s)]
                    
                    results.append({
                        "content": '\n'.join(relevant_sentences[:3]),
                        "metadata": point.payload.get("metadata", {}),
                        "score": 1.0,  # 키워드 매치 시 최고 점수
                        "search_type": "keyword"
                    })
            
            log.info(f"Qdrant 키워드 검색 완료: '{query}' - {len(results)}개 결과")
            return results
            
        except Exception as e:
            log.error(f"Qdrant 키워드 검색 실패: {str(e)}")
            # HTTPException 대신 일반 예외로 변경 (이 메서드는 HTTP 라우터가 아님)
            raise Exception(f"키워드 검색 실패: {str(e)}")
    
    async def hybrid_search(self, query: str, limit: int = 10, vector_weight: float = 0.7, keyword_weight: float = 0.3) -> List[Dict[str, Any]]:
        """하이브리드 검색 (벡터 + 키워드)"""
        try:
            # 벡터 검색과 키워드 검색을 병렬로 실행
            vector_results = await self.search_similar_documents(query, limit)
            keyword_results = await self.search_keywords(query, limit)
            
            # 결과 통합 및 리랭킹
            combined_results = []
            
            # 벡터 검색 결과 처리
            for result in vector_results:
                result["final_score"] = result["score"] * vector_weight
                combined_results.append(result)
            
            # 키워드 검색 결과 처리 (중복 제거)
            existing_ids = {r["metadata"].get("document_id") for r in combined_results}
            
            for result in keyword_results:
                doc_id = result["metadata"].get("document_id")
                if doc_id not in existing_ids:
                    result["final_score"] = result["score"] * keyword_weight
                    combined_results.append(result)
                else:
                    # 중복된 경우 점수 업데이트
                    for existing in combined_results:
                        if existing["metadata"].get("document_id") == doc_id:
                            existing["final_score"] += result["score"] * keyword_weight
                            existing["search_type"] = "hybrid"
                            break
            
            # 최종 점수로 정렬
            combined_results.sort(key=lambda x: x["final_score"], reverse=True)
            
            # 상위 결과만 반환
            final_results = combined_results[:limit]
            
            log.info(f"하이브리드 검색 완료: '{query}' - {len(final_results)}개 결과")
            return final_results
            
        except Exception as e:
            log.error(f"하이브리드 검색 실패: {str(e)}")
            return []
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """컬렉션 정보 조회"""
        try:
            # Qdrant 클라이언트를 통해 컬렉션 정보 조회
            collection_info = self.qdrant_client.get_collection(self.settings.QDRANT_COLLECTION_NAME)
            
            # 인덱스 정보 조회
            indexes_info = await self.get_indexes_info()
            
            info = {
                "name": self.settings.QDRANT_COLLECTION_NAME,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status,
                "embedding_model": self.settings.EMBEDDING_MODEL_NAME,
                "chunk_size": self.settings.CHUNK_SIZE,
                "chunk_overlap": self.settings.CHUNK_OVERLAP,
                "indexes": indexes_info
            }
            
            log.info("LangChain 컬렉션 정보 조회 완료")
            return info
            
        except Exception as e:
            log.error(f"LangChain 컬렉션 정보 조회 실패: {str(e)}")
            return {}
    
    async def get_indexes_info(self) -> Dict[str, Any]:
        """컬렉션의 인덱스 정보 조회"""
        try:
            collection_info = self.qdrant_client.get_collection(self.settings.QDRANT_COLLECTION_NAME)
            
            indexes_info = {
                "payload_schema": collection_info.payload_schema,
                "has_text_index": False,
                "text_index_fields": []
            }
            
            # payload_schema에서 텍스트 인덱스 확인
            if collection_info.payload_schema:
                for field_name, field_config in collection_info.payload_schema.items():
                    # field_config가 딕셔너리인지 확인
                    if isinstance(field_config, dict):
                        if field_config.get("type") == "text" or field_config.get("data_type") == "text":
                            indexes_info["has_text_index"] = True
                            indexes_info["text_index_fields"].append({
                                "field_name": field_name,
                                "config": field_config
                            })
                    else:
                        # field_config가 객체인 경우 속성으로 접근
                        if hasattr(field_config, 'type') and field_config.type == "text":
                            indexes_info["has_text_index"] = True
                            indexes_info["text_index_fields"].append({
                                "field_name": field_name,
                                "config": {
                                    "type": field_config.type,
                                    "data_type": getattr(field_config, 'data_type', None),
                                    "points": getattr(field_config, 'points', None)
                                }
                            })
                        elif hasattr(field_config, 'data_type') and field_config.data_type == "text":
                            indexes_info["has_text_index"] = True
                            indexes_info["text_index_fields"].append({
                                "field_name": field_name,
                                "config": {
                                    "type": getattr(field_config, 'type', None),
                                    "data_type": field_config.data_type,
                                    "points": getattr(field_config, 'points', None)
                                }
                            })
            
            log.info(f"인덱스 정보 조회 완료: {indexes_info}")
            return indexes_info
            
        except Exception as e:
            log.error(f"인덱스 정보 조회 실패: {str(e)}")
            return {"error": str(e)}
    
    async def test_keyword_search_performance(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """키워드 검색 성능 테스트 및 인덱스 사용 여부 확인"""
        try:
            import time
            
            # 검색 시작 시간
            start_time = time.time()
            
            # 키워드 검색 실행
            results = await self.search_keywords(query, limit)
            
            # 검색 완료 시간
            end_time = time.time()
            search_duration = end_time - start_time
            
            # 인덱스 정보 조회
            indexes_info = await self.get_indexes_info()
            
            performance_info = {
                "query": query,
                "search_duration_ms": round(search_duration * 1000, 2),
                "results_count": len(results),
                "indexes_available": indexes_info.get("has_text_index", False),
                "text_index_fields": indexes_info.get("text_index_fields", []),
                "performance_rating": self._rate_search_performance(search_duration, len(results))
            }
            
            log.info(f"키워드 검색 성능 테스트 완료: {search_duration:.3f}초, {len(results)}개 결과")
            return performance_info
            
        except Exception as e:
            log.error(f"키워드 검색 성능 테스트 실패: {str(e)}")
            return {"error": str(e)}
    
    def _rate_search_performance(self, duration: float, result_count: int) -> str:
        """검색 성능 평가"""
        if duration < 0.1:
            return "excellent"
        elif duration < 0.5:
            return "good"
        elif duration < 1.0:
            return "fair"
        else:
            return "poor"
    
    async def debug_collection_data(self) -> Dict[str, Any]:
        """컬렉션 데이터 구조 디버깅"""
        try:
            log.info("컬렉션 데이터 구조 디버깅 시작")
            
            # 컬렉션 정보 조회
            collection_info = self.qdrant_client.get_collection(self.settings.QDRANT_COLLECTION_NAME)
            
            # 샘플 데이터 조회
            sample_data = self.qdrant_client.scroll(
                collection_name=self.settings.QDRANT_COLLECTION_NAME,
                limit=3,
                with_payload=True,
                with_vectors=False
            )
            
            debug_info = {
                "collection_name": self.settings.QDRANT_COLLECTION_NAME,
                "total_points": collection_info.points_count,
                "total_vectors": collection_info.vectors_count,
                "indexed_vectors": collection_info.indexed_vectors_count,
                "status": collection_info.status,
                "payload_schema": collection_info.payload_schema,
                "sample_data": []
            }
            
            for i, point in enumerate(sample_data[0]):
                sample_info = {
                    "point_id": str(point.id),
                    "payload_keys": list(point.payload.keys()),
                    "metadata": point.payload.get("metadata", {}),
                    "page_content_preview": point.payload.get("page_content", "")[:100] + "..." if point.payload.get("page_content") else ""
                }
                debug_info["sample_data"].append(sample_info)
                log.info(f"샘플 포인트 {i+1}: {sample_info}")
            
            log.info("컬렉션 데이터 구조 디버깅 완료")
            return debug_info
            
        except Exception as e:
            log.error(f"컬렉션 데이터 구조 디버깅 실패: {str(e)}")
            return {"error": str(e)}

# 서비스 인스턴스
langchain_embedding_service = LangChainEmbeddingService()
