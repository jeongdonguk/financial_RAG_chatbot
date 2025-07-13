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
    
    async def add_documents_to_vectorstore(self, documents: List[Document]) -> bool:
        """문서들을 벡터 스토어에 추가"""
        try:
            if not documents:
                log.warning("추가할 문서가 없습니다")
                return False
            
            # 벡터 스토어에 문서 추가
            doc_ids = await self.vector_store.aadd_documents(documents)
            
            log.info(f"{len(doc_ids)}개 문서를 벡터 스토어에 추가 완료")
            return True
            
        except Exception as e:
            log.error(f"벡터 스토어에 문서 추가 실패: {str(e)}")
            return False
    
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
            
            # 2. LangChain Document 객체로 변환
            langchain_docs = self.create_langchain_documents(document)
            if not langchain_docs:
                return {
                    "success": False,
                    "message": f"종목코드 {stock_code}의 문서 내용이 비어있습니다",
                    "stock_code": stock_code
                }
            
            # 3. 문서를 청크로 분할
            split_docs = self.split_documents(langchain_docs)
            if not split_docs:
                return {
                    "success": False,
                    "message": f"종목코드 {stock_code}의 문서 분할에 실패했습니다",
                    "stock_code": stock_code
                }
            
            # 4. 벡터 스토어에 추가
            success = await self.add_documents_to_vectorstore(split_docs)
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
        """유사한 문서 검색"""
        try:
            # 벡터 스토어에서 유사 문서 검색
            docs = await self.vector_store.asimilarity_search_with_score(query, k=limit)
            
            # 결과 변환
            results = []
            for doc, score in docs:
                results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score)
                })
            
            log.info(f"LangChain 검색 완료: '{query}' - {len(results)}개 결과")
            return results
            
        except Exception as e:
            log.error(f"LangChain 검색 실패: {str(e)}")
            return []
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """컬렉션 정보 조회"""
        try:
            # Qdrant 클라이언트를 통해 컬렉션 정보 조회
            collection_info = self.qdrant_client.get_collection(self.settings.QDRANT_COLLECTION_NAME)
            
            info = {
                "name": self.settings.QDRANT_COLLECTION_NAME,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status,
                "embedding_model": self.settings.EMBEDDING_MODEL_NAME,
                "chunk_size": self.settings.CHUNK_SIZE,
                "chunk_overlap": self.settings.CHUNK_OVERLAP
            }
            
            log.info("LangChain 컬렉션 정보 조회 완료")
            return info
            
        except Exception as e:
            log.error(f"LangChain 컬렉션 정보 조회 실패: {str(e)}")
            return {}

# 서비스 인스턴스
langchain_embedding_service = LangChainEmbeddingService()
