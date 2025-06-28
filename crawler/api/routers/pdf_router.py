from fastapi import APIRouter, HTTPException, Query, Path, Body
from typing import Optional, Dict, Any
from datetime import datetime
import os
from service.pdf_service import pdf_service
from service.mongodb_service import mongodb_service
from service.prompt_service import prompt_service
from schemas.response import (
    BaseResponse, 
    PDFDownloadRequest, 
    PDFDocument, 
    PDFDocumentList,
    PDFMetadata
)
from core.logging import get_logger

log = get_logger("pdf_router")

router = APIRouter(
    prefix="/pdf",
    tags=["PDF 관리"]
)

@router.post("/download", response_model=BaseResponse[PDFDocument])
async def download_and_store_pdf(
    request: PDFDownloadRequest,
    prompt_type: str = Query("default", description="프롬프트 타입"),
    custom_prompt: Optional[str] = Query(None, description="사용자 정의 프롬프트")
):
    """
    PDF 파일을 다운로드하고 GPT로 파싱한 후 MongoDB에 저장 (기존 방식)
    
    Args:
        request: PDF 다운로드 요청 (URL 포함)
        prompt_type: 사용할 프롬프트 타입
        custom_prompt: 사용자 정의 프롬프트 (선택사항)
        
    Returns:
        BaseResponse[PDFDocument]: 저장된 PDF 문서 정보
    """
    try:
        log.info(f"PDF 다운로드 시작: {request.url}")
        
        # PDF 다운로드
        pdf_data = await pdf_service.download_pdf(str(request.url))
        
        # 프롬프트 선택
        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = prompt_service.get_prompt(prompt_type)
        
        # PDF를 페이지별로 분할하여 병렬로 GPT 처리
        gpt_result = await pdf_service.process_pdf_with_gpt(pdf_data["file_path"], prompt)
        
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
        
        # 깔끔한 메타데이터
        pdf_data["metadata"] = {
            "parsed_content": "\n".join(combined_markdown),
            "total_pages": gpt_result["total_pages"],
            "successful_pages": gpt_result["successful_pages"],
            "failed_pages": gpt_result["failed_pages"],
            "prompt_type": prompt_type
        }
        
        # MongoDB에 저장
        document_id = await mongodb_service.save_pdf_document(pdf_data)
        
        # 저장된 문서 조회
        stored_document = await mongodb_service.get_pdf_document(document_id)
        
        # 임시 파일 정리
        pdf_service.cleanup_file(pdf_data["file_path"])
        
        # 응답 데이터 구성
        pdf_document = PDFDocument(
            id=stored_document["_id"],
            filename=stored_document["filename"],
            original_url=stored_document["original_url"],
            file_size=stored_document["file_size"],
            content_type=stored_document["content_type"],
            download_time=stored_document["download_time"],
            metadata=PDFMetadata(**stored_document["metadata"]),
            status=stored_document["status"],
            created_at=stored_document["created_at"],
            updated_at=stored_document["updated_at"]
        )
        
        log.info(f"PDF 다운로드, GPT 파싱 및 저장 완료: {document_id}")
        
        return BaseResponse(
            success=True,
            message="PDF 파일이 성공적으로 다운로드되고 GPT로 파싱되어 저장되었습니다",
            data=pdf_document
        )
        
    except Exception as e:
        log.error(f"PDF 다운로드 및 저장 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"PDF 다운로드 및 저장 실패: {str(e)}"
        )

@router.get("/documents", response_model=BaseResponse[PDFDocumentList])
async def get_pdf_documents(
    skip: int = Query(0, ge=0, description="건너뛸 문서 수"),
    limit: int = Query(10, ge=1, le=100, description="조회할 문서 수"),
    status: Optional[str] = Query(None, description="상태 필터")
):
    """
    저장된 PDF 문서 목록 조회
    
    Args:
        skip: 건너뛸 문서 수
        limit: 조회할 문서 수
        status: 상태 필터 (선택사항)
        
    Returns:
        BaseResponse[PDFDocumentList]: PDF 문서 목록
    """
    try:
        # 문서 목록 조회
        documents = await mongodb_service.list_pdf_documents(
            skip=skip, 
            limit=limit, 
            status=status
        )
        
        # 전체 문서 수 조회
        total_count = await mongodb_service.collection.count_documents({})
        
        # PDFDocument 객체로 변환
        pdf_documents = []
        for doc in documents:
            pdf_documents.append(PDFDocument(
                id=doc["_id"],
                filename=doc["filename"],
                original_url=doc["original_url"],
                file_size=doc["file_size"],
                content_type=doc["content_type"],
                download_time=doc["download_time"],
                metadata=PDFMetadata(**doc["metadata"]),
                status=doc["status"],
                created_at=doc["created_at"],
                updated_at=doc["updated_at"]
            ))
        
        pdf_document_list = PDFDocumentList(
            documents=pdf_documents,
            total_count=total_count,
            skip=skip,
            limit=limit
        )
        
        return BaseResponse(
            success=True,
            message="PDF 문서 목록 조회가 성공적으로 완료되었습니다",
            data=pdf_document_list
        )
        
    except Exception as e:
        log.error(f"PDF 문서 목록 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"PDF 문서 목록 조회 실패: {str(e)}"
        )

