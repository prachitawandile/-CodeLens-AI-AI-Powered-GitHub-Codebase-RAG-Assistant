"""
RAG Service orchestrating repository cloning, file filtering, chunking,
embedding generation, ChromaDB vector indexing, semantic retrieval, and LLM answer generation.
"""
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from backend.models.schemas import (
    ChatResponse,
    FileContentResponse,
    FileTreeNode,
    RepositoryStatusResponse,
    SourceCitation,
)
from backend.services.chunking_service import ChunkingService
from backend.services.embedding_service import EmbeddingService
from backend.services.file_service import FileService
from backend.services.github_service import GitHubService
from backend.services.llm_service import LLMService
from backend.services.vector_store import VectorStoreService
from backend.utils.helpers import (
    build_file_tree,
    calculate_language_percentages,
    parse_github_url,
)


class RAGService:
    """
    Central coordinator for the AI-Powered GitHub Codebase RAG system.
    Maintains active repository status and coordinates modular services.
    """

    def __init__(
        self,
        github_service: Optional[GitHubService] = None,
        file_service: Optional[FileService] = None,
        chunking_service: Optional[ChunkingService] = None,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store: Optional[VectorStoreService] = None,
        llm_service: Optional[LLMService] = None,
    ):
        self.github_service = github_service or GitHubService()
        self.file_service = file_service or FileService(
            max_file_size_kb=int(os.getenv("MAX_FILE_SIZE_KB", "300"))
        )
        self.chunking_service = chunking_service or ChunkingService(
            chunk_size=int(os.getenv("CHUNK_SIZE", "100")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "15")),
        )
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store or VectorStoreService()
        self.llm_service = llm_service or LLMService()

        # In-memory state tracking for indexing progress and active repository
        self.lock = threading.Lock()
        self.status = "idle"  # idle, cloning, scanning, chunking, embedding, ready, error
        self.step_message = "No repository analyzed yet."
        self.progress_percentage = 0
        self.error_message: Optional[str] = None

        self.current_repo_name: Optional[str] = None
        self.current_github_url: Optional[str] = None
        self.current_repo_dir: Optional[Path] = None
        self.current_files: List[dict] = []
        self.current_languages: Dict[str, float] = {}
        self.current_languages_count: Dict[str, int] = {}
        self.current_chunks_count: int = 0
        self.indexed_at: Optional[str] = None

    def _update_progress(self, message: str, percentage: int, status: str = "processing"):
        with self.lock:
            self.step_message = message
            self.progress_percentage = percentage
            self.status = status

    def get_status(self) -> RepositoryStatusResponse:
        """Return the current repository status and stats."""
        with self.lock:
            return RepositoryStatusResponse(
                is_indexed=(self.status == "ready"),
                repository_name=self.current_repo_name,
                github_url=self.current_github_url,
                status=self.status,
                step_message=self.step_message,
                progress_percentage=self.progress_percentage,
                files_count=len(self.current_files),
                chunks_count=self.current_chunks_count,
                languages=self.current_languages,
                error_message=self.error_message,
            )

    def analyze_repository(self, github_url: str, force_reindex: bool = False) -> dict:
        """
        Execute full RAG indexing pipeline:
        1. Validate & clone repository
        2. Scan & filter files
        3. Split into overlapping line chunks
        4. Generate embeddings
        5. Store in ChromaDB
        """
        try:
            self.error_message = None
            owner, repo = parse_github_url(github_url)
            repo_id = f"{owner}__{repo}".lower()

            self._update_progress(f"Connecting to GitHub for {owner}/{repo}...", 5, "cloning")

            # Step 1: Clone or fetch from local cache
            repo_dir = self.github_service.clone_repository(
                github_url,
                force_reindex=force_reindex,
                progress_callback=lambda msg, pct: self._update_progress(msg, pct, "cloning"),
            )

            # Step 2: Scan & extract supported files
            self._update_progress("Scanning and filtering supported source files...", 30, "scanning")
            extracted_files, lang_counts = self.file_service.scan_and_extract(
                repo_dir=repo_dir,
                repo_name=repo,
                progress_callback=lambda msg, pct: self._update_progress(msg, pct, "scanning"),
            )

            # Step 3: Chunking
            self._update_progress(f"Chunking {len(extracted_files)} files...", 50, "chunking")
            chunks = self.chunking_service.chunk_all_files(
                extracted_files,
                progress_callback=lambda msg, pct: self._update_progress(msg, pct, "chunking"),
            )

            # Step 4: Embedding generation
            self._update_progress(f"Generating vector embeddings for {len(chunks)} chunks...", 65, "embedding")
            chunk_texts = [c.text for c in chunks]
            embeddings = self.embedding_service.get_embeddings_batch(
                chunk_texts,
                progress_callback=lambda msg, pct: self._update_progress(msg, pct, "embedding"),
            )

            # Step 5: Store in ChromaDB
            self._update_progress("Indexing vectors into ChromaDB...", 85, "embedding")
            self.vector_store.add_chunks(
                repo_id=repo_id,
                chunks=chunks,
                embeddings=embeddings,
                progress_callback=lambda msg, pct: self._update_progress(msg, pct, "embedding"),
            )

            # Calculate stats
            lang_pcts = calculate_language_percentages(lang_counts)

            with self.lock:
                self.current_repo_name = f"{owner}/{repo}"
                self.current_github_url = github_url
                self.current_repo_dir = repo_dir
                self.current_files = extracted_files
                self.current_languages = lang_pcts
                self.current_languages_count = lang_counts
                self.current_chunks_count = len(chunks)
                self.status = "ready"
                self.step_message = f"Repository {owner}/{repo} successfully indexed and ready for questions!"
                self.progress_percentage = 100
                self.indexed_at = datetime.utcnow().isoformat()

            return {
                "success": True,
                "message": f"Successfully indexed {owner}/{repo}.",
                "repository_name": f"{owner}/{repo}",
                "github_url": github_url,
                "files_count": len(extracted_files),
                "chunks_count": len(chunks),
                "languages": lang_pcts,
                "languages_count": lang_counts,
            }

        except Exception as e:
            with self.lock:
                self.status = "error"
                self.error_message = str(e)
                self.step_message = f"Analysis failed: {str(e)}"
                self.progress_percentage = 0
            raise

    def ask(self, question: str, top_k: int = 5) -> ChatResponse:
        """
        Execute RAG question-answering workflow:
        1. Ensure a repository is indexed
        2. Embed question
        3. Query ChromaDB for top_k relevant chunks
        4. Pass context + question to LLM
        5. Return answer with rich source citations
        """
        if self.status != "ready" or not self.current_repo_name:
            raise ValueError("No repository is currently indexed. Please analyze a repository first.")

        owner, repo = parse_github_url(self.current_github_url)
        repo_id = f"{owner}__{repo}".lower()

        # Step 1: Embed question
        query_vector = self.embedding_service.get_embedding(question)

        # Step 2: Retrieve top K chunks from ChromaDB
        retrieved_chunks = self.vector_store.query(
            repo_id=repo_id,
            query_embedding=query_vector,
            top_k=top_k,
        )

        # Step 3: Call LLM with retrieved context
        llm_result = self.llm_service.generate_answer(
            question=question,
            context_chunks=retrieved_chunks,
            repository_name=self.current_repo_name,
        )

        # Step 4: Build source citations
        citations = []
        for chunk in retrieved_chunks:
            citations.append(
                SourceCitation(
                    file_path=chunk["file_path"],
                    file_name=chunk["file_name"],
                    language=chunk["language"],
                    start_line=chunk["start_line"],
                    end_line=chunk["end_line"],
                    chunk_index=chunk["chunk_index"],
                    code_snippet=chunk["text"],
                    similarity_score=chunk["similarity_score"],
                )
            )

        return ChatResponse(
            question=question,
            answer=llm_result["answer"],
            sources=citations,
            model_used=llm_result["model_used"],
        )

    def get_file_tree(self) -> List[FileTreeNode]:
        """Return the hierarchical file tree of the currently indexed repository."""
        if not self.current_files:
            return []
        tree_dicts = build_file_tree(self.current_files)
        return [FileTreeNode(**item) for item in tree_dicts]

    def get_file_content(self, rel_path: str) -> FileContentResponse:
        """Safely read and return the content of a file in the active repository."""
        if not self.current_repo_dir:
            raise ValueError("No active repository loaded.")

        info = self.file_service.read_file(self.current_repo_dir, rel_path)
        return FileContentResponse(**info)

    def clear(self) -> bool:
        """Clear the currently active repository and ChromaDB collection."""
        with self.lock:
            if self.current_github_url:
                try:
                    owner, repo = parse_github_url(self.current_github_url)
                    repo_id = f"{owner}__{repo}".lower()
                    self.vector_store.delete_collection(repo_id)
                except Exception:
                    pass

            self.status = "idle"
            self.step_message = "No repository analyzed yet."
            self.progress_percentage = 0
            self.error_message = None
            self.current_repo_name = None
            self.current_github_url = None
            self.current_repo_dir = None
            self.current_files = []
            self.current_languages = {}
            self.current_languages_count = {}
            self.current_chunks_count = 0
            self.indexed_at = None

        return True
