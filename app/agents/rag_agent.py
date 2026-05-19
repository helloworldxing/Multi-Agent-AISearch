"""RAG pipeline: chunk + embed + Chroma index + retrieve + LLM rerank.

A fresh, persisted Chroma collection is created per request under
``data/vector_db/<trace_id>``. The directory is wiped on each new request so
stale chunks from prior runs never leak in. The embedder (BGE-small-zh) is
loaded lazily and cached at module level — first call downloads the model.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import uuid
from pathlib import Path

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
    """Lazy-load BGE; first call downloads ~95MB."""
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer(_EMBED_MODEL)
    return _embedder


def _embed(texts: list[str]) -> list[list[float]]:
    model = _get_embedder()
    return model.encode(texts, normalize_embeddings=True).tolist()


def _open_collection(trace_id: str):
    import chromadb
    persist_dir = _VECTOR_ROOT / trace_id
    if persist_dir.exists():
        shutil.rmtree(persist_dir, ignore_errors=True)
    persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_dir))
    return client.get_or_create_collection(name="docs", metadata={"hnsw:space": "cosine"})


def index_documents(ctx: MCPContext, docs: list[dict]) -> dict:
    """Chunk every doc and persist embeddings into a per-request Chroma collection."""
    collection = _open_collection(ctx.trace_id)

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
            metadatas.append({
                "doc_index": d_idx,
                "title": d.get("title", ""),
                "url": d.get("url", ""),
            })

    if not texts:
        return {"chunks": 0, "persist_dir": str(_VECTOR_ROOT / ctx.trace_id)}

    embeddings = _embed(texts)
    collection.add(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)

    return {"chunks": len(texts), "persist_dir": str(_VECTOR_ROOT / ctx.trace_id)}


def retrieve(ctx: MCPContext, k_recall: int = 12, k_final: int = 6) -> list[dict]:
    """Vector-recall then LLM rerank.

    Returns a list of chunks of the form
    ``{"id", "title", "url", "text", "doc_index"}`` ordered by reranked relevance.
    """
    import chromadb
    persist_dir = _VECTOR_ROOT / ctx.trace_id
    if not persist_dir.exists():
        return []

    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = client.get_or_create_collection(name="docs")
    if collection.count() == 0:
        return []

    query_emb = _embed([ctx.request])[0]
    n_results = min(k_recall, collection.count())
    res = collection.query(query_embeddings=[query_emb], n_results=n_results)

    documents = (res.get("documents") or [[]])[0]
    metadatas = (res.get("metadatas") or [[]])[0]

    candidates: list[dict] = []
    for i, (text, meta) in enumerate(zip(documents, metadatas), start=1):
        candidates.append({
            "id": i,
            "text": text,
            "title": (meta or {}).get("title", ""),
            "url": (meta or {}).get("url", ""),
            "doc_index": (meta or {}).get("doc_index", -1),
        })

    if not candidates:
        return []

    ranked_ids = _llm_rerank(ctx.request, candidates)
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
    response = llm.invoke([
        SystemMessage(content=RERANK_SYSTEM),
        HumanMessage(content=build_rerank_user_message(query, chunks)),
    ])
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
