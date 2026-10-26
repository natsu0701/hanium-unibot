"""
청크 JSON 을 테스트 DB 에 넣고 검색 정확도를 비교한다.

- 질의·판정은 check_questions_auto.py 와 같음 (60개 질의, search() Top-10, 정답 키워드)
- 운영 DB 는 건드리지 않고 data/processed/_eval_chroma/ 에서 검색
- --expand-section: 검색된 청크와 제목 경로가 같은 조각을 합쳐서 판정 (1500자 이내)
- 결과: evaluation/chunkeval_<조건>_result.csv, chunkeval_summary.md
  (E0~E5 실험 기록은 evaluation/chunkexp_* 에 있음)

사용법 (backend 디렉터리에서):
    .venv/bin/python scripts/eval_chunking_experiments.py                          # 전체 조건
    .venv/bin/python scripts/eval_chunking_experiments.py --conditions final final_expand
    .venv/bin/python scripts/eval_chunking_experiments.py --expand-section --data data/processed/konkuk/extracted_exp.json --name custom
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
for path in (BACKEND_DIR, SCRIPTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.services import rag_service  # noqa: E402
from check_questions import CHECKLIST_PATH, TOP_K_PARTIAL, TOP_K_PASS, ChecklistRow, clean_preview_text, load_checklist  # noqa: E402
from check_questions_auto import ANSWER_KEYWORDS, MULTI_PART_KEYWORDS, is_answer  # noqa: E402

PROCESSED_DIR = BACKEND_DIR / "data" / "processed" / "konkuk"
EVAL_CHROMA_PATH = BACKEND_DIR / "data" / "processed" / "_eval_chroma"
EVAL_DIR = BACKEND_DIR / "evaluation"
SCHOOL_ID = "konkuk"
SECTION_MAX_LEN = 1500
PREFIX = re.compile(r"^(\[[^\]\n]+\])\n")

DATASETS = {
    "final": PROCESSED_DIR / "extracted_exp.json",
    "merged": PROCESSED_DIR / "extracted.json",
}

# 조건: (데이터셋, 섹션 확장)
CONDITIONS = {
    "final": ("final", False),
    "final_expand": ("final", True),
    "Emerge": ("merged", False),
}

VARIANTS = ("A", "B", "C")


# =========================================================
# 테스트 컬렉션
# =========================================================

def use_eval_chroma() -> None:
    """이 프로세스의 rag_service 가 운영 DB 대신 테스트 DB 를 보도록 전환."""
    rag_service.CHROMA_PATH = EVAL_CHROMA_PATH
    rag_service._client = None
    logging.getLogger("app.services.rag_service").setLevel(logging.WARNING)


def use_collection(name: str) -> None:
    rag_service.COLLECTION_NAME = name


def file_sha(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def ensure_collection(dataset: str) -> str:
    """데이터셋 JSON 을 테스트 컬렉션에 적재 (파일이 바뀌지 않았으면 재사용). 컬렉션 이름 반환."""
    path = DATASETS[dataset]
    if not path.exists():
        raise FileNotFoundError(f"데이터 파일이 없습니다: {path}")
    name = f"eval_{dataset}"
    marker = EVAL_CHROMA_PATH / f"{name}.sha1"
    sha = file_sha(path)

    use_collection(name)
    if marker.exists() and marker.read_text() == sha and rag_service.collection_count() > 0:
        print(f"  테스트 컬렉션 재사용: {name} ({rag_service.collection_count()}개)")
        return name

    print(f"  테스트 컬렉션 적재: {name} ← {path.name}")
    try:
        rag_service.get_client().delete_collection(name)
    except Exception:
        pass
    collection = rag_service.get_collection()
    model = rag_service.get_model()

    # 운영 적재(save_to_chromadb)와 같이 chunk_id 로 중복 제거하되, 문서 순서(chunk_index)를 메타데이터에 추가
    unique: dict[str, tuple[int, dict]] = {}
    for index, chunk in enumerate(rag_service.load_chunks(path)):
        unique.setdefault(rag_service.build_chunk_id(chunk), (index, chunk))

    items = list(unique.items())
    for start in range(0, len(items), 64):
        batch = items[start:start + 64]
        vectors = model.encode(
            [rag_service.build_search_text(chunk) for _, (_, chunk) in batch],
            batch_size=32,
            normalize_embeddings=True,
        ).tolist()
        collection.upsert(
            ids=[chunk_id for chunk_id, _ in batch],
            documents=[str(chunk.get("text") or "") for _, (_, chunk) in batch],
            embeddings=vectors,
            metadatas=[{**rag_service.build_metadata(chunk), "chunk_index": index} for _, (index, chunk) in batch],
        )
    marker.write_text(sha)
    print(f"    → {collection.count()}개")
    return name


# =========================================================
# 섹션 확장
# =========================================================

_section_cache: dict[tuple[str, str], str] = {}


def expand_section(text: str) -> tuple[str, str]:
    """(섹션 키, 확장된 텍스트). prefix 가 없으면 원문 그대로."""
    match = PREFIX.match(text)
    if not match:
        return text, text
    prefix = match.group(1)
    cache_key = (rag_service.COLLECTION_NAME, prefix)
    if cache_key not in _section_cache:
        found = rag_service.get_collection().get(
            where={"school_id": SCHOOL_ID},
            where_document={"$contains": prefix + "\n"},
            include=["documents", "metadatas"],
        )
        siblings = sorted(
            (meta.get("chunk_index", 0), doc)
            for doc, meta in zip(found["documents"], found["metadatas"])
            if doc.startswith(prefix + "\n")     # 본문 중간에 같은 문자열이 있는 경우 제외
        )
        bodies = [doc[len(prefix) + 1:] for _, doc in siblings]
        _section_cache[cache_key] = prefix + "\n" + "\n".join(bodies)
    combined = _section_cache[cache_key]
    return prefix, combined if len(combined) <= SECTION_MAX_LEN else text


# =========================================================
# 평가
# =========================================================

@dataclass
class Hit:
    rank: int
    page: str
    score: str
    text: str
    is_answer: bool


@dataclass
class Result:
    row: ChecklistRow
    verdict: str
    rank: int | None
    hits: list[Hit] = field(default_factory=list)


def answer_parts(qid: str) -> list[list[str]]:
    return MULTI_PART_KEYWORDS.get(qid) or [ANSWER_KEYWORDS[qid]]


def evaluate(row: ChecklistRow, *, expand: bool) -> Result:
    parts = answer_parts(row.id)
    results = rag_service.search(row.question, n_results=TOP_K_PARTIAL, school_id=SCHOOL_ID)

    texts: list[tuple[dict, str]] = []
    if expand:
        seen: set[str] = set()
        for result in results:
            key, expanded = expand_section(str(result.get("text") or ""))
            if key in seen:
                continue                     # 같은 섹션은 한 번만, 다음 순위를 당겨 씀
            seen.add(key)
            texts.append((result, expanded))
    else:
        texts = [(result, str(result.get("text") or "")) for result in results]

    hits = [
        Hit(
            rank=rank,
            page=str(result.get("page") or ""),
            score=f"{float(result.get('score') or 0.0):.4f}",
            text=text,
            is_answer=any(is_answer(text, part) for part in parts),
        )
        for rank, (result, text) in enumerate(texts, start=1)
    ]
    if not hits:
        return Result(row, "EMPTY", None, hits)

    part_ranks = [next((h.rank for h in hits if is_answer(h.text, part)), None) for part in parts]
    rank = None if None in part_ranks else max(part_ranks)
    verdict = "FAIL" if rank is None else "PASS" if rank <= TOP_K_PASS else "PARTIAL"
    return Result(row, verdict, rank, hits)


def run_condition(name: str, dataset: str, expand: bool, checklist: list[ChecklistRow]) -> list[Result]:
    print(f"\n[{name}] 데이터={dataset} 섹션확장={'O' if expand else 'X'}")
    ensure_collection(dataset)
    results = [evaluate(row, expand=expand) for row in checklist]
    save_condition_csv(name, results)
    passed = sum(r.verdict == "PASS" for r in results)
    print(f"  PASS {passed}/{len(results)} ({passed / len(results):.1%})")
    return results


def save_condition_csv(name: str, results: list[Result]) -> Path:
    path = EVAL_DIR / f"chunkeval_{name}_result.csv"
    fieldnames = ["id", "variant", "question", "verdict", "answer_rank", "answer_keywords"]
    for rank in range(1, TOP_K_PASS + 1):
        fieldnames += [f"top{rank}_page", f"top{rank}_score", f"top{rank}_text"]
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            row = {
                "id": r.row.id,
                "variant": r.row.variant,
                "question": r.row.question,
                "verdict": r.verdict,
                "answer_rank": r.rank or "",
                "answer_keywords": " / ".join(" + ".join(p) for p in answer_parts(r.row.id)),
            }
            for hit in r.hits[:TOP_K_PASS]:
                row[f"top{hit.rank}_page"] = hit.page
                row[f"top{hit.rank}_score"] = hit.score
                row[f"top{hit.rank}_text"] = ("[정답] " if hit.is_answer else "") + clean_preview_text(hit.text, 300)
            writer.writerow(row)
    return path


# =========================================================
# 비교 리포트
# =========================================================

VERDICT_ORDER = {"PASS": 0, "PARTIAL": 1, "FAIL": 2, "EMPTY": 3}


def summary_table(all_results: dict[str, list[Result]]) -> list[str]:
    lines = [
        "| 조건 | 데이터 | 섹션확장 | PASS | PARTIAL | FAIL | EMPTY | A PASS | B PASS | C PASS |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name, results in all_results.items():
        dataset, expand = CONDITIONS.get(name, (name, None))
        total = len(results)

        def cell(verdict: str) -> str:
            count = sum(r.verdict == verdict for r in results)
            return f"{count} ({count / total:.1%})"

        def variant_pass(variant: str) -> str:
            subset = [r for r in results if r.row.variant == variant]
            return f"{sum(r.verdict == 'PASS' for r in subset)}/{len(subset)}"

        mark = lambda flag: "-" if flag is None else ("O" if flag else "X")  # noqa: E731
        lines.append(
            f"| {name} | {DATASETS.get(dataset, Path(dataset)).name} | {mark(expand)} | "
            f"{cell('PASS')} | {cell('PARTIAL')} | {cell('FAIL')} | {cell('EMPTY')} | "
            f"{variant_pass('A')} | {variant_pass('B')} | {variant_pass('C')} |"
        )
    return lines


def change_table(base: list[Result], other: list[Result]) -> tuple[list[str], list[str]]:
    """(변화 목록, 나빠진 목록)"""
    changed, worse = [], []
    for before, after in zip(base, other):
        if before.verdict == after.verdict and before.rank == after.rank:
            continue
        qid = f"{before.row.id}-{before.row.variant}"
        line = (
            f"| {qid} | {before.row.question} | {before.verdict} → {after.verdict} | "
            f"{before.rank or '-'} → {after.rank or '-'} |"
        )
        changed.append(line)
        if VERDICT_ORDER[after.verdict] > VERDICT_ORDER[before.verdict]:
            worse.append(line)
    return changed, worse


def write_summary(all_results: dict[str, list[Result]]) -> Path:
    lines = ["# 청킹 결과 평가", "", "질의 60개(20문항 × A/B/C), 운영 search() Top-10, 정답 키워드 자동 판정", ""]
    lines += ["## 결과", ""] + summary_table(all_results) + [""]

    comparisons = [("final", name) for name in all_results if name != "final"]
    for base_name, name in comparisons:
        if base_name in all_results and name in all_results:
            base, results = all_results[base_name], all_results[name]
            changed, worse = change_table(base, results)
            lines += [f"## {base_name} → {name} 판정·순위 변화 ({len(changed)}건)", ""]
            if worse:
                lines += [f"**⚠️ 나빠진 질의 {len(worse)}건**", "", "| 질의 | 질문 | 판정 | 정답 rank |", "|---|---|---|---|"] + worse + [""]
            if changed:
                lines += ["| 질의 | 질문 | 판정 | 정답 rank |", "|---|---|---|---|"] + changed + [""]
            else:
                lines += ["변화 없음", ""]

    path = EVAL_DIR / "chunkeval_summary.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="청킹 결과 평가 (테스트 DB, 섹션 확장 선택)")
    parser.add_argument("--conditions", nargs="+", default=list(CONDITIONS), choices=list(CONDITIONS),
                        help="실행할 조건 (기본: 전체)")
    parser.add_argument("--data", type=Path, default=None, help="임의 데이터 JSON 으로 한 조건만 실행")
    parser.add_argument("--name", default="custom", help="--data 사용 시 조건 이름")
    parser.add_argument("--expand-section", action="store_true", help="--data 사용 시 섹션 확장 적용")
    args = parser.parse_args()

    use_eval_chroma()
    checklist = load_checklist(CHECKLIST_PATH)
    print(f"질의 {len(checklist)}개 | 테스트 DB: {EVAL_CHROMA_PATH}")

    all_results: dict[str, list[Result]] = {}
    if args.data:
        DATASETS[args.name] = args.data
        all_results[args.name] = run_condition(args.name, args.name, args.expand_section, checklist)
    else:
        for name in args.conditions:
            dataset, expand = CONDITIONS[name]
            all_results[name] = run_condition(name, dataset, expand, checklist)

    print()
    print("\n".join(summary_table(all_results)))
    summary = write_summary(all_results)
    print(f"\n📄 {summary}")
    print(f"📄 {EVAL_DIR}/chunkeval_<조건>_result.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
