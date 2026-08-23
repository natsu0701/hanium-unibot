"""
학사 규칙 더미 데이터를 생성하는 스크립트.

기존 학사요람 extracted.json을 샘플링해
demo_univ_1, demo_univ_2, ... demo_univ_n 학교용 테스트셋을 만듭니다.

사용법 (backend 디렉터리에서):
    python scripts/make_dummy_school.py 3
    python scripts/make_dummy_school.py --count 5 --n-sample 30
    python scripts/make_dummy_school.py 2 --source data/processed/extracted.json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = BACKEND_DIR / "data" / "processed"

DEFAULT_SOURCE_CANDIDATES = [
    PROCESSED_DIR / "konkuk" / "extracted.json",
    PROCESSED_DIR / "extracted.json",
]

DEFAULT_N_SAMPLE = 25


def resolve_source(source: Path | None) -> Path:
    if source is not None:
        path = source if source.is_absolute() else BACKEND_DIR / source
        if not path.exists():
            raise FileNotFoundError(f"원본 JSON을 찾을 수 없습니다: {path}")
        return path

    for candidate in DEFAULT_SOURCE_CANDIDATES:
        if candidate.exists():
            return candidate

    tried = ", ".join(str(p) for p in DEFAULT_SOURCE_CANDIDATES)
    raise FileNotFoundError(
        "원본 extracted.json을 찾을 수 없습니다. "
        f"다음 경로를 확인하거나 --source로 지정하세요: {tried}"
    )


def load_chunks(source_path: Path) -> list[dict]:
    with source_path.open(encoding="utf-8") as f:
        chunks = json.load(f)

    if not isinstance(chunks, list):
        raise ValueError("원본 JSON 최상위 구조는 배열이어야 합니다.")

    valid = [
        chunk
        for chunk in chunks
        if isinstance(chunk, dict) and str(chunk.get("text") or "").strip()
    ]

    if not valid:
        raise ValueError("원본에 유효한 청크가 없습니다.")

    return valid


def make_school_chunks(
    chunks: list[dict],
    school_index: int,
    n_sample: int,
    seed: int,
) -> list[dict]:
    school_id = f"demo_univ_{school_index}"
    school_name = f"데모대학교 {school_index}"

    rng = random.Random(seed + school_index)
    sample_size = min(n_sample, len(chunks))
    sample = rng.sample(chunks, sample_size)

    dummy_chunks: list[dict] = []

    for chunk in sample:
        new_chunk = dict(chunk)
        origin_doc_id = str(chunk.get("doc_id") or "unknown")

        new_chunk["school_id"] = school_id
        new_chunk["doc_name"] = f"{school_name} 학사요람(더미)"
        new_chunk["doc_id"] = f"{school_id}-{origin_doc_id}"
        dummy_chunks.append(new_chunk)

    return dummy_chunks


def make_dummies(
    count: int,
    n_sample: int = DEFAULT_N_SAMPLE,
    source: Path | None = None,
    seed: int = 42,
    output_dir: Path | None = None,
) -> list[Path]:
    if count < 1:
        raise ValueError("count는 1 이상이어야 합니다.")

    source_path = resolve_source(source)
    chunks = load_chunks(source_path)
    out_root = output_dir or PROCESSED_DIR
    out_root.mkdir(parents=True, exist_ok=True)

    print(f"원본: {source_path}")
    print(f"원본 청크 수: {len(chunks)}")
    print(f"생성할 학교 수: {count} (청크/학교: 최대 {n_sample})")

    written: list[Path] = []

    for i in range(1, count + 1):
        school_id = f"demo_univ_{i}"
        dummy_chunks = make_school_chunks(
            chunks,
            school_index=i,
            n_sample=n_sample,
            seed=seed,
        )

        school_dir = out_root / school_id
        school_dir.mkdir(parents=True, exist_ok=True)
        output_path = school_dir / "extracted.json"

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(dummy_chunks, f, ensure_ascii=False, indent=2)

        written.append(output_path)
        print(
            f"  [{school_id}] 청크 {len(dummy_chunks)}개 → {output_path}"
        )

    print(f"완료: demo_univ_1 … demo_univ_{count} 생성")
    return written


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "기존 학사규칙 JSON을 샘플링해 "
            "demo_univ_1 … demo_univ_n 더미 데이터를 생성합니다."
        ),
    )
    parser.add_argument(
        "count",
        type=int,
        nargs="?",
        help="생성할 데모 학교 개수 (demo_univ_1 … demo_univ_n)",
    )
    parser.add_argument(
        "--count",
        dest="count_opt",
        type=int,
        help="생성할 데모 학교 개수 (--count 형태)",
    )
    parser.add_argument(
        "--n-sample",
        type=int,
        default=DEFAULT_N_SAMPLE,
        help=f"학교당 샘플링할 청크 수 (기본: {DEFAULT_N_SAMPLE})",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="원본 extracted.json 경로 (기본: konkuk/extracted.json 또는 extracted.json)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="샘플링 시드 (학교마다 seed+i 사용)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="출력 루트 디렉터리 (기본: data/processed)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    count = args.count_opt if args.count_opt is not None else args.count

    if count is None:
        print(
            "사용법: python scripts/make_dummy_school.py <개수>\n"
            "예시:   python scripts/make_dummy_school.py 3",
            file=sys.stderr,
        )
        return 1

    try:
        make_dummies(
            count=count,
            n_sample=args.n_sample,
            source=args.source,
            seed=args.seed,
            output_dir=args.output_dir,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
