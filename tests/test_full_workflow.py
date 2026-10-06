"""
End-to-End workflow integration test for RAG pipeline.
"""
from pathlib import Path
import pytest
from backend.services.chunking_service import ChunkingService
from backend.services.file_service import FileService
from backend.services.github_service import GitHubService
from backend.services.llm_service import LLMService
from backend.services.rag_service import RAGService
from backend.services.vector_store import VectorStoreService


class MockGitHubService(GitHubService):
    """Mock GitHub Service for deterministic offline testing."""

    def __init__(self, sample_repo_path: Path):
        self.sample_repo_path = sample_repo_path

    def validate_url(self, url: str):
        return "sample-owner", "sample-repo"

    def check_accessibility(self, owner: str, repo: str):
        return True, None

    def clone_repository(self, github_url: str, force_reindex: bool = False, progress_callback=None):
        if progress_callback:
            progress_callback("Cloned mock repo", 25)
        return self.sample_repo_path


def test_full_rag_workflow(tmp_path):
    # 1. Create a dummy test codebase
    repo_dir = tmp_path / "mock_project"
    repo_dir.mkdir()

    auth_file = repo_dir / "auth.py"
    auth_file.write_text(
        "def authenticate_user(username, password):\n"
        "    if username == 'admin' and password == 'secret':\n"
        "        return {'token': 'jwt_token_123', 'role': 'admin'}\n"
        "    return None\n",
        encoding="utf-8",
    )

    db_file = repo_dir / "database.py"
    db_file.write_text(
        "def connect_db():\n"
        "    # Handles PostgreSQL database connection\n"
        "    return 'db_connection_pool'\n",
        encoding="utf-8",
    )

    readme_file = repo_dir / "README.md"
    readme_file.write_text(
        "# Mock Project\n"
        "This project provides user authentication and PostgreSQL database connection.\n",
        encoding="utf-8",
    )

    # 2. Instantiate services
    mock_gh = MockGitHubService(repo_dir)
    file_service = FileService()
    chunking_service = ChunkingService(chunk_size=50, chunk_overlap=10)
    vector_store = VectorStoreService(persist_dir=str(tmp_path / "chroma_e2e"))
    llm_service = LLMService(api_key="test_offline_key")

    rag = RAGService(
        github_service=mock_gh,
        file_service=file_service,
        chunking_service=chunking_service,
        vector_store=vector_store,
        llm_service=llm_service,
    )

    # 3. Analyze repository
    result = rag.analyze_repository("https://github.com/sample-owner/sample-repo")
    assert result["success"] is True
    assert result["files_count"] == 3
    assert result["chunks_count"] >= 3

    # Check status
    status = rag.get_status()
    assert status.is_indexed is True
    assert status.status == "ready"
    assert "Python" in status.languages

    # 4. Check file tree
    tree = rag.get_file_tree()
    assert len(tree) == 3
    paths = [node.path for node in tree]
    assert "auth.py" in paths
    assert "database.py" in paths

    # 5. Check file content
    content_res = rag.get_file_content("auth.py")
    assert "authenticate_user" in content_res.content

    # 6. Ask question: Where is authentication handled?
    response = rag.ask("Where is authentication handled?")
    assert response.question == "Where is authentication handled?"
    assert len(response.sources) > 0

    # The top retrieved source must be auth.py!
    top_source = response.sources[0]
    assert "auth.py" in top_source.file_path
    assert top_source.similarity_score > 0.0

    # 7. Ask question: database operations
    db_response = rag.ask("Which file handles database operations?")
    assert any("database.py" in s.file_path for s in db_response.sources)

    # 8. Clear repository
    rag.clear()
    cleared_status = rag.get_status()
    assert cleared_status.is_indexed is False
    assert cleared_status.status == "idle"
