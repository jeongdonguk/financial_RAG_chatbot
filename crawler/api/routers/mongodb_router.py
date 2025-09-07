from fastapi import APIRouter, HTTPException, Path, Query
from typing import Optional, Dict, Any, List
from service.mongodb_service import mongodb_service
from schemas.response import BaseResponse
from core.logging import get_logger

log = get_logger("mongodb_router")

router = APIRouter(
    prefix="/mongodb",
    tags=["MongoDB 문서 관리"]
)

@router.get("/documents", response_model=BaseResponse[List[Dict[str, Any]]], summary="문서 목록 조회")
async def list_documents(
    skip: int = Query(0, ge=0, description="건너뛸 문서 수"),
    limit: int = Query(10, ge=1, le=100, description="조회할 문서 수"),
    status: Optional[str] = Query(None, description="문서 상태 필터")
):
    """
    MongoDB에 저장된 문서 목록 조회
    
    Args:
        skip: 건너뛸 문서 수
        limit: 조회할 문서 수
        status: 문서 상태 필터 (processed, completed 등)
        
    Returns:
        BaseResponse[List[Dict]]: 문서 목록
    """
    try:
        log.info(f"문서 목록 조회 요청: skip={skip}, limit={limit}, status={status}")
        
        documents = await mongodb_service.list_pdf_documents(skip, limit, status)
        
        log.info(f"문서 목록 조회 완료: {len(documents)}개 문서")
        
        return BaseResponse(
            success=True,
            message=f"{len(documents)}개의 문서를 조회했습니다",
            data=documents
        )
        
    except Exception as e:
        log.error(f"문서 목록 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"문서 목록 조회 실패: {str(e)}"
        )

@router.get("/documents/{document_id}", response_model=BaseResponse[Dict[str, Any]], summary="문서 상세 조회")
async def get_document(
    document_id: str = Path(..., description="문서 ID")
):
    """
    특정 문서의 상세 정보 조회
    
    Args:
        document_id: 문서 ID
        
    Returns:
        BaseResponse[Dict]: 문서 상세 정보
    """
    try:
        log.info(f"문서 상세 조회 요청: {document_id}")
        
        document = await mongodb_service.get_pdf_document(document_id)
        
        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"문서 ID {document_id}에 해당하는 문서를 찾을 수 없습니다"
            )
        
        log.info(f"문서 상세 조회 완료: {document_id}")
        
        return BaseResponse(
            success=True,
            message="문서 상세 정보를 조회했습니다",
            data=document
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"문서 상세 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"문서 상세 조회 실패: {str(e)}"
        )

@router.get("/documents/stock/{stock_code}", response_model=BaseResponse[Dict[str, Any]], summary="종목코드로 문서 조회")
async def get_document_by_stock_code(
    stock_code: str = Path(..., description="종목코드")
):
    """
    종목코드로 문서 조회
    
    Args:
        stock_code: 종목코드
        
    Returns:
        BaseResponse[Dict]: 문서 정보
    """
    try:
        log.info(f"종목코드로 문서 조회 요청: {stock_code}")
        
        document = await mongodb_service.get_document_by_stock_code(stock_code)
        
        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"종목코드 {stock_code}에 해당하는 문서를 찾을 수 없습니다"
            )
        
        log.info(f"종목코드로 문서 조회 완료: {stock_code}")
        
        return BaseResponse(
            success=True,
            message=f"종목코드 {stock_code}의 문서를 조회했습니다",
            data=document
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"종목코드로 문서 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"종목코드로 문서 조회 실패: {str(e)}"
        )

@router.put("/documents/{document_id}/status", response_model=BaseResponse[Dict[str, Any]], summary="문서 상태 업데이트")
async def update_document_status(
    document_id: str = Path(..., description="문서 ID"),
    status: str = Query(..., description="새로운 상태")
):
    """
    문서 상태 업데이트
    
    Args:
        document_id: 문서 ID
        status: 새로운 상태
        
    Returns:
        BaseResponse[Dict]: 업데이트 결과
    """
    try:
        log.info(f"문서 상태 업데이트 요청: {document_id} -> {status}")
        
        success = await mongodb_service.update_document_status(document_id, status)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"문서 ID {document_id}에 해당하는 문서를 찾을 수 없습니다"
            )
        
        log.info(f"문서 상태 업데이트 완료: {document_id} -> {status}")
        
        return BaseResponse(
            success=True,
            message=f"문서 상태가 {status}로 업데이트되었습니다",
            data={"document_id": document_id, "status": status}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"문서 상태 업데이트 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"문서 상태 업데이트 실패: {str(e)}"
        )

@router.delete("/documents/{document_id}", response_model=BaseResponse[Dict[str, Any]], summary="문서 삭제")
async def delete_document(
    document_id: str = Path(..., description="문서 ID")
):
    """
    문서 삭제
    
    Args:
        document_id: 문서 ID
        
    Returns:
        BaseResponse[Dict]: 삭제 결과
    """
    try:
        log.info(f"문서 삭제 요청: {document_id}")
        
        success = await mongodb_service.delete_document(document_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"문서 ID {document_id}에 해당하는 문서를 찾을 수 없습니다"
            )
        
        log.info(f"문서 삭제 완료: {document_id}")
        
        return BaseResponse(
            success=True,
            message="문서가 삭제되었습니다",
            data={"document_id": document_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"문서 삭제 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"문서 삭제 실패: {str(e)}"
        )

@router.post("/cleanup-duplicates", response_model=BaseResponse[Dict[str, Any]], summary="중복 문서 정리")
async def cleanup_duplicate_documents():
    """
    stock_code 기준으로 중복 문서 정리
    
    Returns:
        BaseResponse[Dict]: 정리 결과
    """
    try:
        log.info("중복 문서 정리 요청")
        
        result = await mongodb_service.cleanup_duplicate_documents()
        
        log.info(f"중복 문서 정리 완료: {result}")
        
        return BaseResponse(
            success=True,
            message="중복 문서 정리가 완료되었습니다",
            data=result
        )
        
    except Exception as e:
        log.error(f"중복 문서 정리 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"중복 문서 정리 실패: {str(e)}"
        )
