"""
FastAPI Main Application Entry Point.
Connects repository and chat routes, CORS middleware, static frontend mounting, and health checks.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Load environment variables from .env file
base_dir = Path(__file__).resolve().parent.parent
env_path = base_dir / ".env"
load_dotenv(dotenv_path=env_path)

from backend.api.chat import router as chat_router
from backend.api.repository import router as repository_router

app = FastAPI(
    title="AI-Powered GitHub Codebase RAG Assistant",
    description="Production-quality B.Tech final-year project demonstrating Codebase RAG, ChromaDB vector search, and LLM code understanding.",
    version="1.0.0",
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(repository_router)
app.include_router(chat_router)


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint to verify backend operational readiness."""
    return {
        "status": "healthy",
        "service": "AI-Powered GitHub Codebase RAG Assistant",
        "version": "1.0.0",
        "llm_provider": os.getenv("LLM_PROVIDER", "gemini"),
        "embedding_model": os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
    }


# Static frontend mounting
frontend_dir = base_dir / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_frontend_index():
        """Serve frontend index.html directly from root URL."""
        index_file = frontend_dir / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "Frontend index.html not found"}


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)
