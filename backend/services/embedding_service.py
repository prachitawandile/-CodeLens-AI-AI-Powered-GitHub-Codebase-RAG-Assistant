"""
Embedding Service for generating dense vector representations of code chunks and queries.
Uses sentence-transformers (all-MiniLM-L6-v2) - lightweight, fast on CPU, and student-laptop friendly.
"""
from typing import Callable, List, Optional
import os


class EmbeddingService:
    """
    Handles local dense vector embeddings using SentenceTransformers.
    Model: all-MiniLM-L6-v2 (384 dimensions)
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self._model = None

    def _load_model(self):
        """Lazy load the sentence-transformers model upon first request."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
            except Exception as e:
                # If offline or downloading fails, provide a helpful error message
                raise RuntimeError(
                    f"Failed to load embedding model '{self.model_name}'. "
                    f"Ensure sentence-transformers is installed and internet connection is active for initial download: {str(e)}"
                )

    def get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for a single string (e.g. user question).
        Returns a list of 384 floats.
        """
        self._load_model()
        cleaned = text.strip()
        if not cleaned:
            cleaned = "empty question"

        vector = self._model.encode(cleaned, normalize_embeddings=True)
        return vector.tolist()

    def get_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> List[List[float]]:
        """
        Generate embeddings in batches for improved CPU/RAM throughput.
        
        Args:
            texts: List of chunk text strings.
            batch_size: Mini-batch size for inference (default 32).
            progress_callback: Optional callback(step_message, percentage).
            
        Returns:
            List of embedding vectors.
        """
        self._load_model()
        total = len(texts)
        if total == 0:
            return []

        all_embeddings: List[List[float]] = []

        if progress_callback:
            progress_callback(f"Generating embeddings for {total} chunks using {self.model_name}...", 65)

        for i in range(0, total, batch_size):
            batch = texts[i : i + batch_size]
            # Replace empty strings if any
            clean_batch = [t if t.strip() else "empty chunk" for t in batch]
            batch_vectors = self._model.encode(
                clean_batch,
                batch_size=len(clean_batch),
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            all_embeddings.extend(batch_vectors.tolist())

            if progress_callback:
                processed = min(i + batch_size, total)
                pct = 65 + int((processed / max(1, total)) * 20)
                progress_callback(f"Generated embeddings {processed}/{total} chunks...", pct)

        return all_embeddings
