"""
Chunking Service for splitting repository files into meaningful overlapping line chunks.
Preserves exact start/end line numbers and rich metadata for accurate RAG citations.
"""
from typing import Callable, Dict, List, Optional


class CodeChunk:
    """Represents a single chunk of code or text with source citation metadata."""

    def __init__(
        self,
        chunk_id: str,
        text: str,
        repository: str,
        file_path: str,
        file_name: str,
        language: str,
        start_line: int,
        end_line: int,
        chunk_index: int,
    ):
        self.chunk_id = chunk_id
        self.text = text
        self.repository = repository
        self.file_path = file_path
        self.file_name = file_name
        self.language = language
        self.start_line = start_line
        self.end_line = end_line
        self.chunk_index = chunk_index

    def to_dict(self) -> Dict:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "metadata": {
                "repository": self.repository,
                "file_path": self.file_path,
                "file_name": self.file_name,
                "language": self.language,
                "start_line": self.start_line,
                "end_line": self.end_line,
                "chunk_index": self.chunk_index,
            },
        }


class ChunkingService:
    """
    Splits source code and documentation files into overlapping line chunks.
    
    Why line-based chunking with overlap?
    - Simple and understandable for student viva explanations.
    - Code logic (classes, functions, loops) naturally spans multiple lines.
    - Overlap prevents boundary cutoff where a function definition or comment
      is severed midway, ensuring semantic completeness for embeddings.
    """

    def __init__(self, chunk_size: int = 100, chunk_overlap: int = 15):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be a positive integer.")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative.")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be strictly less than chunk_size.")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_file(self, file_info: dict) -> List[CodeChunk]:
        """
        Split a single file into overlapping line chunks with metadata.
        
        Args:
            file_info: Dictionary containing 'repository', 'file_path', 'file_name',
                       'language', and 'content'.
        Returns:
            List of CodeChunk objects.
        """
        repository = file_info["repository"]
        file_path = file_info["file_path"].replace("\\", "/")
        file_name = file_info["file_name"]
        language = file_info.get("language", "Code")
        content = file_info.get("content", "")

        lines = content.splitlines()
        total_lines = len(lines)

        # Empty file check
        if total_lines == 0:
            return []

        # If file is shorter than or equal to chunk_size, create a single chunk
        if total_lines <= self.chunk_size:
            header = f"# File: {file_path} | Lines: 1-{total_lines} | Language: {language}\n"
            chunk_body = "\n".join(lines)
            chunk_text = f"{header}{chunk_body}"
            safe_id = f"{repository}_{file_path}_0".replace("/", "_").replace(".", "_")
            return [
                CodeChunk(
                    chunk_id=safe_id,
                    text=chunk_text,
                    repository=repository,
                    file_path=file_path,
                    file_name=file_name,
                    language=language,
                    start_line=1,
                    end_line=total_lines,
                    chunk_index=0,
                )
            ]

        # Generate sliding window chunks with overlap
        chunks: List[CodeChunk] = []
        step = self.chunk_size - self.chunk_overlap
        chunk_idx = 0
        current_line_idx = 0

        while current_line_idx < total_lines:
            start_line = current_line_idx + 1  # 1-indexed
            end_line = min(current_line_idx + self.chunk_size, total_lines)

            # Slice the lines
            chunk_lines = lines[current_line_idx:end_line]
            chunk_body = "\n".join(chunk_lines)

            # Contextual header to assist vector similarity and LLM understanding
            header = f"# File: {file_path} | Lines: {start_line}-{end_line} | Language: {language}\n"
            chunk_text = f"{header}{chunk_body}"

            safe_id = f"{repository}_{file_path}_{chunk_idx}".replace("/", "_").replace(".", "_")
            chunks.append(
                CodeChunk(
                    chunk_id=safe_id,
                    text=chunk_text,
                    repository=repository,
                    file_path=file_path,
                    file_name=file_name,
                    language=language,
                    start_line=start_line,
                    end_line=end_line,
                    chunk_index=chunk_idx,
                )
            )

            chunk_idx += 1
            current_line_idx += step

            # Break if we reached or exceeded the end
            if end_line >= total_lines:
                break

        return chunks

    def chunk_all_files(
        self,
        extracted_files: List[dict],
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> List[CodeChunk]:
        """
        Process all extracted files and return the combined list of CodeChunks.
        """
        all_chunks: List[CodeChunk] = []
        total_files = len(extracted_files)

        if progress_callback:
            progress_callback(f"Chunking {total_files} files...", 50)

        for i, file_info in enumerate(extracted_files):
            file_chunks = self.chunk_file(file_info)
            all_chunks.extend(file_chunks)

            if progress_callback and (i % 25 == 0 or i == total_files - 1):
                pct = 50 + int(((i + 1) / max(1, total_files)) * 15)
                progress_callback(f"Chunked {i + 1}/{total_files} files ({len(all_chunks)} chunks created)...", pct)

        return all_chunks
