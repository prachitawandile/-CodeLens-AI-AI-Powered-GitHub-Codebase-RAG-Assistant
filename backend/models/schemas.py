"""
Pydantic schemas for request and response validation.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class RepositoryAnalyzeRequest(BaseModel):
    """Request payload to analyze and index a GitHub repository."""
    github_url: str = Field(..., description="Public GitHub repository URL (e.g. https://github.com/user/repo)")
    force_reindex: bool = Field(False, description="Whether to re-clone and re-index if already cached")


class RepositoryAnalyzeResponse(BaseModel):
    """Response payload returned after starting or completing analysis."""
    success: bool
    message: str
    repository_name: str
    github_url: str
    files_count: int = 0
    chunks_count: int = 0
    languages: Dict[str, float] = Field(default_factory=dict, description="Language percentages")
    languages_count: Dict[str, int] = Field(default_factory=dict, description="File count per language")


class RepositoryStatusResponse(BaseModel):
    """Current repository indexing status and statistics."""
    is_indexed: bool = False
    repository_name: Optional[str] = None
    github_url: Optional[str] = None
    status: str = "idle"  # idle, cloning, scanning, chunking, embedding, ready, error
    step_message: str = "No repository indexed"
    progress_percentage: int = 0
    files_count: int = 0
    chunks_count: int = 0
    languages: Dict[str, float] = Field(default_factory=dict)
    error_message: Optional[str] = None


class ChatRequest(BaseModel):
    """User question payload."""
    question: str = Field(..., min_length=1, description="Natural language question about the repository")
    top_k: Optional[int] = Field(default=5, ge=1, le=15, description="Number of relevant chunks to retrieve")


class SourceCitation(BaseModel):
    """Source reference citation corresponding to a retrieved chunk."""
    file_path: str = Field(..., description="Relative file path in repository")
    file_name: str = Field(..., description="Name of the source file")
    language: str = Field(..., description="Programming or markup language")
    start_line: int = Field(..., description="Starting line number in source file")
    end_line: int = Field(..., description="Ending line number in source file")
    chunk_index: int = Field(..., description="Chunk index within the file")
    code_snippet: str = Field(..., description="Extracted code/text chunk")
    similarity_score: float = Field(default=0.0, description="Cosine similarity score (0.0 to 1.0)")


class ChatResponse(BaseModel):
    """LLM answer response along with source citations."""
    question: str
    answer: str
    sources: List[SourceCitation] = Field(default_factory=list)
    model_used: str = "gemini"


class FileTreeNode(BaseModel):
    """Represents a node in the repository file tree."""
    name: str
    path: str
    type: str  # "file" or "directory"
    language: Optional[str] = None
    size_bytes: Optional[int] = None
    children: Optional[List["FileTreeNode"]] = None


class FileContentResponse(BaseModel):
    """Content of a specific file in the repository."""
    file_path: str
    file_name: str
    language: str
    content: str
    lines_count: int


class RepositorySummary(BaseModel):
    """Metadata summary of an indexed repository."""
    name: str
    url: str
    files_count: int
    chunks_count: int
    languages: Dict[str, float]
    indexed_at: str


class ClearRepositoryResponse(BaseModel):
    """Response when clearing indexed repository data."""
    success: bool
    message: str
