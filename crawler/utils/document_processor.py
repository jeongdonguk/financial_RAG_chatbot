"""
문서 처리 관련 유틸리티 함수들
"""
from typing import List, Dict, Any
from core.logging import get_logger

log = get_logger("document_processor")


def combine_page_results(page_results: List[Dict[str, Any]]) -> str:
    """
    페이지별 GPT 결과를 Markdown으로 통합하는 공통 함수
    
    Args:
        page_results: 페이지별 GPT 처리 결과 리스트
        
    Returns:
        str: 통합된 Markdown 내용
    """
    try:
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
        
        result = "\n".join(combined_markdown)
        log.info(f"페이지 결과 통합 완료: {len(page_results)}개 페이지")
        return result
        
    except Exception as e:
        log.error(f"페이지 결과 통합 실패: {str(e)}")
        return ""


def extract_content_from_gpt_response(gpt_response: Any) -> str:
    """
    GPT 응답에서 실제 내용을 추출하는 공통 함수
    
    Args:
        gpt_response: GPT 응답 객체
        
    Returns:
        str: 추출된 내용
    """
    try:
        if isinstance(gpt_response, dict) and "raw_response" in gpt_response:
            return gpt_response["raw_response"]
        elif isinstance(gpt_response, str):
            return gpt_response
        else:
            return str(gpt_response)
    except Exception as e:
        log.error(f"GPT 응답 내용 추출 실패: {str(e)}")
        return str(gpt_response) if gpt_response else ""
