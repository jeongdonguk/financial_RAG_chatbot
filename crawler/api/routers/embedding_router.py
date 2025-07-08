from fastapi import APIRouter, HTTPException, Path, Query, Body
from typing import Optional, Dict, Any, List
from service.langchain_embedding_service import langchain_embedding_service
from schemas.response import BaseResponse
from core.logging import get_logger

log = get_logger("embedding_router")

router = APIRouter(
    prefix="/embedding",
    tags=["임베딩 및 벡터 검색"]
)

@router.post("/store/{stock_code}", response_model=BaseResponse[Dict[str, Any]], summary="종목별 문서 임베딩 저장")
async def store_document_embedding(
    stock_code: str = Path(..., description="종목코드")
):
    """
    종목코드를 입력받아 MongoDB에서 해당 문서를 조회하고 BAAI/bge-m3로 임베딩하여 Qdrant에 저장
    
    Args:
        stock_code: 종목코드 (예: "005930")
        
    Returns:
        BaseResponse[Dict]: 임베딩 저장 결과
    """
    try:
        log.info(f"종목코드 {stock_code} 임베딩 저장 요청")
        
        # LangChain 기반 임베딩 처리 및 저장
        result = await langchain_embedding_service.embed_and_store_document(stock_code)
        
        if result["success"]:
            log.info(f"종목코드 {stock_code} 임베딩 저장 완료")
            return BaseResponse(
                success=True,
                message=result["message"],
                data={
                    "stock_code": result["stock_code"],
                    "chunks_count": result["chunks_count"],
                    "document_info": result["document_info"]
                }
            )
        else:
            log.warning(f"종목코드 {stock_code} 임베딩 저장 실패: {result['message']}")
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"종목코드 {stock_code} 임베딩 저장 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"종목코드 {stock_code} 임베딩 저장 실패: {str(e)}"
        )

@router.post("/search", response_model=BaseResponse[List[Dict[str, Any]]], summary="유사 문서 검색")
async def search_similar_documents(
    query: str = Body(..., description="검색 쿼리"),
    limit: int = Query(10, ge=1, le=100, description="검색 결과 수")
):
    """
    쿼리를 입력받아 유사한 문서를 검색
    
    Args:
        query: 검색 쿼리
        limit: 검색 결과 수
        
    Returns:
        BaseResponse[List[Dict]]: 검색 결과
    """
    try:
        log.info(f"유사 문서 검색 요청: '{query}'")
        
        # LangChain 기반 유사 문서 검색
        results = await langchain_embedding_service.search_similar_documents(query, limit)
        
        log.info(f"검색 완료: {len(results)}개 결과")
        
        return BaseResponse(
            success=True,
            message=f"'{query}'에 대한 검색이 완료되었습니다",
            data=results
        )
        
    except Exception as e:
        log.error(f"유사 문서 검색 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"유사 문서 검색 실패: {str(e)}"
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

@router.get("/document/{stock_code}", response_model=BaseResponse[Dict[str, Any]], summary="종목별 문서 조회")
async def get_document_by_stock_code(
    stock_code: str = Path(..., description="종목코드")
):
    """
    종목코드로 MongoDB에서 문서 조회
    
    Args:
        stock_code: 종목코드
        
    Returns:
        BaseResponse[Dict]: 문서 정보
    """
    try:
        log.info(f"종목코드 {stock_code} 문서 조회 요청")
        
        # LangChain 기반 문서 조회
        document = await langchain_embedding_service.get_document_by_stock_code(stock_code)
        
        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"종목코드 {stock_code}에 해당하는 문서를 찾을 수 없습니다"
            )
        
        log.info(f"종목코드 {stock_code} 문서 조회 완료")
        
        return BaseResponse(
            success=True,
            message=f"종목코드 {stock_code}의 문서 조회가 완료되었습니다",
            data=document
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"종목코드 {stock_code} 문서 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"종목코드 {stock_code} 문서 조회 실패: {str(e)}"
        )