@router.get("/documents/{document_id}", response_model=BaseResponse[PDFDocument])
async def get_pdf_document(document_id: str = Path(..., description="문서 ID")):
    """
    특정 PDF 문서 조회
    
    Args:
        document_id: 조회할 문서 ID
        
    Returns:
        BaseResponse[PDFDocument]: PDF 문서 정보
    """
    try:
        document = await mongodb_service.get_pdf_document(document_id)
        
        if not document:
            raise HTTPException(
                status_code=404,
                detail="해당 문서를 찾을 수 없습니다"
            )
        
        pdf_document = PDFDocument(
            id=document["_id"],
            filename=document["filename"],
            original_url=document["original_url"],
            file_size=document["file_size"],
            content_type=document["content_type"],
            download_time=document["download_time"],
            metadata=PDFMetadata(**document["metadata"]),
            status=document["status"],
            created_at=document["created_at"],
            updated_at=document["updated_at"]
        )
        
        return BaseResponse(
            success=True,
            message="PDF 문서 조회가 성공적으로 완료되었습니다",
            data=pdf_document
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"PDF 문서 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"PDF 문서 조회 실패: {str(e)}"
        )

@router.put("/documents/{document_id}/status", response_model=BaseResponse[dict])
async def update_document_status(
    document_id: str = Path(..., description="문서 ID"),
    status: str = Query(..., description="새로운 상태")
):
    """
    PDF 문서 상태 업데이트
    
    Args:
        document_id: 문서 ID
        status: 새로운 상태
        
    Returns:
        BaseResponse[dict]: 업데이트 결과
    """
    try:
        success = await mongodb_service.update_document_status(document_id, status)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="문서를 찾을 수 없거나 업데이트에 실패했습니다"
            )
        
        return BaseResponse(
            success=True,
            message="문서 상태가 성공적으로 업데이트되었습니다",
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

@router.delete("/documents/{document_id}", response_model=BaseResponse[dict])
async def delete_pdf_document(document_id: str = Path(..., description="문서 ID")):
    """
    PDF 문서 삭제
    
    Args:
        document_id: 삭제할 문서 ID
        
    Returns:
        BaseResponse[dict]: 삭제 결과
    """
    try:
        success = await mongodb_service.delete_document(document_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="문서를 찾을 수 없거나 삭제에 실패했습니다"
            )
        
        return BaseResponse(
            success=True,
            message="PDF 문서가 성공적으로 삭제되었습니다",
            data={"document_id": document_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"PDF 문서 삭제 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"PDF 문서 삭제 실패: {str(e)}"
        )

@router.post("/cleanup-duplicates", response_model=BaseResponse[dict])
async def cleanup_duplicate_documents():
    """
    중복 문서 정리 (stock_code 기준)
    
    Returns:
        BaseResponse[dict]: 정리 결과
    """
    try:
        result = await mongodb_service.cleanup_duplicate_documents()
        
        return BaseResponse(
            success=True,
            message=f"중복 문서 정리가 완료되었습니다. {result.get('total_removed', 0)}개 문서가 삭제되었습니다.",
            data=result
        )
        
    except Exception as e:
        log.error(f"중복 문서 정리 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"중복 문서 정리 실패: {str(e)}"
        )

@router.get("/documents/stock/{stock_code}", response_model=BaseResponse[PDFDocument])
async def get_document_by_stock_code(stock_code: str = Path(..., description="종목코드")):
    """
    종목코드로 문서 조회
    
    Args:
        stock_code: 조회할 종목코드
        
    Returns:
        BaseResponse[PDFDocument]: PDF 문서 정보
    """
    try:
        document = await mongodb_service.get_document_by_stock_code(stock_code)
        
        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"종목코드 {stock_code}에 해당하는 문서를 찾을 수 없습니다"
            )
        
        pdf_document = PDFDocument(
            id=document["_id"],
            filename=document["filename"],
            original_url=document["original_url"],
            file_size=document["file_size"],
            content_type=document["content_type"],
            download_time=document["download_time"],
            metadata=PDFMetadata(**document.get("metadata", {})),
            status=document["status"],
            created_at=document["created_at"],
            updated_at=document["updated_at"]
        )
        
        return BaseResponse(
            success=True,
            message=f"종목코드 {stock_code}의 문서 조회가 성공적으로 완료되었습니다",
            data=pdf_document
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"종목코드 {stock_code} 문서 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"종목코드 {stock_code} 문서 조회 실패: {str(e)}"
        )



