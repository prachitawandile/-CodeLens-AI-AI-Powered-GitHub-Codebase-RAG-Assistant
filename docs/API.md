# REST API Documentation

Base URL: `http://127.0.0.1:8000`

Interactive OpenAPI / Swagger Documentation is available at:
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

---

## 1. Repository Endpoints

### 1.1 Analyze Repository
Initiate cloning, scanning, chunking, and embedding of a public GitHub repository.

- **Method**: `POST`
- **Path**: `/api/repository/analyze`
- **Headers**: `Content-Type: application/json`

**Request Body**:
```json
{
  "github_url": "https://github.com/psf/requests",
  "force_reindex": false
}
```

**Response (200 OK)**:
```json
{
  "success": true,
  "message": "Indexing initiated for psf/requests. Track progress via /api/repository/status.",
  "repository_name": "psf/requests",
  "github_url": "https://github.com/psf/requests",
  "files_count": 0,
  "chunks_count": 0,
  "languages": {},
  "languages_count": {}
}
```

---

### 1.2 Get Indexing Status
Poll the real-time progress and statistics of the active repository.

- **Method**: `GET`
- **Path**: `/api/repository/status`

**Response (200 OK)**:
```json
{
  "is_indexed": true,
  "repository_name": "psf/requests",
  "github_url": "https://github.com/psf/requests",
  "status": "ready",
  "step_message": "Repository psf/requests successfully indexed and ready for questions!",
  "progress_percentage": 100,
  "files_count": 28,
  "chunks_count": 184,
  "languages": {
    "Python": 88.5,
    "Markdown": 7.7,
    "YAML": 3.8
  },
  "error_message": null
}
```

**Status Enum Values**:
- `idle`: No repository indexed yet.
- `cloning`: Connecting to GitHub and downloading repository files.
- `scanning`: Filtering supported files and excluding dependencies.
- `chunking`: Splitting source code into overlapping line windows.
- `embedding`: Generating dense vectors with Sentence-Transformers and indexing in ChromaDB.
- `ready`: Indexing complete and ready for queries.
- `error`: Analysis failed (error details in `error_message`).

---

### 1.3 Get Repository File Tree
Retrieve the hierarchical directory and file tree of the indexed repository for the file explorer.

- **Method**: `GET`
- **Path**: `/api/repository/files`

**Response (200 OK)**:
```json
[
  {
    "name": "src",
    "path": "src",
    "type": "directory",
    "language": null,
    "size_bytes": null,
    "children": [
      {
        "name": "requests",
        "path": "src/requests",
        "type": "directory",
        "language": null,
        "size_bytes": null,
        "children": [
          {
            "name": "api.py",
            "path": "src/requests/api.py",
            "type": "file",
            "language": "Python",
            "size_bytes": 4820,
            "children": null
          }
        ]
      }
    ]
  },
  {
    "name": "README.md",
    "path": "README.md",
    "type": "file",
    "language": "Markdown",
    "size_bytes": 10240,
    "children": null
  }
]
```

---

### 1.4 Get File Content
Retrieve the full text content of a specific file in the repository. Validates path traversal.

- **Method**: `GET`
- **Path**: `/api/repository/file?path={relative_path}`
- **Query Parameters**:
  - `path` (string, required): Relative path within the repository (e.g. `src/requests/api.py`).

**Response (200 OK)**:
```json
{
  "file_path": "src/requests/api.py",
  "file_name": "api.py",
  "language": "Python",
  "content": "import sys\n\ndef request(method, url, **kwargs):\n    ...",
  "lines_count": 160
}
```

**Error Codes**:
- `400 Bad Request`: Invalid parameters.
- `403 Forbidden`: Path traversal attempt detected.
- `404 Not Found`: File does not exist in repository.

---

### 1.5 Clear Repository
Clear the currently loaded repository and delete its ChromaDB collection.

- **Method**: `POST`
- **Path**: `/api/repository/clear`

**Response (200 OK)**:
```json
{
  "success": true,
  "message": "Active repository and vector database cleared successfully."
}
```

---

## 2. Chat & RAG Endpoints

### 2.1 Ask Question
Ask a natural-language question about the indexed codebase.

- **Method**: `POST`
- **Path**: `/api/chat`
- **Headers**: `Content-Type: application/json`

**Request Body**:
```json
{
  "question": "Where is the main entry point and how does request sending work?",
  "top_k": 5
}
```

**Response (200 OK)**:
```json
{
  "question": "Where is the main entry point and how does request sending work?",
  "answer": "The main entry point for sending requests is implemented in `src/requests/api.py`...",
  "sources": [
    {
      "file_path": "src/requests/api.py",
      "file_name": "api.py",
      "language": "Python",
      "start_line": 15,
      "end_line": 65,
      "chunk_index": 0,
      "code_snippet": "# File: src/requests/api.py | Lines: 15-65 ...",
      "similarity_score": 0.8924
    }
  ],
  "model_used": "Gemini (gemini-1.5-flash)"
}
```

---

### 2.2 Get Suggested Questions
Retrieve contextual questions tailored to the active repository.

- **Method**: `GET`
- **Path**: `/api/chat/suggested-questions`

**Response (200 OK)**:
```json
[
  "Explain the overall project architecture and structure.",
  "Where is the main application entry point defined?",
  "What frameworks and dependencies are configured in this project?",
  "Which functions or modules handle data processing or database logic?",
  "Where is authentication or user handling implemented?",
  "How does error handling work across the codebase?"
]
```

---

## 3. System Health

### 3.1 Health Check
- **Method**: `GET`
- **Path**: `/api/health`

**Response (200 OK)**:
```json
{
  "status": "healthy",
  "service": "AI-Powered GitHub Codebase RAG Assistant",
  "version": "1.0.0",
  "llm_provider": "gemini",
  "embedding_model": "all-MiniLM-L6-v2"
}
```
