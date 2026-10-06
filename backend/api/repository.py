"""
Repository API routes: Analyze, status, file tree, file content, and clear.
"""
from typing import List
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from backend.models.schemas import (
    ClearRepositoryResponse,
    FileContentResponse,
    FileTreeNode,
    RepositoryAnalyzeRequest,
    RepositoryAnalyzeResponse,
    RepositoryStatusResponse,
)
from backend.services.rag_service import RAGService
from backend.utils.helpers import is_valid_github_url, parse_github_url

router = APIRouter(prefix="/api/repository", tags=["Repository"])

# Singleton RAGService instance for the application
rag_service = RAGService()


@router.post("/analyze", response_model=RepositoryAnalyzeResponse)
async def analyze_repository(
    request: RepositoryAnalyzeRequest,
    background_tasks: BackgroundTasks,
):
    """
    Validate and analyze a public GitHub repository.
    Starts the RAG indexing pipeline and returns initial status.
    """
    url = request.github_url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="GitHub repository URL cannot be empty.")

    if not is_valid_github_url(url):
        raise HTTPException(
            status_code=400,
            detail="Invalid GitHub repository URL. Must be in the format 'https://github.com/owner/repo'.",
        )

    try:
        owner, repo = parse_github_url(url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Run indexing in background so the UI receives an immediate response and polls /status
    def _run_indexing():
        try:
            rag_service.analyze_repository(url, force_reindex=request.force_reindex)
        except Exception:
            pass  # Error is captured in rag_service state

    background_tasks.add_task(_run_indexing)

    return RepositoryAnalyzeResponse(
        success=True,
        message=f"Indexing initiated for {owner}/{repo}. Track progress via /api/repository/status.",
        repository_name=f"{owner}/{repo}",
        github_url=url,
        files_count=0,
        chunks_count=0,
        languages={},
        languages_count={},
    )


@router.get("/status", response_model=RepositoryStatusResponse)
async def get_repository_status():
    """Get the current indexing status, progress percentage, and statistics."""
    return rag_service.get_status()


@router.get("/files", response_model=List[FileTreeNode])
async def get_repository_files():
    """Retrieve the hierarchical file tree of the currently indexed repository."""
    return rag_service.get_file_tree()


@router.get("/file", response_model=FileContentResponse)
async def get_file_content(path: str = Query(..., description="Relative file path")):
    """Retrieve full content of a specific file for the code viewer with traversal protection."""
    try:
        return rag_service.get_file_content(path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")


@router.post("/clear", response_model=ClearRepositoryResponse)
async def clear_repository():
    """Clear currently indexed repository and vector database data."""
    rag_service.clear()
    return ClearRepositoryResponse(
        success=True,
        message="Active repository and vector database cleared successfully.",
    )
