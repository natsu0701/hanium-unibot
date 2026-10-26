"""
table_parser.py
Uni-Bot 프로젝트 — 신예진 담당 (OCR/Infra)

Upstage Document Parse API가 반환한 <table> HTML을
RAG 검색에 적합한 자연어 텍스트로 변환하는 유틸 모듈.

이 모듈의 출력은 조한익의 extract_pdf.py에 통합됩니다.

사용 방법:
    from app.utils.table_parser import html_table_to_text
    result = html_table_to_text(html_string)
"""

from bs4 import BeautifulSoup


def html_table_to_text(html: str) -> dict:
    """
    Upstage Document Parse가 반환한 <table> HTML을
    RAG 검색에 적합한 자연어 텍스트로 변환합니다.

    Args:
        html: <table>...</table> 형태의 HTML 문자열

    Returns:
        {
            "text": "자연어로 재구성된 표 내용 (각 행을 줄바꿈으로 연결)",
            "headers": ["컬럼1", "컬럼2", ...],
            "row_count": 5,
            "rows_summary": "표의 첫 3행을 나열한 1~2줄 요약"
        }

    주의사항:
        - rowspan/colspan은 이번 버전에서 무시합니다.
          (복잡한 병합 셀 처리는 다음 스프린트 과제)
        - 빈 셀은 '(공란)'으로 표시합니다.
        - 헤더가 없는 표는 첫 번째 행을 헤더로 간주합니다.
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")

    # 표가 없으면 빈 결과 반환
    if not table:
        return {
            "text": "",
            "headers": [],
            "row_count": 0,
            "rows_summary": ""
        }

    rows = table.find_all("tr")

    if not rows:
        return {
            "text": "",
            "headers": [],
            "row_count": 0,
            "rows_summary": ""
        }

    # 첫 번째 행을 헤더로 인식
    # Upstage HTML은 종종 헤더 셀에 <br>이 들어있어서
    # get_text(separator=' ')로 처리하면 자연스럽게 합쳐짐
    header_cells = rows[0].find_all(["td", "th"])
    headers = []
    for cell in header_cells:
        # <br> 태그가 있어도 공백으로 합쳐서 읽기
        header_text = cell.get_text(separator=" ").strip()
        # 빈 헤더는 '(공란)'으로 표시
        if not header_text:
            header_text = "(공란)"
        headers.append(header_text)

    # 데이터 행 처리 (헤더 제외한 나머지 행들)
    data_rows = rows[1:]
    row_sentences = []  # 각 행을 자연어 문장으로 변환한 결과

    for row in data_rows:
        cells = row.find_all(["td", "th"])
        cell_texts = []

        for cell in cells:
            # rowspan/colspan은 무시하고 텍스트만 추출
            # (무시 이유: 복잡한 병합 셀 처리는 이번 스프린트 범위 밖)
            cell_text = cell.get_text(separator=" ").strip()
            if not cell_text:
                cell_text = "(공란)"
            cell_texts.append(cell_text)

        # 헤더와 값을 zip해서 "헤더: 값" 형태로 자연어 문장 생성
        # 예: "과목명: 전공기초 / 학점: 3 / 이수구분: 필수"
        pairs = []
        for header, value in zip(headers, cell_texts):
            pairs.append(f"{header}: {value}")

        # 셀 수가 헤더보다 많으면 헤더 없이 그냥 이어붙임
        if len(cell_texts) > len(headers):
            extra = cell_texts[len(headers):]
            pairs.extend(extra)

        if pairs:
            row_sentences.append(" / ".join(pairs))

    # 전체 텍스트: 각 행 문장을 줄바꿈으로 연결
    full_text = "\n".join(row_sentences)

    # rows_summary: 첫 3행을 나열해서 '이런 표입니다' 수준의 요약
    summary_lines = row_sentences[:3]
    if summary_lines:
        rows_summary = "표 내용 예시: " + " | ".join(summary_lines)
    else:
        rows_summary = ""

    return {
        "text": full_text,
        "headers": headers,
        "row_count": len(data_rows),
        "rows_summary": rows_summary
    }


# ─────────────────────────────────────────
# 단독 실행 시 테스트 (3가지 케이스)
# python table_parser.py
# ─────────────────────────────────────────
if __name__ == "__main__":

    print("=" * 60)
    print("테스트 1: 단순 2열 표 (헤더 2개, 데이터 3행)")
    print("=" * 60)
    html1 = """
    <table>
        <tr><td>과목명</td><td>학점</td></tr>
        <tr><td>전공기초</td><td>3</td></tr>
        <tr><td>전공필수</td><td>3</td></tr>
        <tr><td>교양필수</td><td>2</td></tr>
    </table>
    """
    result1 = html_table_to_text(html1)
    print(f"헤더: {result1['headers']}")
    print(f"행 수: {result1['row_count']}")
    print(f"텍스트:\n{result1['text']}")
    print(f"요약: {result1['rows_summary']}")

    print()
    print("=" * 60)
    print("테스트 2: 3열 표")
    print("=" * 60)
    html2 = """
    <table>
        <tr><th>과목명</th><th>학점</th><th>이수구분</th></tr>
        <tr><td>전공기초</td><td>3</td><td>필수</td></tr>
        <tr><td>전공선택</td><td>3</td><td>선택</td></tr>
        <tr><td>교양필수</td><td>2</td><td>필수</td></tr>
        <tr><td>일반선택</td><td>1</td><td>선택</td></tr>
    </table>
    """
    result2 = html_table_to_text(html2)
    print(f"헤더: {result2['headers']}")
    print(f"행 수: {result2['row_count']}")
    print(f"텍스트:\n{result2['text']}")
    print(f"요약: {result2['rows_summary']}")

    print()
    print("=" * 60)
    print("테스트 3: 헤더에 <br> 태그가 있는 표")
    print("=" * 60)
    html3 = """
    <table>
        <tr>
            <td>과목명<br>Course Name</td>
            <td>학점<br>Credits</td>
            <td>비고<br>Note</td>
        </tr>
        <tr><td>전공기초</td><td>3</td><td>1학년 필수</td></tr>
        <tr><td></td><td>2</td><td>선택</td></tr>
    </table>
    """
    result3 = html_table_to_text(html3)
    print(f"헤더: {result3['headers']}")
    print(f"행 수: {result3['row_count']}")
    print(f"텍스트:\n{result3['text']}")
    print(f"요약: {result3['rows_summary']}")