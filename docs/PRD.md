# Product Requirements Document (PRD)

## Product Name
**AI-Powered GitHub Codebase RAG Assistant** (CodeLens AI)

---

## 1. Problem Statement
Understanding an unfamiliar software codebase is one of the most time-consuming and challenging tasks for developers, engineering students, and open-source contributors. When exploring a repository with dozens or hundreds of source files, developers often must manually open and read file after file to locate:
- Authentication and authorization logic
- Database schemas and ORM operations
- API routing and request/response lifecycles
- Architectural patterns and main entry points

Manual inspection without contextual guidance causes cognitive overload, onboarding delays, and increased risk of misinterpreting complex logic.

---

## 2. Product Goal
The primary objective of this project is to build an intelligent, production-quality, yet beginner-explainable web application that allows users to input any public GitHub repository URL and interact with it through natural-language queries. The system automatically ingests the codebase, filters relevant source files, chunks the code while preserving line ranges, generates dense vector embeddings, stores them in ChromaDB, and performs semantic retrieval to supply grounded context to a Large Language Model (LLM).

The application must provide **verifiable source citations** (exact file paths and line ranges) to eliminate AI hallucinations and allow users to immediately view the corresponding source code.

---

## 3. Target Users
- **Undergraduate & Graduate IT / CS Students**: Learning software architectures and preparing for viva examinations or code reviews.
- **Junior & Beginner Developers**: Onboarding onto unfamiliar codebases or open-source projects.
- **Senior Engineers & Reviewers**: Quickly identifying dependencies, entry points, and security flows in third-party libraries.
- **Hackathon Participants**: Rapidly grasping documentation and API structures under tight deadlines.

---

## 4. User Stories
- **US-01**: *As a developer*, I want to paste a public GitHub URL so that the tool automatically analyzes and indexes the project without requiring manual file uploads or GitHub personal access tokens.
- **US-02**: *As a student*, I want to ask natural-language questions (e.g., "Where is authentication handled?") so that I can understand the codebase architecture without reading every line.
- **US-03**: *As a code reviewer*, I want to see exact file citations and line numbers for every answer so that I can verify that the AI's explanation is grounded in real code.
- **US-04**: *As a user*, I want to inspect the indexed repository files in a hierarchical tree explorer and view file contents with syntax highlighting directly inside the app.
- **US-05**: *As a user*, I want real-time feedback during repository indexing (cloning, scanning, chunking, embedding, vector database building) so that I understand what operations are occurring.

---

## 5. Functional Requirements

| Requirement ID | Name | Description |
| :--- | :--- | :--- |
| **FR-01** | **Repository Ingestion** | Accept public GitHub repository URLs (`https://github.com/owner/repo`). Validate URL format and verify public accessibility via HEAD requests. |
| **FR-02** | **Shallow Cloning & Fallback** | Perform fast shallow clone (`git clone --depth 1`). Automatically fall back to downloading and extracting GitHub archive ZIP if git is unavailable. |
| **FR-03** | **File Filtering** | Scan repository directories and filter supported source and doc extensions (`.py`, `.js`, `.ts`, `.java`, `.cpp`, `.html`, `.css`, `.md`, `.json`, etc.). Exclude vendor and cache directories (`node_modules`, `.git`, `venv`, `dist`, etc.) and binaries. |
| **FR-04** | **Line-Based Chunking** | Split source files into overlapping line chunks (default 100 lines, 15 lines overlap) preserving exact line numbers (`start_line`, `end_line`) and file metadata. |
| **FR-05** | **Vector Embeddings** | Generate dense vector embeddings using Sentence-Transformers (`all-MiniLM-L6-v2`, 384 dimensions) optimized for CPU performance on personal laptops. |
| **FR-06** | **ChromaDB Storage** | Persist vector embeddings, text documents, and source metadata in local ChromaDB collections isolated per repository with cosine distance. |
| **FR-07** | **Semantic Retrieval** | Convert user queries into dense vectors and query ChromaDB for top-K (default 5) most relevant code and documentation chunks. |
| **FR-08** | **LLM Answer Generation** | Construct a grounded prompt with retrieved chunks and invoke an LLM (configurable between Google Gemini and OpenAI). Enforce strict grounding. |
| **FR-09** | **Source Citations** | Accompany every answer with clickable source citations showing file path, line range, and similarity score. Support opening the code snippet modal. |
| **FR-10** | **File Explorer & Viewer** | Provide an interactive file tree and code viewer with syntax highlighting and line count indicators. Prevent directory traversal attacks. |
| **FR-11** | **Repository Dashboard** | Display real computed statistics: files indexed, code chunks, language breakdown percentages, and index status. |
| **FR-12** | **Suggested Questions** | Dynamically suggest codebase questions tailored to the repository's detected programming languages and architectural patterns. |

---

## 6. Non-Functional Requirements
- **Usability**: Clean developer tool aesthetics (dark mode, crisp typography, intuitive navigation). A new user should understand how to use the app within 5 seconds.
- **Performance**: Ingestion and indexing of small to medium repositories (10–100 files) completes in under 30 seconds on standard dual-core/quad-core laptop CPUs.
- **Reliability & Idempotency**: Re-indexing an existing repository reuses cached files unless `force_reindex` is specified.
- **Security**: Strict path traversal prevention (`sanitize_repo_path`). Code is never executed. API keys are strictly loaded from `.env` and never leaked to the client.
- **Beginner Explainability**: Code modularity where each file has a single responsibility and standard libraries are preferred over complex frameworks.

---

## 7. Success Criteria
1. Public GitHub URLs can be entered, validated, and processed reliably.
2. Irrelevant directories (`node_modules`, `.git`, etc.) and binary files are automatically excluded.
3. Code chunks accurately record starting and ending line numbers.
4. ChromaDB stores embeddings and successfully returns relevant chunks via cosine similarity search.
5. Natural-language questions receive grounded answers with clickable source citations.
6. Clickable citations allow users to inspect the exact code snippet.
7. File explorer enables browsing and viewing indexed repository files safely.
8. All unit and integration tests pass consistently.

---

## 8. Current Limitations
- Supports public GitHub repositories only; private repository authentication is not implemented in this version.
- Extremely large repositories (e.g. tens of thousands of files like the Linux kernel) should be indexed selectively to avoid memory exhaustion on student laptops.
- Chunking is line-based rather than Abstract Syntax Tree (AST) symbol-based.

---

## 9. Future Scope
- GitHub OAuth and personal access token support for private repositories.
- AST-based semantic chunking for function and class boundaries across multiple languages.
- Interactive call graph and dependency visualizer.
- Multi-repository comparison and Pull Request code review assistant.
- Conversational multi-turn memory with vector-based conversation history.
