import aiohttp
import aiofiles
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
from datetime import datetime
import hashlib
import os
import json
import base64
import fitz  # PyMuPDF
import asyncio
from concurrent.futures import ThreadPoolExecutor

from core.config import Settings
from core.logging import get_logger

log = get_logger("pdf_service")
settings = Settings()

class PDFDownloadService:

    def __init__(self):
        self.download_dir = Path("./downloads")
        self.download_dir.mkdir(exist_ok=True)
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.settings = Settings()
    
    def generate_pdf_url(self, stock_code: str) -> str:
        """
        종목코드를 기반으로 PDF 다운로드 URL 생성
        
        Args:
            stock_code: 종목코드 (예: "005930")
            
        Returns:
            str: PDF 다운로드 URL
        """
        # 실제 URL 패턴에 맞게 수정 필요
        # 예시: https://example.com/reports/{stock_code}.pdf
        return f"{self.settings.FUND_PDF_URL}{stock_code}"
    
    async def download_pdf(self, url: str, stock_code: str = None) -> Dict[str, Any]:
        """
        PDF 파일을 다운로드하고 메타데이터를 반환
        
        Args:
            url: 다운로드할 PDF URL
            stock_code: 종목코드 (파일명 생성용)
            
        Returns:
            Dict: 파일 경로, 메타데이터 등이 포함된 딕셔너리
        """
        try:
            # 파일명 생성
            if stock_code:
                filename = f"{stock_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            else:
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                filename = f"pdf_{url_hash}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            file_path = self.download_dir / filename
            
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.settings.PDF_DOWNLOAD_TIMEOUT)
            ) as session:

                async with session.get(url) as response:
                    if response.status != 200:
                        raise Exception(f"PDF 다운로드 실패: HTTP {response.status}")
                    content_type = response.headers.get('content-type', '')
                    if 'application/pdf' not in content_type:
                        raise Exception(f"PDF가 아닌 파일 타입: {content_type}")
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > self.settings.PDF_MAX_SIZE_MB * 1024 * 1024:
                        raise Exception(f"파일 크기 초과: {content_length} bytes")

                    async with aiofiles.open(file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(32*1024):
                            await f.write(chunk)

            file_size = file_path.stat().st_size
            if file_size >= self.settings.PDF_MAX_SIZE_MB * 1024 * 1024:
                file_path.unlink(missing_ok=True)
                raise Exception(f"다운로드된 파일 크기 초과: {file_size} bytes")

            log.info(f"[다운로드 완료] {filename} ({file_size} bytes)")

            return {
                "file_path": str(file_path),
                "filename": filename,
                "original_url": url,
                "file_size": file_size,
                "download_time": datetime.now(),
                "content_type": content_type,
                "stock_code": stock_code
            }

        except Exception as e:
            log.error(f"PDF 다운로드 실패: {str(e)}")
            raise


    async def split_pdf_by_pages(self, file_path: str) -> List[Dict[str, Any]]:
        """
        PDF를 페이지별로 분할하여 텍스트 추출
        
        Args:
            file_path: PDF 파일 경로
            
        Returns:
            List[Dict]: 각 페이지의 텍스트와 메타데이터
        """
        def _extract_page_text(pdf_path: str) -> List[Dict[str, Any]]:
            """PDF 페이지별 텍스트 추출 (동기 함수)"""
            pages = []
            try:
                doc = fitz.open(pdf_path)
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    text = page.get_text()
                    
                    pages.append({
                        "page_number": page_num + 1,
                        "text": text,
                        "char_count": len(text),
                        "word_count": len(text.split())
                    })
                doc.close()
            except Exception as e:
                log.error(f"PDF 페이지 분할 실패: {str(e)}")
                raise
            
            return pages
        
        # 스레드 풀에서 실행
        loop = asyncio.get_event_loop()
        pages = await loop.run_in_executor(self.executor, _extract_page_text, file_path)
        
        log.info(f"PDF 페이지 분할 완료: {len(pages)}페이지")
        return pages
    
    async def process_pdf_with_gpt(self, file_path: str, prompt: str) -> Dict[str, Any]:
        """
        PDF를 페이지별로 분할하여 병렬로 GPT 처리
        
        Args:
            file_path: PDF 파일 경로
            prompt: GPT 프롬프트
            
        Returns:
            Dict: 통합된 GPT 처리 결과
        """
        try:
            # PDF 페이지별 분할
            pages = await self.split_pdf_by_pages(file_path)
            
            # 각 페이지를 병렬로 GPT 처리
            tasks = []
            for page in pages:
                task = self._process_page_with_gpt(page, prompt)
                tasks.append(task)
            
            # 모든 페이지 처리 완료 대기
            page_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 결과 통합
            successful_results = []
            failed_pages = []
            
            for i, result in enumerate(page_results):
                if isinstance(result, Exception):
                    log.error(f"페이지 {i+1} GPT 처리 실패: {str(result)}")
                    failed_pages.append(i+1)
                else:
                    successful_results.append(result)
            
            # 통합된 결과 생성
            integrated_result = {
                "total_pages": len(pages),
                "successful_pages": len(successful_results),
                "failed_pages": failed_pages,
                "page_results": successful_results,
                "integrated_summary": self._integrate_page_results(successful_results)
            }
            
            log.info(f"PDF GPT 처리 완료: {len(successful_results)}/{len(pages)} 페이지 성공")
            return integrated_result
            
        except Exception as e:
            log.error(f"PDF GPT 처리 실패: {str(e)}")
            raise
    
    async def _process_page_with_gpt(self, page: Dict[str, Any], prompt: str) -> Dict[str, Any]:
        """
        단일 페이지를 GPT로 처리
        
        Args:
            page: 페이지 데이터
            prompt: GPT 프롬프트
            
        Returns:
            Dict: GPT 처리 결과
        """
        try:
            # OpenAI API 호출
            import openai
            import httpx
            
            # httpx 클라이언트를 직접 생성하여 사용
            async with httpx.AsyncClient() as http_client:
                client = openai.AsyncOpenAI(
                    api_key=self.settings.OPENAI_API_KEY,
                    http_client=http_client
                )
                
                response = await client.chat.completions.create(
                    model=self.settings.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": f"페이지 {page['page_number']} 내용:\n\n{page['text']}"}
                    ],
                    max_tokens=self.settings.OPENAI_MAX_TOKENS,
                    temperature=self.settings.OPENAI_TEMPERATURE
                )
                
                result_text = response.choices[0].message.content
                
                # JSON 파싱 시도
                try:
                    parsed_result = json.loads(result_text)
                except json.JSONDecodeError:
                    parsed_result = {"raw_response": result_text}
                
                return {
                    "page_number": page["page_number"],
                    "char_count": page["char_count"],
                    "word_count": page["word_count"],
                    "gpt_response": parsed_result,
                    "processing_time": datetime.now()
                }
            
        except Exception as e:
            log.error(f"페이지 {page['page_number']} GPT 처리 실패: {str(e)}")
            raise
    
    def _integrate_page_results(self, page_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        페이지별 GPT 결과를 통합
        
        Args:
            page_results: 페이지별 GPT 처리 결과
            
        Returns:
            Dict: 통합된 결과
        """
        if not page_results:
            return {"error": "처리된 페이지가 없습니다"}
        
        # 기본 통합 로직
        integrated = {
            "total_pages_processed": len(page_results),
            "combined_keywords": set(),
            "combined_summary": "",
            "page_summaries": [],
            "important_data": {},
            "categories": set()
        }
        
        for result in page_results:
            gpt_response = result.get("gpt_response", {})
            
            # 키워드 통합
            if isinstance(gpt_response, dict) and "keywords" in gpt_response:
                if isinstance(gpt_response["keywords"], list):
                    integrated["combined_keywords"].update(gpt_response["keywords"])
            
            # 요약 통합
            if isinstance(gpt_response, dict) and "summary" in gpt_response:
                integrated["page_summaries"].append({
                    "page": result["page_number"],
                    "summary": gpt_response["summary"]
                })
            
            # 카테고리 통합
            if isinstance(gpt_response, dict) and "category" in gpt_response:
                integrated["categories"].add(gpt_response["category"])
        
        # 최종 통합
        integrated["combined_keywords"] = list(integrated["combined_keywords"])
        integrated["categories"] = list(integrated["categories"])
        integrated["combined_summary"] = " ".join([ps["summary"] for ps in integrated["page_summaries"]])
        
        return integrated

    def cleanup_file(self, file_path: str):
        """파일 정리"""
        try:
            os.remove(file_path)
            log.info(f"파일 삭제 완료: {file_path}")
        except Exception as e:
            log.warning(f"파일 삭제 실패: {str(e)}")

# 서비스 인스턴스
pdf_service = PDFDownloadService()
