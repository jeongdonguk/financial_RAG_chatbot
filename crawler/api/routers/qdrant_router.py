from fastapi import APIRouter, HTTPException, Path, Query, Body
from typing import Optional, Dict, Any, List
from service.langchain_embedding_service import langchain_embedding_service
from schemas.response import BaseResponse
from core.logging import get_logger

log = get_logger("qdrant_router")

router = APIRouter(
    prefix="/qdrant",
    tags=["Qdrant 벡터 검색"]
)

@router.post("/store/{stock_code}", response_model=BaseResponse[Dict[str, Any]], summary="종목별 문서 벡터화 저장")
async def store_document_embedding(
    stock_code: str = Path(..., description="종목코드"),
    deduplicate: bool = Query(True, description="중복 제거 여부")
):
    """
    종목코드를 입력받아 MongoDB에서 해당 문서를 조회하고 벡터화하여 Qdrant에 저장
    
    Args:
        stock_code: 종목코드 (예: "005930")
        deduplicate: 중복 제거 여부
        
    Returns:
        BaseResponse[Dict]: 벡터화 저장 결과
    """
    try:
        log.info(f"종목코드 {stock_code} 벡터화 저장 요청 (중복제거: {deduplicate})")
        
        # 기존 문서 존재 여부 확인
        exists = await langchain_embedding_service.check_document_exists(stock_code)
        if exists and deduplicate:
            log.info(f"종목코드 {stock_code}의 기존 벡터 데이터를 삭제합니다")
            await langchain_embedding_service.delete_documents_by_stock_code(stock_code)
        
        # LangChain 기반 벡터화 처리 및 저장
        result = await langchain_embedding_service.embed_and_store_document(stock_code)
        
        if result["success"]:
            log.info(f"종목코드 {stock_code} 벡터화 저장 완료")
            return BaseResponse(
                success=True,
                message=result["message"],
                data={
                    "stock_code": result["stock_code"],
                    "chunks_count": result["chunks_count"],
                    "document_info": result["document_info"],
                    "deduplicated": deduplicate
                }
            )
        else:
            log.warning(f"종목코드 {stock_code} 벡터화 저장 실패: {result['message']}")
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"종목코드 {stock_code} 벡터화 저장 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"종목코드 {stock_code} 벡터화 저장 실패: {str(e)}"
        )

@router.post("/search/vector", response_model=BaseResponse[List[Dict[str, Any]]], summary="벡터 유사도 검색")
async def search_similar_documents(
    query: str = Body(..., description="검색 쿼리"),
    limit: int = Query(10, ge=1, le=100, description="검색 결과 수")
):
    """
    벡터 유사도를 기반으로 유사한 문서를 검색
    
    Args:
        query: 검색 쿼리
        limit: 검색 결과 수
        
    Returns:
        BaseResponse[List[Dict]]: 검색 결과
    """
    try:
        log.info(f"벡터 유사도 검색 요청: '{query}'")
        
        # LangChain 기반 유사 문서 검색
        results = await langchain_embedding_service.search_similar_documents(query, limit)
        
        log.info(f"벡터 유사도 검색 완료: {len(results)}개 결과")
        
        return BaseResponse(
            success=True,
            message=f"'{query}'에 대한 벡터 유사도 검색이 완료되었습니다",
            data=results
        )
        
    except Exception as e:
        log.error(f"벡터 유사도 검색 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"벡터 유사도 검색 실패: {str(e)}"
        )

@router.post("/search/keywords", response_model=BaseResponse[List[Dict[str, Any]]], summary="키워드 검색")
async def search_keywords(
    query: str = Body(..., description="검색 쿼리"),
    limit: int = Query(10, ge=1, le=100, description="검색 결과 수")
):
    """
    키워드 기반 문서 검색 (텍스트 인덱스 활용)
    
    Args:
        query: 검색 쿼리
        limit: 검색 결과 수
        
    Returns:
        BaseResponse[List[Dict]]: 검색 결과
    """
    try:
        log.info(f"키워드 검색 요청: '{query}'")
        
        # 키워드 기반 검색
        results = await langchain_embedding_service.search_keywords(query, limit)
        
        log.info(f"키워드 검색 완료: {len(results)}개 결과")
        
        return BaseResponse(
            success=True,
            message=f"'{query}'에 대한 키워드 검색이 완료되었습니다",
            data=results
        )
        
    except Exception as e:
        log.error(f"키워드 검색 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"키워드 검색 실패: {str(e)}"
        )

