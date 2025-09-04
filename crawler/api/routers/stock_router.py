from fastapi import APIRouter, HTTPException, Query, Path, Body
from typing import Optional, Dict, Any
from datetime import datetime
import os
from service.pdf_service import pdf_service
from service.mongodb_service import mongodb_service
from service.prompt_service import prompt_service
from schemas.response import BaseResponse
from core.logging import get_logger

log = get_logger("stock_router")

router = APIRouter(
    prefix="/stock",
    tags=["종목별 PDF 처리"]
)

@router.post("/process/{stock_code}", response_model=BaseResponse[Dict[str, Any]])
async def process_stock_pdf(
    stock_code: str = Path(..., description="종목코드"),
    prompt_type: str = Query("default", description="프롬프트 타입"),
    custom_prompt: Optional[str] = Query(None, description="사용자 정의 프롬프트")
):
    """
    종목코드를 기반으로 PDF를 다운로드하고 GPT로 처리하여 MongoDB에 저장
    
    Args:
        stock_code: 종목코드 (예: "005930")
        prompt_type: 사용할 프롬프트 타입
        custom_prompt: 사용자 정의 프롬프트 (선택사항)
        
    Returns:
        BaseResponse[Dict]: 처리 결과
    """
    try:
        log.info(f"종목 {stock_code} PDF 처리 시작")
        
        # 1. 종목코드로 PDF URL 생성
        pdf_url = pdf_service.generate_pdf_url(stock_code)
        log.info(f"생성된 PDF URL: {pdf_url}")
        
        # 2. PDF 다운로드
        pdf_data = await pdf_service.download_pdf(pdf_url, stock_code)
        log.info(f"PDF 다운로드 완료: {pdf_data['filename']}")
        
        # 3. 프롬프트 선택
        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = prompt_service.get_prompt(prompt_type)
        
        # 4. PDF를 페이지별로 분할하여 병렬로 GPT 처리
        gpt_result = await pdf_service.process_pdf_with_gpt(pdf_data["file_path"], prompt)
        log.info(f"GPT 처리 완료: {gpt_result['successful_pages']}/{gpt_result['total_pages']} 페이지")
        
        # 5. 결과를 MongoDB에 저장
        document_id = await mongodb_service.save_processed_document(
            stock_code, 
            gpt_result, 
            pdf_data
        )
        log.info(f"MongoDB 저장 완료: {document_id}")
        
        # 6. 임시 파일 정리
        pdf_service.cleanup_file(pdf_data["file_path"])
        
        # 7. 응답 데이터 구성
        response_data = {
            "stock_code": stock_code,
            "document_id": document_id,
            "pdf_url": pdf_url,
            "filename": pdf_data["filename"],
            "file_size": pdf_data["file_size"],
            "processing_result": {
                "total_pages": gpt_result["total_pages"],
                "successful_pages": gpt_result["successful_pages"],
                "failed_pages": gpt_result["failed_pages"],
                "parsed_content": "페이지별 결과가 MongoDB에 저장되었습니다"
            },
            "processed_at": datetime.now()
        }
        
        log.info(f"종목 {stock_code} PDF 처리 완료")
        
        return BaseResponse(
            success=True,
            message=f"종목 {stock_code}의 PDF가 성공적으로 처리되어 저장되었습니다",
            data=response_data
        )
        
    except Exception as e:
        log.error(f"종목 {stock_code} PDF 처리 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"종목 {stock_code} PDF 처리 실패: {str(e)}"
        )

@router.get("/documents/{stock_code}", response_model=BaseResponse[Dict[str, Any]])
async def get_stock_documents(
    stock_code: str = Path(..., description="종목코드"),
    skip: int = Query(0, ge=0, description="건너뛸 문서 수"),
    limit: int = Query(10, ge=1, le=100, description="조회할 문서 수")
):
    """
    특정 종목의 처리된 문서 목록 조회
    
    Args:
        stock_code: 종목코드
        skip: 건너뛸 문서 수
        limit: 조회할 문서 수
        
    Returns:
        BaseResponse[Dict]: 문서 목록
    """
    try:
        # 종목별 문서 조회
        filter_query = {"stock_code": stock_code}
        cursor = mongodb_service.collection.find(filter_query).skip(skip).limit(limit).sort("created_at", -1)
        documents = await cursor.to_list(length=limit)
        
        # 전체 문서 수 조회
        total_count = await mongodb_service.collection.count_documents(filter_query)
        
        # ObjectId를 문자열로 변환
        for doc in documents:
            doc["_id"] = str(doc["_id"])
        
        response_data = {
            "stock_code": stock_code,
            "documents": documents,
            "total_count": total_count,
            "skip": skip,
            "limit": limit
        }
        
        return BaseResponse(
            success=True,
            message=f"종목 {stock_code}의 문서 목록 조회가 성공적으로 완료되었습니다",
            data=response_data
        )
        
    except Exception as e:
        log.error(f"종목 {stock_code} 문서 목록 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"종목 {stock_code} 문서 목록 조회 실패: {str(e)}"
        )

@router.get("/documents/{stock_code}/{document_id}", response_model=BaseResponse[Dict[str, Any]])
async def get_stock_document(
    stock_code: str = Path(..., description="종목코드"),
    document_id: str = Path(..., description="문서 ID")
):
    """
    특정 종목의 특정 문서 조회
    
    Args:
        stock_code: 종목코드
        document_id: 문서 ID
        
    Returns:
        BaseResponse[Dict]: 문서 정보
    """
    try:
        from bson import ObjectId
        
        document = await mongodb_service.collection.find_one({
            "_id": ObjectId(document_id),
            "stock_code": stock_code
        })
        
        if not document:
            raise HTTPException(
                status_code=404,
                detail="해당 문서를 찾을 수 없습니다"
            )
        
        document["_id"] = str(document["_id"])
        
        return BaseResponse(
            success=True,
            message="문서 조회가 성공적으로 완료되었습니다",
            data=document
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"문서 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"문서 조회 실패: {str(e)}"
        )

@router.delete("/documents/{stock_code}/{document_id}", response_model=BaseResponse[Dict[str, Any]])
async def delete_stock_document(
    stock_code: str = Path(..., description="종목코드"),
    document_id: str = Path(..., description="문서 ID")
):
    """
    특정 종목의 특정 문서 삭제
    
    Args:
        stock_code: 종목코드
        document_id: 문서 ID
        
    Returns:
        BaseResponse[Dict]: 삭제 결과
    """
    try:
        from bson import ObjectId
        
        # 문서 조회
        document = await mongodb_service.collection.find_one({
            "_id": ObjectId(document_id),
            "stock_code": stock_code
        })
        
        if not document:
            raise HTTPException(
                status_code=404,
                detail="해당 문서를 찾을 수 없습니다"
            )
        
        # GridFS에서 파일 삭제
        if "file_id" in document:
            await mongodb_service._delete_file_from_gridfs(document["file_id"])
        
        # 문서 삭제
        result = await mongodb_service.collection.delete_one({
            "_id": ObjectId(document_id),
            "stock_code": stock_code
        })
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail="문서 삭제에 실패했습니다"
            )
        
        return BaseResponse(
            success=True,
            message="문서가 성공적으로 삭제되었습니다",
            data={"document_id": document_id, "stock_code": stock_code}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"문서 삭제 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"문서 삭제 실패: {str(e)}"
        )
