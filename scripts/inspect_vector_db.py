"""Inspect a per-request Chroma collection on disk.

Usage:
  .venv/Scripts/python.exe scripts/inspect_vector_db.py            # list all trace_ids
  .venv/Scripts/python.exe scripts/inspect_vector_db.py <trace_id> # dump that collection
  .venv/Scripts/python.exe scripts/inspect_vector_db.py latest     # dump most-recent
"""
from __future__ import annotations

import sys
from pathlib import Path

import chromadb

_VECTOR_ROOT = Path(__file__).parent.parent / "data" / "vector_db"


def list_traces() -> None:
    if not _VECTOR_ROOT.exists():
        print(f"目录不存在: {_VECTOR_ROOT}")
        return
    traces = sorted(
        [p for p in _VECTOR_ROOT.iterdir() if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
    )
    if not traces:
        print(f"{_VECTOR_ROOT} 下还没有任何 trace 目录")
        return
    print(f"已存在的 trace 目录（按修改时间）：\n")
    for p in traces:
        size_mb = sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / 1024 / 1024
        print(f"  {p.name}  ({size_mb:.2f} MB)")


def dump_trace(trace_id: str) -> None:
    persist_dir = _VECTOR_ROOT / trace_id
    if not persist_dir.exists():
        print(f"trace 目录不存在: {persist_dir}")
        return

    client = chromadb.PersistentClient(path=str(persist_dir))
    try:
        collection = client.get_collection("docs")
    except Exception as e:
        print(f"打不开 collection 'docs': {e}")
        print(f"该目录下的 collections: {[c.name for c in client.list_collections()]}")
        return

    total = collection.count()
    print(f"trace_id : {trace_id}")
    print(f"路径     : {persist_dir}")
    print(f"chunks   : {total}\n")

    if total == 0:
        return

    res = collection.get(include=["documents", "metadatas", "embeddings"])
    ids = res["ids"]
    docs = res["documents"]
    metas = res["metadatas"]
    embs = res["embeddings"]

    for i, (cid, doc, meta, emb) in enumerate(zip(ids, docs, metas, embs)):
        print(f"--- [{i + 1}/{total}] id={cid} ---")
        print(f"  来源标题 : {meta.get('title', '')}")
        print(f"  URL      : {meta.get('url', '')}")
        print(f"  doc_index: {meta.get('doc_index', '')}")
        print(f"  向量维度 : {len(emb)}  前5维: {[round(x, 4) for x in emb[:5]]}")
        text = doc.replace("\n", " ")
        if len(text) > 200:
            text = text[:200] + "..."
        print(f"  文本预览 : {text}\n")


def latest_trace() -> str | None:
    if not _VECTOR_ROOT.exists():
        return None
    traces = [p for p in _VECTOR_ROOT.iterdir() if p.is_dir()]
    if not traces:
        return None
    return max(traces, key=lambda p: p.stat().st_mtime).name


def main() -> None:
    args = sys.argv[1:]
    if not args:
        list_traces()
        return
    target = args[0]
    if target == "latest":
        latest = latest_trace()
        if not latest:
            print("没有任何 trace 目录")
            return
        dump_trace(latest)
    else:
        dump_trace(target)


if __name__ == "__main__":
    main()
