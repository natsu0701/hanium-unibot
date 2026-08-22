"""
extracted_pdf_withoutAPI.py 의 역할
→ extracted_pdf.py의 임시 대체용, extract_pdf.py를 토대로 만들어짐
→ Upstage API 없이 PyMuPDF로 PDF 텍스트 추출
→ extracted.json 형식으로 저장

사용법: extracted_pdf_withoutAPI.py <pdf파일>
예시:   python extracted_pdf_withouteAPI.py data/guide.pdf
"""

import json
import os
import re
import sys

from pypdf import PdfReader

# json파일 저장 위치 지정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(BASE_DIR, "..", "data", "processed")
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "extracted.json")

# ────────────────────────────────────────────
# 전처리
# ────────────────────────────────────────────

def clean_revision_dates(text: str) -> str:
    """개정일 제거"""
    patterns = [
        r"<[^>]*(개정|시행|제정|폐지|공포)[^>]*>",
        r"<\d{4}\.\d{1,2}\.\d{1,2}[^>]*>",
        r"\(\d{4}\.\d{1,2}\.\d{1,2}[^)]*\)",
    ]
    for pattern in patterns:
        text = re.sub(pattern, "", text)
    return text.strip()


def extract_chapter(text: str):
    """제9장 휴학·복학·제적 및 자퇴 → (9, "휴학·복학·제적 및 자퇴")"""
    pattern = r"제\s*(\d+)\s*장\s*\n?\s*(.+)"
    match = re.search(pattern, text)
    if not match:
        return None, None
    chapter_num = int(match.group(1))
    chapter_title = match.group(2).split("\n")[0].strip()
    return chapter_num, chapter_title


def extract_article(text: str):
    """제51조(휴학) → (51, "휴학")"""
    pattern = r"제\s*(\d+)\s*조(?:\s*\((.*?)\))?"
    match = re.search(pattern, text)
    if match:
        title = match.group(2) or ""
        return int(match.group(1)), title.strip()
    pattern = r"제\s*(\d+)\s*조"
    match = re.search(pattern, text)
    if match:
        return int(match.group(1)), ""
    return None, None


def build_doc_id(filename: str) -> str:
    name = os.path.splitext(filename)[0]
    return name.lower().replace(" ", "-").replace("_", "-")


# ────────────────────────────────────────────
# PDF 추출
# ────────────────────────────────────────────

def extract_pdf(pdf_path: str) -> list:
    reader = PdfReader(pdf_path)
    doc_name = os.path.basename(pdf_path)
    doc_id = build_doc_id(doc_name)

    results = []
    current_chapter = None
    current_chapter_title = None
    current_article = None
    current_article_title = None

    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = clean_revision_dates(text)

        if not text.strip():
            continue

        # 장/조 추출
        chapter, chapter_title = extract_chapter(text)
        if chapter is not None:
            current_chapter = chapter
            current_chapter_title = chapter_title

        article, article_title = extract_article(text)
        if article is not None:
            current_article = article
            current_article_title = article_title

        record = {
            "text":          text.strip(),
            "page":          page_num,
            "doc_id":        doc_id,
            "doc_name":      doc_name,
            "chapter":       current_chapter,
            "chapter_title": current_chapter_title,
            "article":       current_article,
            "article_title": current_article_title,
            "is_table":      False
        }

        results.append(record)
        print(f"page {page_num} 처리 완료", file=sys.stderr)

    print(f"\n완료! 총 {len(results)}페이지", file=sys.stderr)
    return results


# ────────────────────────────────────────────
# 실행
# ────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("사용법: python pdf_to_json.py <pdf파일>")
        print("예시:   python pdf_to_json.py data/guide.pdf")
        sys.exit(1)

    pdf_path = sys.argv[1]
    print(f"PDF 추출 중: {pdf_path}", file=sys.stderr)

    results = extract_pdf(pdf_path)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"저장 완료: {output_path}")
    print(f"총 {len(results)}개 청크")


if __name__ == "__main__":
    main()