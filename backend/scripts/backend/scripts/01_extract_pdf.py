"""
01_extract_pdf.py
Uni-Bot 프로젝트 — 신예진 담당 (OCR/Infra)

PDF 파일에서 페이지별 텍스트를 추출해서 JSON으로 출력하는 스크립트.
이 스크립트의 출력(extracted.json)은 유정진의 02_chunk.py의 입력이 됩니다.

실행 방법:
    python 01_extract_pdf.py <pdf_경로>
    python 01_extract_pdf.py <pdf_경로> > extracted.json

출력 형식:
    [
        { "page": 1, "text": "제1조 (목적) 이 규정은 ..." },
        { "page": 2, "text": "제2조 (적용 범위) ..." },
        ...
    ]
"""

import sys
import json
import os

def extract_pdf(pdf_path: str) -> list[dict]:
    """
    PDF 파일에서 페이지별 텍스트를 추출합니다.

    Args:
        pdf_path: PDF 파일 경로

    Returns:
        페이지별 딕셔너리 리스트
        [{ "page": 1, "text": "..." }, ...]

    주의:
        - 빈 페이지도 { "page": N, "text": "" } 형태로 유지 (드롭 금지)
        - 페이지 번호는 1부터 시작 (PDF 원본 페이지 번호와 일치)
        - 빈 페이지 번호를 보존해야 나중에 출처 기능이 정확하게 동작함
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        print("pypdf가 설치되지 않았습니다. 아래 명령어로 설치해주세요:", file=sys.stderr)
        print("  pip install pypdf", file=sys.stderr)
        sys.exit(1)

    # PDF 파일 존재 확인
    if not os.path.exists(pdf_path):
        print(f"오류: 파일을 찾을 수 없습니다 — {pdf_path}", file=sys.stderr)
        sys.exit(1)

    if not pdf_path.lower().endswith(".pdf"):
        print(f"오류: PDF 파일만 지원합니다 — {pdf_path}", file=sys.stderr)
        sys.exit(1)

    print(f"PDF 로드 중: {pdf_path}", file=sys.stderr)

    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    print(f"총 {total_pages}페이지 감지됨", file=sys.stderr)

    results = []

    for i, page in enumerate(reader.pages):
        page_num = i + 1  # 1부터 시작

        # 텍스트 추출 (실패해도 빈 문자열로 유지 — 페이지 번호 보존이 핵심)
        try:
            text = page.extract_text() or ""
            # 앞뒤 공백 제거, 중간 과도한 줄바꿈 정리
            text = text.strip()
        except Exception as e:
            print(f"경고: {page_num}페이지 텍스트 추출 실패 ({e}) — 빈 텍스트로 유지", file=sys.stderr)
            text = ""

        results.append({
            "page": page_num,
            "text": text
        })

        # 진행률 stderr로 출력 (stdout은 JSON 출력 전용)
        print(f"{page_num}/{total_pages} 페이지 처리 완료...", file=sys.stderr)

    print(f"\n완료! 총 {total_pages}페이지 추출됨", file=sys.stderr)
    return results


def main():
    # 인자 검증
    if len(sys.argv) < 2:
        print("사용법: python 01_extract_pdf.py <pdf_파일_경로>", file=sys.stderr)
        print("예시: python 01_extract_pdf.py data/요람.pdf > extracted.json", file=sys.stderr)
        sys.exit(1)

    pdf_path = sys.argv[1]

    # 추출 실행
    pages = extract_pdf(pdf_path)

    # stdout에 JSON 출력 (ensure_ascii=False: 한글 깨짐 방지)
    print(json.dumps(pages, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()