@router.post("/search/hybrid", response_model=BaseResponse[List[Dict[str, Any]]], summary="하이브리드 검색")
async def search_hybrid(
    query: str = Body(..., description="검색 쿼리"),
    limit: int = Query(10, ge=1, le=100, description="검색 결과 수"),
    vector_weight: float = Query(0.7, ge=0.0, le=1.0, description="벡터 검색 가중치"),
    keyword_weight: float = Query(0.3, ge=0.0, le=1.0, description="키워드 검색 가중치")
):
    """
    하이브리드 검색 (벡터 + 키워드)
    
    Args:
        query: 검색 쿼리
        limit: 검색 결과 수
        vector_weight: 벡터 검색 가중치 (0.0-1.0)
        keyword_weight: 키워드 검색 가중치 (0.0-1.0)
        
    Returns:
        BaseResponse[List[Dict]]: 검색 결과
    """
    try:
        log.info(f"하이브리드 검색 요청: '{query}' (벡터:{vector_weight}, 키워드:{keyword_weight})")
        
        # 하이브리드 검색
        results = await langchain_embedding_service.hybrid_search(
            query, limit, vector_weight, keyword_weight
        )
        
        log.info(f"하이브리드 검색 완료: {len(results)}개 결과")
        
        return BaseResponse(
            success=True,
            message=f"'{query}'에 대한 하이브리드 검색이 완료되었습니다",
            data=results
        )
        
    except Exception as e:
        log.error(f"하이브리드 검색 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"하이브리드 검색 실패: {str(e)}"
        )

@router.get("/collection/info", response_model=BaseResponse[Dict[str, Any]], summary="컬렉션 정보 조회")
async def get_collection_info():
    """
    Qdrant 컬렉션 정보 조회
    
    Returns:
        BaseResponse[Dict]: 컬렉션 정보
    """
    try:
        log.info("컬렉션 정보 조회 요청")
        
        # LangChain 기반 컬렉션 정보 조회
        info = await langchain_embedding_service.get_collection_info()
        
        log.info("컬렉션 정보 조회 완료")
        
        return BaseResponse(
            success=True,
            message="컬렉션 정보 조회가 완료되었습니다",
            data=info
        )
        
    except Exception as e:
        log.error(f"컬렉션 정보 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"컬렉션 정보 조회 실패: {str(e)}"
        )

@router.get("/indexes/info", response_model=BaseResponse[Dict[str, Any]], summary="인덱스 정보 조회")
async def get_indexes_info():
    """
    Qdrant 컬렉션의 인덱스 정보 조회
    
    Returns:
        BaseResponse[Dict]: 인덱스 정보
    """
    try:
        log.info("인덱스 정보 조회 요청")
        
        # 인덱스 정보 조회
        indexes_info = await langchain_embedding_service.get_indexes_info()
        
        log.info("인덱스 정보 조회 완료")
        
        return BaseResponse(
            success=True,
            message="인덱스 정보 조회가 완료되었습니다",
            data=indexes_info
        )
        
    except Exception as e:
        log.error(f"인덱스 정보 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"인덱스 정보 조회 실패: {str(e)}"
        )

