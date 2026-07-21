"""
01_extract_pdf.py
Uni-Bot 프로젝트 — 신예진 담당 (OCR/Infra)

PDF 파일에서 페이지별 텍스트를 추출하여
RAG 파이프라인에서 사용할 JSON으로 변환합니다.

출력 예시

{
    "text": "...",
    "page": 3,
    "doc_id": "konkuk-regulation",
    "doc_name": "건국대학교_학칙.pdf",
    "chapter": 9,
    "chapter_title": "휴학·복학·제적 및 자퇴",
    "article": 51,
    "article_title": "휴학",
    "is_table": false
}
"""

import json
import os
import re
import sys
import requests
from pypdf import PdfReader, PdfWriter
import tempfile
import time

from dotenv import load_dotenv

# json파일 저장 위치 지정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(BASE_DIR, "..", "data", "processed")
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "extracted.json")

# .env 파일 읽기
load_dotenv()

# API Key 읽기
API_KEY = os.getenv("UPSTAGE_API_KEY")

if not API_KEY:
    print("UPSTAGE_API_KEY가 설정되지 않았습니다.", file=sys.stderr)
    sys.exit(1)
print("API KEY starts with:", API_KEY[:10])

def clean_revision_dates(text: str) -> str:
    """
    개정일 제거

    제거 예시
    <2024.03.01 개정>
    <개정 2023.02.01>
    (2024.03.01)
    (일부개정 2024.01.01)
    """

    patterns = [
        r"<[^>]*(개정|시행|제정|폐지|공포)[^>]*>",
        r"<\d{4}\.\d{1,2}\.\d{1,2}[^>]*>",
        r"\(\d{4}\.\d{1,2}\.\d{1,2}[^)]*\)",
    ]

    for pattern in patterns:
        text = re.sub(pattern, "", text)

    return text.strip()

def remove_html(text: str) -> str:
    """
    HTML 태그 제거
    <p>안녕하세요</p> -> 안녕하세요
    """

    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()

def extract_chapter(text: str):
    """
    제9장 휴학·복학·제적 및 자퇴

    return
    -------
    (9, "휴학·복학·제적 및 자퇴")
    """

    pattern = r"제\s*(\d+)\s*장\s*\n?\s*(.+)"

    match = re.search(pattern, text)

    if not match:
        return None, None

    chapter_num = int(match.group(1))
    chapter_title = match.group(2).split("\n")[0].strip()

    return chapter_num, chapter_title


def extract_article(text: str):
    """
    제51조(휴학)

    return

    51
    휴학
    """

    pattern = r"제\s*(\d+)\s*조(?:\s*\((.*?)\))?"

    match = re.search(pattern, text)

    if match:
        title = match.group(2) or ""
        return int(match.group(1)), title.strip()

    # 제목 없는 조
    pattern = r"제\s*(\d+)\s*조"

    match = re.search(pattern, text)

    if match:
        return int(match.group(1)), ""

    return None, None


def build_doc_id(filename: str) -> str:
    """
    건국대학교_학칙.pdf

    →

    konkuk-regulation (예시)

    현재는 파일명 기반으로 생성
    """

    name = os.path.splitext(filename)[0]

    doc_id = (
        name.lower()
        .replace(" ", "-")
        .replace("_", "-")
    )

    return doc_id

def parse_pdf_with_upstage(pdf_path: str):

    url = "https://api.upstage.ai/v1/document-ai/document-parse"

    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }

    data = {
        "ocr": "auto"
    }

    with open(pdf_path, "rb") as f:

        files = {
            "document": f
        }

        response = requests.post(
            url,
            headers=headers,
            files=files,
            data=data,
            timeout=300

        )

    response.raise_for_status()

    result = response.json()

    print(f"parsed elements: {len(result['elements'])}", file=sys.stderr)

    return result

def split_pdf(pdf_path, chunk_size=100):
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)

    chunks = []

    for start in range(0, total_pages, chunk_size):
        writer = PdfWriter()
        end = min(start + chunk_size, total_pages)

        for i in range(start, end):
            writer.add_page(reader.pages[i])

        temp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        writer.write(temp)
        temp.close()

        chunks.append((temp.name, start))

    return chunks


def extract_pdf(pdf_path: str):

    response = parse_pdf_with_upstage(pdf_path)

    doc_name = os.path.basename(pdf_path)
    doc_id = build_doc_id(doc_name)

    results = []
    seen_pages = set()

    # 현재 장/조 정보 유지
    current_chapter = None
    current_chapter_title = None

    current_article = None
    current_article_title = None

    for element in response["elements"]:

        page_num = element["page"]
        category = element["category"]

        if category in ["figure", "image"]:
            continue

        try:
            content = element["content"]

            text = (
                content.get("text")
                or content.get("markdown")
                or content.get("html")
                or ""
            ).strip()

            text = remove_html(text)

        except Exception as e:

            print(f"element 처리 완료 (page {page_num})", file=sys.stderr)

            text = ""

        # -----------------------------
        # 개정일 제거
        # -----------------------------

        text = clean_revision_dates(text)
        
        if not text:
            continue

        # -----------------------------
        # 장 정보 추출
        # -----------------------------

        chapter, chapter_title = extract_chapter(text)

        if chapter is not None:
            current_chapter = chapter
            current_chapter_title = chapter_title

        # -----------------------------
        # 조 정보 추출
        # -----------------------------

        article, article_title = extract_article(text)

        if article is not None:
            current_article = article
            current_article_title = article_title

        # -----------------------------
        # 표 여부
        # 현재 pypdf에서는 정확한 판별 불가
        # 이후 Upstage 적용 예정
        # -----------------------------

        is_table = element["category"] == "table"

        if is_table:
            text = remove_html(content.get("html", ""))

        # -----------------------------
        # JSON 생성
        # -----------------------------

        record = {

            "text": text,

            "page": page_num,

            "doc_id": doc_id,

            "doc_name": doc_name,

            "chapter": current_chapter,

            "chapter_title": current_chapter_title,

            "article": current_article,

            "article_title": current_article_title,

            "is_table": is_table
        }

        results.append(record)

        if page_num not in seen_pages:
            print(
                f"page {page_num} 처리 완료",
                file=sys.stderr
            )
            seen_pages.add(page_num)

    print(
        f"\n완료! 총 {len(results)}페이지",
        file=sys.stderr
    )

    return results

def main():

    # -----------------------------
    # 인자 확인
    # -----------------------------

    if len(sys.argv) < 2:

        print(
            "사용법:",
            file=sys.stderr
        )

        print(
            "python 01_extract_pdf.py <pdf파일>",
            file=sys.stderr
        )

        print(
            "예시:",
            file=sys.stderr
        )

        print(
            "python 01_extract_pdf.py data/학칙.pdf > extracted.json",
            file=sys.stderr
        )

        sys.exit(1)

    pdf_path = sys.argv[1]

    all_pages = []

    chunks = split_pdf(pdf_path, 50)

    for i, (chunk, start_page) in enumerate(chunks):
        print(f"{i+1}/{len(chunks)} 번째 PDF 처리 중...", file=sys.stderr)

        pages = extract_pdf(chunk)

        for p in pages:
            p["page"] += start_page  # ⭐ chunk 기준 보정

        all_pages.extend(pages)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            all_pages,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(f"저장 완료: {output_path}")


if __name__ == "__main__":
    main()