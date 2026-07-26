"""
RAG Engine — ChromaDB wrapper with one ingest pipeline.

Ingests documents (PDF, text, HTML, JSON) into ChromaDB collections.
Provides semantic search and retrieval for the agent loop and modules.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

RAG_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "rag"

# Chunking defaults
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


@dataclass
class Document:
    content: str
    metadata: Dict[str, Any]
    doc_id: Optional[str] = None


@dataclass
class SearchResult:
    content: str
    metadata: Dict[str, Any]
    score: float
    doc_id: Optional[str] = None


class RAGEngine:
    """ChromaDB-backed RAG with ingest and query."""

    def __init__(self, persist_dir: Optional[str] = None):
        self._persist_dir = Path(persist_dir) if persist_dir else RAG_DIR
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = None
        self._collections: Dict[str, Any] = {}

    def _get_client(self):
        if self._client is None:
            try:
                import chromadb
                self._client = chromadb.PersistentClient(path=str(self._persist_dir))
            except ImportError:
                raise RuntimeError("chromadb not installed. Run: pip install chromadb")
        return self._client

    def _get_collection(self, name: str):
        if name not in self._collections:
            client = self._get_client()
            self._collections[name] = client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[name]

    def ingest_text(
        self,
        text: str,
        collection: str = "default",
        doc_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
    ) -> int:
        """Ingest a text document, splitting into chunks."""
        chunks = self._chunk_text(text, chunk_size, chunk_overlap)
        col = self._get_collection(collection)
        ids = []
        docs = []
        metas = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id or 'doc'}_chunk_{i}"
            ids.append(chunk_id)
            docs.append(chunk)
            meta = dict(metadata or {})
            meta["chunk_index"] = i
            meta["total_chunks"] = len(chunks)
            if doc_id:
                meta["doc_id"] = doc_id
            metas.append(meta)
        col.upsert(ids=ids, documents=docs, metadatas=metas)
        return len(chunks)

    def ingest_file(self, file_path: str, collection: str = "default", metadata: Optional[Dict] = None) -> int:
        """Ingest a file (text, JSON, or PDF)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        text = ""
        if path.suffix == ".json":
            import json
            text = json.dumps(json.loads(path.read_text(encoding="utf-8")), indent=2)
        elif path.suffix == ".pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(path))
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
            except ImportError:
                raise RuntimeError("pypdf not installed. Run: pip install pypdf")
        else:
            text = path.read_text(encoding="utf-8")

        meta = dict(metadata or {})
        meta["source_file"] = str(path)
        meta["file_type"] = path.suffix
        return self.ingest_text(text, collection, doc_id=path.stem, metadata=meta)

    def query(
        self,
        query_text: str,
        collection: str = "default",
        n_results: int = 5,
        where: Optional[Dict] = None,
    ) -> List[SearchResult]:
        """Semantic search across a collection."""
        col = self._get_collection(collection)
        kwargs = dict(query_texts=[query_text], n_results=n_results)
        if where:
            kwargs["where"] = where
        results = col.query(**kwargs)

        search_results = []
        if results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                search_results.append(SearchResult(
                    content=doc,
                    metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                    score=1.0 - (results["distances"][0][i] if results["distances"] else [0])[i] if i < len(results.get("distances", [[]])[0]) else 0.0,
                    doc_id=results["ids"][0][i] if results["ids"] else None,
                ))
        return search_results

    def delete_collection(self, name: str):
        if name in self._collections:
            del self._collections[name]
        client = self._get_client()
        try:
            client.delete_collection(name)
        except Exception:
            pass

    def list_collections(self) -> List[Dict]:
        client = self._get_client()
        return [{"name": c.name, "count": c.count()} for c in client.list_collections()]

    @staticmethod
    def _chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
        if len(text) <= chunk_size:
            return [text]
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks


_engine: Optional[RAGEngine] = None


def get_rag_engine() -> RAGEngine:
    global _engine
    if _engine is None:
        _engine = RAGEngine()
    return _engine
