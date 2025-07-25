"""
공통 API 엔드포인트들
"""
from fastapi import APIRouter, HTTPException, Path
from typing import Dict, Any
from service.mongodb_service import mongodb_service
from service.langchain_embedding_service import langchain_embedding_service
from schemas.response import BaseResponse
from core.logging import get_logger

log = get_logger("common_router")

router = APIRouter(
    prefix="/common",
    tags=["공통 API"]
)

@router.get("/document/{stock_code}", response_model=BaseResponse[Dict[str, Any]], summary="종목별 문서 조회")
async def get_document_by_stock_code(
    stock_code: str = Path(..., description="종목코드")
):
    """
    종목코드로 MongoDB에서 문서 조회 (공통 엔드포인트)
    
    Args:
        stock_code: 종목코드
        
    Returns:
        BaseResponse[Dict]: 문서 정보
    """
    try:
        log.info(f"종목코드 {stock_code} 문서 조회 요청")
        
        # MongoDB에서 문서 조회
        document = await mongodb_service.get_document_by_stock_code(stock_code)
        
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
