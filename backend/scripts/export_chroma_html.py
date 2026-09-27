"""
ChromaDB에 저장된 전체 청크를 읽어 브라우저로 볼 수 있는 HTML 파일로 내보냅니다.

사용법:
    .venv/bin/python scripts/export_chroma_html.py
    .venv/bin/python scripts/export_chroma_html.py --out /tmp/chroma.html
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import chromadb

# backend/scripts/export_chroma_html.py -> parents[1] = backend
BACKEND_DIR = Path(__file__).resolve().parents[1]
CHROMA_PATH = BACKEND_DIR / "chroma_db"
COLLECTION_NAME = "school_regulations"
DEFAULT_OUT = BACKEND_DIR / "chroma_db_view.html"


def load_rows() -> list[dict]:
    col = chromadb.PersistentClient(path=str(CHROMA_PATH)).get_collection(COLLECTION_NAME)
    result = col.get(include=["documents", "metadatas"])

    rows = [
        {"id": chunk_id, "text": doc or "", **(meta or {})}
        for chunk_id, doc, meta in zip(result["ids"], result["documents"], result["metadatas"])
    ]
    rows.sort(key=lambda r: (str(r.get("school_id")), str(r.get("doc_name")), int(r.get("page") or 0)))
    return rows


def render(rows: list[dict]) -> str:
    # </script> 조기 종료 방지
    data = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    return (
        HTML_TEMPLATE
        .replace("__DATA__", data)
        .replace("__GENERATED__", generated)
        .replace("__COLLECTION__", COLLECTION_NAME)
    )


HTML_TEMPLATE = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ChromaDB Viewer</title>
<style>
:root {
  --bg: #f6f7f9; --panel: #ffffff; --text: #1d2330; --muted: #6b7385; --border: #e2e5eb;
  --accent: #3b5bdb; --accent-soft: #e7ecff; --table: #0b7a53; --table-soft: #dcf5ea; --mark: #ffe58a;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #14161b; --panel: #1c1f26; --text: #e4e7ee; --muted: #9098aa; --border: #2d323d;
    --accent: #8ea5ff; --accent-soft: #273056; --table: #5fd3a3; --table-soft: #173a2d; --mark: #6b5a12;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text);
  font: 14px/1.6 -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Noto Sans KR", "Malgun Gothic", sans-serif; }
header { padding: 20px 16px 8px; max-width: 1100px; margin: 0 auto; }
h1 { margin: 0; font-size: 20px; }
.sub { color: var(--muted); font-size: 12px; }
.stats { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.stat { background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 8px 12px; }
.stat b { display: block; font-size: 18px; }
.stat span { color: var(--muted); font-size: 12px; }
.controls { position: sticky; top: 0; z-index: 5; background: var(--bg); border-bottom: 1px solid var(--border); }
.controls-inner { max-width: 1100px; margin: 0 auto; padding: 10px 16px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
input, select, button { font: inherit; color: var(--text); background: var(--panel);
  border: 1px solid var(--border); border-radius: 6px; padding: 6px 10px; }
input[type=search] { flex: 1 1 240px; min-width: 0; }
select { max-width: 100%; }
button { cursor: pointer; }
button:disabled { opacity: .4; cursor: default; }
label.chk { display: flex; align-items: center; gap: 4px; color: var(--muted); }
main { max-width: 1100px; margin: 0 auto; padding: 12px 16px 40px; }
.count { color: var(--muted); margin-bottom: 8px; }
.card { background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 12px 14px; margin-bottom: 10px; }
.meta { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin-bottom: 6px; }
.badge { font-size: 12px; padding: 1px 8px; border-radius: 999px; background: var(--accent-soft); color: var(--accent); white-space: nowrap; }
.badge.table { background: var(--table-soft); color: var(--table); }
.badge.plain { background: transparent; border: 1px solid var(--border); color: var(--muted); }
.title { font-weight: 600; }
.text { white-space: pre-wrap; word-break: break-word; }
.text.clamp { display: -webkit-box; -webkit-line-clamp: 6; -webkit-box-orient: vertical; overflow: hidden; }
.extra { margin-top: 6px; font-size: 12px; color: var(--muted); word-break: break-all; }
.toggle { margin-top: 6px; font-size: 12px; padding: 2px 8px; }
mark { background: var(--mark); color: inherit; border-radius: 2px; }
.pager { display: flex; gap: 8px; align-items: center; justify-content: center; margin-top: 16px; }
.empty { text-align: center; color: var(--muted); padding: 40px 0; }
</style>
</head>
<body>
<header>
  <h1>ChromaDB Viewer</h1>
  <div class="sub">collection: __COLLECTION__ · 생성: __GENERATED__</div>
  <div class="stats" id="stats"></div>
</header>

<div class="controls"><div class="controls-inner">
  <input type="search" id="q" placeholder="본문·제목·ID 검색 (공백으로 AND 검색)">
  <select id="school"><option value="">전체 학교</option></select>
  <select id="doc"><option value="">전체 문서</option></select>
  <label class="chk"><input type="checkbox" id="tableOnly"> 표만</label>
  <select id="pageSize">
    <option>20</option><option selected>50</option><option>100</option><option value="0">전체</option>
  </select>
</div></div>

<main>
  <div class="count" id="count"></div>
  <div id="list"></div>
  <div class="pager" id="pager"></div>
</main>

<script>
const ROWS = __DATA__;

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const reEsc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

let page = 0;

function uniq(key, rows) {
  const counts = new Map();
  rows.forEach((r) => counts.set(r[key], (counts.get(r[key]) || 0) + 1));
  return [...counts.entries()].sort((a, b) => String(a[0]).localeCompare(String(b[0])));
}

function fillSelect(sel, entries, allLabel) {
  const cur = sel.value;
  sel.innerHTML = `<option value="">${allLabel}</option>` +
    entries.map(([v, n]) => `<option value="${esc(v)}">${esc(v || "(없음)")} (${n})</option>`).join("");
  sel.value = entries.some(([v]) => String(v) === cur) ? cur : "";
}

function renderStats() {
  const schools = uniq("school_id", ROWS).length;
  const docs = uniq("doc_id", ROWS).length;
  const tables = ROWS.filter((r) => r.is_table).length;
  const chars = ROWS.reduce((a, r) => a + r.text.length, 0);
  $("stats").innerHTML = [
    [ROWS.length.toLocaleString(), "청크"], [schools, "학교"], [docs, "문서"],
    [tables.toLocaleString(), "표 청크"], [Math.round(chars / ROWS.length).toLocaleString(), "평균 글자수"],
  ].map(([v, l]) => `<div class="stat"><b>${v}</b><span>${l}</span></div>`).join("");
}

function filtered() {
  const terms = $("q").value.trim().toLowerCase().split(/\s+/).filter(Boolean);
  const school = $("school").value, doc = $("doc").value, tableOnly = $("tableOnly").checked;
  return ROWS.filter((r) => {
    if (school && r.school_id !== school) return false;
    if (doc && r.doc_name !== doc) return false;
    if (tableOnly && !r.is_table) return false;
    if (!terms.length) return true;
    const hay = [r.text, r.id, r.chapter_title, r.article_title, r.table_headers, r.table_summary].join(" ").toLowerCase();
    return terms.every((t) => hay.includes(t));
  });
}

function highlight(text, terms) {
  const safe = esc(text);
  if (!terms.length) return safe;
  return safe.replace(new RegExp(terms.map((t) => reEsc(esc(t))).join("|"), "gi"), (m) => `<mark>${m}</mark>`);
}

function card(r, terms) {
  const heading = [r.chapter && `제${r.chapter}장`, r.chapter_title, r.article && `제${r.article}조`, r.article_title]
    .filter(Boolean).join(" ");
  const extra = [
    r.table_headers && `표 헤더: ${esc(r.table_headers)}`,
    r.table_summary && `표 요약: ${esc(r.table_summary)}`,
    `id: ${esc(r.id)} · doc_id: ${esc(r.doc_id)}`,
  ].filter(Boolean).join("<br>");
  const long = r.text.length > 400 || r.text.split("\n").length > 6;
  return `<div class="card">
    <div class="meta">
      <span class="badge">${esc(r.school_id)}</span>
      <span class="badge plain">${esc(r.doc_name)}</span>
      <span class="badge plain">p.${esc(r.page)}</span>
      ${r.is_table ? '<span class="badge table">표</span>' : ""}
      <span class="badge plain">${r.text.length.toLocaleString()}자</span>
      ${heading ? `<span class="title">${esc(heading)}</span>` : ""}
    </div>
    <div class="text${long ? " clamp" : ""}">${highlight(r.text, terms)}</div>
    ${long ? '<button class="toggle">펼치기</button>' : ""}
    <div class="extra">${extra}</div>
  </div>`;
}

function render() {
  const terms = $("q").value.trim().split(/\s+/).filter(Boolean);
  const rows = filtered();
  const size = Number($("pageSize").value) || rows.length || 1;
  const pages = Math.max(1, Math.ceil(rows.length / size));
  page = Math.min(page, pages - 1);
  const slice = rows.slice(page * size, page * size + size);

  $("count").textContent = `${rows.length.toLocaleString()}개 청크` +
    (rows.length ? ` · ${page * size + 1}–${page * size + slice.length}번째 표시` : "");
  $("list").innerHTML = slice.length ? slice.map((r) => card(r, terms)).join("") : '<div class="empty">결과가 없습니다.</div>';
  $("pager").innerHTML = pages > 1 ? `
    <button data-go="0" ${page === 0 ? "disabled" : ""}>«</button>
    <button data-go="${page - 1}" ${page === 0 ? "disabled" : ""}>이전</button>
    <span>${page + 1} / ${pages}</span>
    <button data-go="${page + 1}" ${page >= pages - 1 ? "disabled" : ""}>다음</button>
    <button data-go="${pages - 1}" ${page >= pages - 1 ? "disabled" : ""}>»</button>` : "";
}

function syncDocOptions() {
  const school = $("school").value;
  fillSelect($("doc"), uniq("doc_name", school ? ROWS.filter((r) => r.school_id === school) : ROWS), "전체 문서");
}

const reset = () => { page = 0; render(); };
let timer;
$("q").addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(reset, 150); });
$("school").addEventListener("change", () => { syncDocOptions(); reset(); });
["doc", "tableOnly", "pageSize"].forEach((id) => $(id).addEventListener("change", reset));
$("pager").addEventListener("click", (e) => {
  const go = e.target.dataset.go;
  if (go !== undefined) { page = Number(go); render(); window.scrollTo(0, 0); }
});
$("list").addEventListener("click", (e) => {
  if (!e.target.classList.contains("toggle")) return;
  const text = e.target.previousElementSibling;
  text.classList.toggle("clamp");
  e.target.textContent = text.classList.contains("clamp") ? "펼치기" : "접기";
});

fillSelect($("school"), uniq("school_id", ROWS), "전체 학교");
syncDocOptions();
renderStats();
render();
</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="ChromaDB 전체 데이터를 HTML로 내보냅니다.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"출력 경로 (기본: {DEFAULT_OUT})")
    args = parser.parse_args()

    rows = load_rows()
    args.out.write_text(render(rows), encoding="utf-8")
    print(f"{len(rows)}개 청크 → {args.out}")


if __name__ == "__main__":
    main()
