"""
ChromaDB Vector Store Service.
Manages persistent local vector database storage, collections per repository,
batch chunk indexing, and cosine similarity retrieval.
"""
import os
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional

import chromadb
from chromadb.config import Settings


class VectorStoreService:
    """
    Encapsulates ChromaDB operations.
    Stores chunk embeddings, text, and source metadata locally on disk.
    """

    def __init__(self, persist_dir: Optional[str] = None):
        if persist_dir:
            self.persist_dir = Path(persist_dir)
        else:
            base_dir = Path(__file__).resolve().parent.parent
            self.persist_dir = base_dir / "data" / "chroma_db"

        self.persist_dir.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB persistent client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False),
        )

    def _sanitize_collection_name(self, repo_id: str) -> str:
        """
        ChromaDB collection name rules:
        - 3-63 characters
        - Starts and ends with alphanumeric character
        - Contains only [a-zA-Z0-9._-]
        """
        cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", repo_id.strip())
        # Prefix if begins with invalid char
        if not cleaned[0].isalnum():
            cleaned = "repo_" + cleaned
        if not cleaned[-1].isalnum():
            cleaned = cleaned + "_idx"

        # Truncate to 63 chars max
        if len(cleaned) > 63:
            cleaned = cleaned[:63]
        if len(cleaned) < 3:
            cleaned = f"col_{cleaned}".ljust(3, "0")

        return cleaned.lower()

    def get_collection(self, repo_id: str):
        """Retrieve existing collection for repository if present."""
        coll_name = self._sanitize_collection_name(repo_id)
        try:
            return self.client.get_collection(name=coll_name)
        except Exception:
            return None

    def get_or_create_collection(self, repo_id: str):
        """Create or get a ChromaDB collection with cosine distance metadata."""
        coll_name = self._sanitize_collection_name(repo_id)
        return self.client.get_or_create_collection(
            name=coll_name,
            metadata={"hnsw:space": "cosine"},
        )

    def collection_exists(self, repo_id: str) -> bool:
        """Check if repository collection exists and contains indexed chunks."""
        coll = self.get_collection(repo_id)
        if coll is not None:
            try:
                return coll.count() > 0
            except Exception:
                return False
        return False

    def delete_collection(self, repo_id: str) -> bool:
        """Delete collection for repository (used during re-indexing or clearing)."""
        coll_name = self._sanitize_collection_name(repo_id)
        try:
            self.client.delete_collection(name=coll_name)
            return True
        except Exception:
            return False

    def get_collection_count(self, repo_id: str) -> int:
        """Return total number of chunks stored in collection."""
        coll = self.get_collection(repo_id)
        if coll is not None:
            try:
                return coll.count()
            except Exception:
                return 0
        return 0

    def add_chunks(
        self,
        repo_id: str,
        chunks: List,  # List of CodeChunk objects or dicts
        embeddings: List[List[float]],
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> int:
        """
        Store chunks with their dense embeddings and metadata in ChromaDB.
        Uses batches of 500 items to adhere to vector store performance best practices.
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Mismatch: {len(chunks)} chunks and {len(embeddings)} embeddings provided."
            )

        total = len(chunks)
        if total == 0:
            return 0

        # Delete existing collection to prevent duplicate chunks upon reindexing
        self.delete_collection(repo_id)
        collection = self.get_or_create_collection(repo_id)

        if progress_callback:
            progress_callback(f"Storing {total} vector chunks into ChromaDB...", 85)

        batch_size = 500
        for i in range(0, total, batch_size):
            end_idx = min(i + batch_size, total)
            batch_chunks = chunks[i:end_idx]
            batch_embeddings = embeddings[i:end_idx]

            ids = []
            documents = []
            metadatas = []
            for j, c in enumerate(batch_chunks, start=i):
                if isinstance(c, dict):
                    cid = c.get("chunk_id", f"{repo_id}_{j}")
                    doc = c.get("text", "")
                    meta = c.get("metadata", {})
                else:
                    cid = getattr(c, "chunk_id", f"{repo_id}_{j}")
                    doc = getattr(c, "text", "")
                    meta = {
                        "repository": getattr(c, "repository", ""),
                        "file_path": getattr(c, "file_path", ""),
                        "file_name": getattr(c, "file_name", ""),
                        "language": getattr(c, "language", ""),
                        "start_line": getattr(c, "start_line", 1),
                        "end_line": getattr(c, "end_line", 1),
                        "chunk_index": getattr(c, "chunk_index", 0),
                    }
                ids.append(cid)
                documents.append(doc)
                metadatas.append(meta)

            collection.add(
                ids=ids,
                documents=documents,
                embeddings=batch_embeddings,
                metadatas=metadatas,
            )

            if progress_callback:
                pct = 85 + int((end_idx / max(1, total)) * 10)
                progress_callback(f"Stored {end_idx}/{total} vectors in ChromaDB...", pct)

        if progress_callback:
            progress_callback(f"Vector database indexing complete! Total chunks: {total}", 95)

        return total

    def query(
        self,
        repo_id: str,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[dict]:
        """
        Perform cosine similarity search on the repository's ChromaDB collection.
        
        Returns:
            List of retrieved chunks with metadata and computed similarity score.
        """
        collection = self.get_collection(repo_id)
        if collection is None or collection.count() == 0:
            return []

        # Chroma query
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        retrieved: List[dict] = []
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc, meta, dist in zip(documents, metadatas, distances):
            # Chroma returns cosine distance in [0, 2] for cosine space
            # Cosine similarity = 1 - cosine distance (clamped to [0.0, 1.0])
            similarity = max(0.0, min(1.0, round(1.0 - float(dist), 4)))

            retrieved.append(
                {
                    "text": doc,
                    "metadata": meta,
                    "similarity_score": similarity,
                    "file_path": meta.get("file_path", "unknown"),
                    "file_name": meta.get("file_name", "unknown"),
                    "language": meta.get("language", "Text"),
                    "start_line": meta.get("start_line", 1),
                    "end_line": meta.get("end_line", 1),
                    "chunk_index": meta.get("chunk_index", 0),
                }
            )

        return retrieved