@router.post("/test-performance", response_model=BaseResponse[Dict[str, Any]], summary="키워드 검색 성능 테스트")
async def test_keyword_search_performance(
    query: str = Body(..., description="테스트할 검색 쿼리"),
    limit: int = Query(10, ge=1, le=100, description="검색 결과 수")
):
    """
    키워드 검색 성능 테스트 및 인덱스 사용 여부 확인
    
    Args:
        query: 테스트할 검색 쿼리
        limit: 검색 결과 수
        
    Returns:
        BaseResponse[Dict]: 성능 테스트 결과
    """
    try:
        log.info(f"키워드 검색 성능 테스트 요청: '{query}'")
        
        # 성능 테스트 실행
        performance_info = await langchain_embedding_service.test_keyword_search_performance(query, limit)
        
        log.info(f"키워드 검색 성능 테스트 완료: {performance_info.get('search_duration_ms', 0)}ms")
        
        return BaseResponse(
            success=True,
            message=f"'{query}'에 대한 성능 테스트가 완료되었습니다",
            data=performance_info
        )
        
    except Exception as e:
        log.error(f"키워드 검색 성능 테스트 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"키워드 검색 성능 테스트 실패: {str(e)}"
        )

@router.get("/documents/{stock_code}/exists", response_model=BaseResponse[Dict[str, Any]], summary="종목코드 문서 존재 여부 확인")
async def check_document_exists(
    stock_code: str = Path(..., description="종목코드")
):
    """
    특정 종목코드의 문서가 Qdrant에 존재하는지 확인
    
    Args:
        stock_code: 종목코드
        
    Returns:
        BaseResponse[Dict]: 존재 여부
    """
    try:
        log.info(f"종목코드 {stock_code} 문서 존재 여부 확인 요청")
        
        exists = await langchain_embedding_service.check_document_exists(stock_code)
        
        log.info(f"종목코드 {stock_code} 문서 존재 여부: {exists}")
        
        return BaseResponse(
            success=True,
            message=f"종목코드 {stock_code} 문서 존재 여부 확인 완료",
            data={"stock_code": stock_code, "exists": exists}
        )
        
    except Exception as e:
        log.error(f"종목코드 {stock_code} 문서 존재 여부 확인 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"종목코드 {stock_code} 문서 존재 여부 확인 실패: {str(e)}"
        )

@router.delete("/documents/{stock_code}", response_model=BaseResponse[Dict[str, Any]], summary="종목코드별 문서 삭제")
async def delete_documents_by_stock_code(
    stock_code: str = Path(..., description="종목코드")
):
    """
    특정 종목코드의 모든 문서를 Qdrant에서 삭제
    
    Args:
        stock_code: 종목코드
        
    Returns:
        BaseResponse[Dict]: 삭제 결과
    """
    try:
        log.info(f"종목코드 {stock_code} 문서 삭제 요청")
        
        deleted_count = await langchain_embedding_service.delete_documents_by_stock_code(stock_code)
        
        log.info(f"종목코드 {stock_code} 문서 {deleted_count}개 삭제 완료")
        
        return BaseResponse(
            success=True,
            message=f"종목코드 {stock_code}의 {deleted_count}개 문서가 삭제되었습니다",
            data={"stock_code": stock_code, "deleted_count": deleted_count}
        )
        
    except Exception as e:
        log.error(f"종목코드 {stock_code} 문서 삭제 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"종목코드 {stock_code} 문서 삭제 실패: {str(e)}"
        )

@router.get("/debug/collection", response_model=BaseResponse[Dict[str, Any]], summary="컬렉션 데이터 구조 디버깅")
async def debug_collection_data():
    """
    Qdrant 컬렉션의 데이터 구조를 디버깅하여 확인
    
    Returns:
        BaseResponse[Dict]: 디버깅 정보
    """
    try:
        log.info("컬렉션 데이터 구조 디버깅 요청")
        
        debug_info = await langchain_embedding_service.debug_collection_data()
        
        log.info("컬렉션 데이터 구조 디버깅 완료")
        
        return BaseResponse(
            success=True,
            message="컬렉션 데이터 구조 디버깅이 완료되었습니다",
            data=debug_info
        )
        
    except Exception as e:
        log.error(f"컬렉션 데이터 구조 디버깅 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"컬렉션 데이터 구조 디버깅 실패: {str(e)}"
        )
