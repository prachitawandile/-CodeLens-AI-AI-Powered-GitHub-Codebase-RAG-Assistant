"""
File Service for scanning repository directories, filtering supported source/doc files,
ignoring binaries/vendor folders, and securely reading file contents.
"""
import os
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

from backend.utils.helpers import (
    DEFAULT_IGNORE_DIRS,
    EXTENSION_LANGUAGE_MAP,
    IGNORE_EXTENSIONS,
    detect_language,
    sanitize_repo_path,
)


class FileService:
    """Handles scanning, filtering, and content extraction of repository files."""

    def __init__(
        self,
        supported_extensions: Optional[Set[str]] = None,
        ignore_dirs: Optional[Set[str]] = None,
        max_file_size_kb: int = 300,
    ):
        self.supported_extensions = (
            supported_extensions or set(EXTENSION_LANGUAGE_MAP.keys())
        )
        self.ignore_dirs = ignore_dirs or DEFAULT_IGNORE_DIRS
        self.max_file_size_bytes = max_file_size_kb * 1024

    def is_binary_file(self, file_path: Path) -> bool:
        """Heuristic check to detect binary files (e.g. contains null byte in the first 2KB)."""
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(2048)
                if b"\x00" in chunk:
                    return True
            return False
        except Exception:
            return True

    def should_ignore_dir(self, dir_path: Path) -> bool:
        """Check if any directory segment should be ignored."""
        parts = {p.lower() for p in dir_path.parts}
        return bool(parts & {d.lower() for d in self.ignore_dirs})

    def is_supported_file(self, file_path: Path, repo_root: Path) -> bool:
        """
        Check whether the file should be included in RAG indexing.
        Verifies directory exclusion, extension, file size, and non-binary content.
        """
        # Exclude hidden files that start with dot except supported config files like .env.example
        if file_path.name.startswith(".") and not file_path.name.endswith(tuple(self.supported_extensions)):
            return False

        # Check ignored extension
        suffix = file_path.suffix.lower()
        if suffix in IGNORE_EXTENSIONS:
            return False

        # Must have a supported extension
        if suffix not in self.supported_extensions:
            return False

        # File size check
        try:
            size = file_path.stat().st_size
            if size == 0 or size > self.max_file_size_bytes:
                return False
        except OSError:
            return False

        # Check binary heuristic
        if self.is_binary_file(file_path):
            return False

        return True

    def scan_and_extract(
        self,
        repo_dir: Path,
        repo_name: str,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> Tuple[List[dict], Dict[str, int]]:
        """
        Scan the repository directory, filter supported files, and extract text contents.
        
        Returns:
            Tuple of:
                - List of file metadata and content dictionaries
                - Dictionary mapping Language -> count of files
        """
        extracted_files: List[dict] = []
        languages_count: Dict[str, int] = {}

        if not repo_dir.exists() or not repo_dir.is_dir():
            raise FileNotFoundError(f"Repository directory '{repo_dir}' does not exist.")

        all_candidate_paths: List[Path] = []

        # Walk directory skipping ignored folders
        for root, dirs, files in os.walk(repo_dir):
            root_path = Path(root)
            rel_root = root_path.relative_to(repo_dir)

            # Prune ignored directories in-place for performance
            dirs[:] = [
                d
                for d in dirs
                if d.lower() not in {x.lower() for x in self.ignore_dirs}
                and not d.startswith(".")
            ]

            for file_name in files:
                file_path = root_path / file_name
                all_candidate_paths.append(file_path)

        total_candidates = len(all_candidate_paths)
        if progress_callback:
            progress_callback(f"Scanning {total_candidates} candidate files...", 30)

        for i, file_path in enumerate(all_candidate_paths):
            if not self.is_supported_file(file_path, repo_dir):
                continue

            rel_path = file_path.relative_to(repo_dir).as_posix()
            language = detect_language(rel_path)

            try:
                # Attempt UTF-8 with fallback to latin-1
                try:
                    content = file_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    content = file_path.read_text(encoding="latin-1", errors="replace")

                lines = content.splitlines()
                # Skip empty or whitespace-only files
                if not content.strip():
                    continue

                extracted_files.append(
                    {
                        "repository": repo_name,
                        "file_path": rel_path,
                        "file_name": file_path.name,
                        "language": language,
                        "content": content,
                        "size_bytes": len(content.encode("utf-8")),
                        "lines_count": len(lines),
                    }
                )

                languages_count[language] = languages_count.get(language, 0) + 1

            except Exception:
                # Gracefully skip unreadable files
                continue

            # Update progress periodically
            if progress_callback and i % 50 == 0:
                pct = 30 + int((i / max(1, total_candidates)) * 15)
                progress_callback(f"Extracted {len(extracted_files)} valid source files...", pct)

        if not extracted_files:
            raise ValueError(
                "No supported source code or documentation files were found in this repository. "
                "Supported formats include: .py, .js, .ts, .java, .cpp, .html, .css, .md, .json, etc."
            )

        if progress_callback:
            progress_callback(
                f"Completed scan: {len(extracted_files)} files extracted across {len(languages_count)} languages.",
                45,
            )

        return extracted_files, languages_count

    def read_file(self, repo_dir: Path, rel_path: str) -> dict:
        """
        Safely read a specific file from the repository with path traversal protection.
        """
        safe_path = sanitize_repo_path(repo_dir, rel_path)
        if not safe_path.exists() or not safe_path.is_file():
            raise FileNotFoundError(f"File '{rel_path}' does not exist in repository.")

        try:
            content = safe_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = safe_path.read_text(encoding="latin-1", errors="replace")

        return {
            "file_path": rel_path.replace("\\", "/"),
            "file_name": safe_path.name,
            "language": detect_language(safe_path.name),
            "content": content,
            "lines_count": len(content.splitlines()),
        }
