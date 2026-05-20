"""RAG 管道：分块 + 向量化 + Chroma 索引 + 召回 + LLM 重排。

每次请求会在 ``data/vector_db/<trace_id>/<subdir>`` 下创建一个独立持久化的
Chroma collection。``subdir`` 允许并行子任务各写各的隔离目录，避免并发
分叉彼此覆盖。默认 ``subdir="main"`` 保持单轮模式。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.mcp.context import MCPContext
from app.prompts import RERANK_SYSTEM, build_rerank_user_message

_VECTOR_ROOT = Path(__file__).parent.parent.parent / "data" / "vector_db"
_EMBED_MODEL = "BAAI/bge-small-zh-v1.5"
_PER_DOC_RAW_CHAR_LIMIT = 8000

_embedder = None
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=80,
    separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""],
)


def _get_embedder():
    """延迟加载 BGE；首次调用会下载约 95MB。"""
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer

        _embedder = SentenceTransformer(_EMBED_MODEL)
    return _embedder


def _embed(texts: list[str]) -> list[list[float]]:
    model = _get_embedder()
    return model.encode(texts, normalize_embeddings=True).tolist()


def _persist_dir(trace_id: str, subdir: str) -> Path:
    return _VECTOR_ROOT / trace_id / subdir


def _open_collection(trace_id: str, subdir: str):
    import chromadb

    persist_dir = _persist_dir(trace_id, subdir)
    if persist_dir.exists():
        shutil.rmtree(persist_dir, ignore_errors=True)
    persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_dir))
    return client.get_or_create_collection(
        name="docs", metadata={"hnsw:space": "cosine"}
    )


def index_documents(ctx: MCPContext, docs: list[dict], subdir: str = "main") -> dict:
    """对每篇文档分块并写入对应 (request, subdir) 的 Chroma collection。"""
    collection = _open_collection(ctx.trace_id, subdir)

    ids: list[str] = []
    texts: list[str] = []
    metadatas: list[dict] = []

    for d_idx, d in enumerate(docs):
        raw = (d.get("raw_content") or d.get("content") or "").strip()
        if not raw:
            continue
        if len(raw) > _PER_DOC_RAW_CHAR_LIMIT:
            raw = raw[:_PER_DOC_RAW_CHAR_LIMIT]
        chunks = _splitter.split_text(raw)
        for c_idx, chunk in enumerate(chunks):
            chunk = chunk.strip()
            if len(chunk) < 30:
                continue
            ids.append(f"d{d_idx}-c{c_idx}-{uuid.uuid4().hex[:8]}")
            texts.append(chunk)
            metadatas.append(
                {
                    "doc_index": d_idx,
                    "title": d.get("title", ""),
                    "url": d.get("url", ""),
                }
            )

    persist_dir = _persist_dir(ctx.trace_id, subdir)
    if not texts:
        return {"chunks": 0, "subdir": subdir, "persist_dir": str(persist_dir)}

    embeddings = _embed(texts)
    collection.add(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)

    return {"chunks": len(texts), "subdir": subdir, "persist_dir": str(persist_dir)}


def retrieve(
    ctx: MCPContext,
    query: Optional[str] = None,
    subdir: str = "main",
    k_recall: int = 12,
    k_final: int = 6,
) -> list[dict]:
    """向量召回后 LLM 重排，仅作用于指定 ``subdir``。"""
    import chromadb

    persist_dir = _persist_dir(ctx.trace_id, subdir)
    if not persist_dir.exists():
        return []

    actual_query = (query or ctx.request).strip()

    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = client.get_or_create_collection(name="docs")
    if collection.count() == 0:
        return []

    query_emb = _embed([actual_query])[0]
    n_results = min(k_recall, collection.count())
    res = collection.query(query_embeddings=[query_emb], n_results=n_results)

    documents = (res.get("documents") or [[]])[0]
    metadatas = (res.get("metadatas") or [[]])[0]

    candidates: list[dict] = []
    for i, (text, meta) in enumerate(zip(documents, metadatas), start=1):
        candidates.append(
            {
                "id": i,
                "text": text,
                "title": (meta or {}).get("title", ""),
                "url": (meta or {}).get("url", ""),
                "doc_index": (meta or {}).get("doc_index", -1),
            }
        )

    if not candidates:
        return []

    ranked_ids = _llm_rerank(actual_query, candidates)
    if not ranked_ids:
        return candidates[:k_final]

    by_id = {c["id"]: c for c in candidates}
    ranked = [by_id[i] for i in ranked_ids if i in by_id]
    if len(ranked) < k_final:
        seen = {c["id"] for c in ranked}
        for c in candidates:
            if c["id"] not in seen:
                ranked.append(c)
                if len(ranked) >= k_final:
                    break
    return ranked[:k_final]


def _llm_rerank(query: str, chunks: list[dict]) -> list[int]:
    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com",
        temperature=0,
    )
    response = llm.invoke(
        [
            SystemMessage(content=RERANK_SYSTEM),
            HumanMessage(content=build_rerank_user_message(query, chunks)),
        ]
    )
    return _parse_ranking(response.content)


def _parse_ranking(raw: str) -> list[int]:
    if not raw:
        return []
    match = re.search(r"\{.*?\}", raw, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    ranking = data.get("ranking") or []
    out: list[int] = []
    for v in ranking:
        try:
            out.append(int(v))
        except (TypeError, ValueError):
            continue
    return out
