"""
Chat API routes: Question answering with RAG and suggested questions.
"""
from typing import List
from fastapi import APIRouter, HTTPException

from backend.api.repository import rag_service
from backend.models.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def ask_question(request: ChatRequest):
    """
    Ask a natural-language question about the indexed GitHub repository.
    Performs vector similarity search in ChromaDB, builds grounded context,
    invokes LLM, and returns answer with source citations.
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    status = rag_service.get_status()
    if not status.is_indexed:
        raise HTTPException(
            status_code=400,
            detail="No repository is currently indexed. Please enter and analyze a GitHub repository first.",
        )

    try:
        response = rag_service.ask(question=question, top_k=request.top_k or 5)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while answering your question: {str(e)}",
        )


@router.get("/suggested-questions", response_model=List[str])
async def get_suggested_questions():
    """Return tailored example questions for the currently indexed codebase."""
    status = rag_service.get_status()
    if not status.is_indexed:
        return [
            "Where is authentication implemented?",
            "Explain the API flow and endpoints.",
            "Which files handle database operations?",
            "Where is the main entry point of the project?",
            "Explain the overall project architecture.",
        ]

    # Tailor based on detected languages
    langs = {k.lower() for k in status.languages.keys()}
    questions = [
        "Explain the overall project architecture and structure.",
        "Where is the main application entry point defined?",
    ]

    if "python" in langs:
        questions.append("What frameworks and dependencies are configured in this project?")
        questions.append("Which functions or modules handle data processing or database logic?")
    elif "javascript" in langs or "typescript" in langs or "react jsx" in langs or "react tsx" in langs:
        questions.append("How are UI components and state management structured?")
        questions.append("Which files handle API calls or client-side routing?")
    elif "java" in langs:
        questions.append("Where are the core service classes and models located?")
    elif "c++" in langs or "c" in langs:
        questions.append("Where are header definitions and main algorithms located?")

    questions.append("Where is authentication or user handling implemented?")
    questions.append("How does error handling work across the codebase?")

    return questions[:6]
