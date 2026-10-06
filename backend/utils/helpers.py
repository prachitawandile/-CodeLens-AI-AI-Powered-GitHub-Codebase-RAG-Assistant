"""
Helper functions for URL validation, file language detection, path security, and tree building.
"""
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

# File extension to human-readable language mapping
EXTENSION_LANGUAGE_MAP: Dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "React JSX",
    ".ts": "TypeScript",
    ".tsx": "React TSX",
    ".java": "Java",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".c": "C",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "SASS",
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".txt": "Plain Text",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".xml": "XML",
    ".sql": "SQL",
    ".sh": "Shell Script",
    ".bash": "Shell Script",
    ".rs": "Rust",
    ".go": "Go",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
}

# Directories that must always be ignored
DEFAULT_IGNORE_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "__pycache__",
    "dist",
    "build",
    "coverage",
    ".coverage",
    "target",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".mypy_cache",
    ".next",
    ".nuxt",
    "bin",
    "obj",
    ".gradle",
    "vendor",
}

# Binary and non-text extensions to ignore
IGNORE_EXTENSIONS = {
    ".exe", ".dll", ".so", ".dylib", ".bin",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
    ".zip", ".tar", ".gz", ".7z", ".rar",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".pyc", ".pyo", ".pyd", ".class", ".jar",
    ".lock", ".wasm", ".parquet", ".pkl", ".pickle",
}


def parse_github_url(url: str) -> Tuple[str, str]:
    """
    Parse a GitHub repository URL into (owner, repo_name).
    Returns (owner, repo_name) or raises ValueError if invalid.
    
    Examples:
        https://github.com/torvalds/linux -> ("torvalds", "linux")
        https://github.com/psf/requests.git -> ("psf", "requests")
    """
    if not url or not isinstance(url, str):
        raise ValueError("GitHub URL cannot be empty.")

    cleaned_url = url.strip()
    # Normalize git+https or http to https
    if cleaned_url.startswith("git+"):
        cleaned_url = cleaned_url[4:]
    
    parsed = urlparse(cleaned_url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise ValueError(f"GitHub URL must use http:// or https:// scheme, got '{scheme}://'.")

    hostname = (parsed.hostname or "").lower()
    
    if hostname not in ("github.com", "www.github.com"):
        raise ValueError(f"URL must be a public github.com URL, got hostname '{hostname}'.")

    # Path should be /owner/repo or /owner/repo/
    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(path_parts) < 2:
        raise ValueError("GitHub URL must contain both an owner and repository name (e.g., https://github.com/owner/repo).")

    owner = path_parts[0]
    repo = path_parts[1]

    # Strip .git suffix if present
    if repo.endswith(".git"):
        repo = repo[:-4]

    # Validate characters (GitHub usernames and repo names allow alphanumeric, dashes, dots, underscores)
    valid_name_pattern = r"^[A-Za-z0-9_.-]+$"
    if not re.match(valid_name_pattern, owner) or not re.match(valid_name_pattern, repo):
        raise ValueError(f"Invalid characters in repository owner '{owner}' or name '{repo}'.")

    return owner, repo


def is_valid_github_url(url: str) -> bool:
    """Return True if the URL is a syntactically valid public GitHub repository URL."""
    try:
        parse_github_url(url)
        return True
    except ValueError:
        return False


def detect_language(file_path: str) -> str:
    """Detect programming/markup language based on file extension."""
    suffix = Path(file_path).suffix.lower()
    return EXTENSION_LANGUAGE_MAP.get(suffix, "Other")


def sanitize_repo_path(base_dir: Path, requested_path: str) -> Path:
    """
    Verify and sanitize a file path to prevent directory traversal attacks (FR-27).
    Ensures that resolved path stays strictly within base_dir.
    Raises PermissionError or ValueError if traversal is detected.
    """
    # Reject absolute path strings or Windows drive roots
    if requested_path.startswith("/") or requested_path.startswith("\\") or ":" in requested_path:
        # Strip leading slashes to evaluate as relative
        requested_path = requested_path.lstrip("/\\")

    resolved_base = base_dir.resolve()
    target_file = (base_dir / requested_path).resolve()

    try:
        # Python 3.9+ is_relative_to
        if not target_file.is_relative_to(resolved_base):
            raise PermissionError(f"Directory traversal detected: '{requested_path}' escapes repository boundary.")
    except AttributeError:
        # Fallback for earlier versions
        if resolved_base not in target_file.parents and resolved_base != target_file:
            raise PermissionError(f"Directory traversal detected: '{requested_path}' escapes repository boundary.")

    return target_file


def calculate_language_percentages(language_counts: Dict[str, int]) -> Dict[str, float]:
    """
    Calculate normalized language breakdown percentages.
    Example: {'Python': 62.5, 'JavaScript': 25.0, 'HTML': 12.5}
    """
    total = sum(language_counts.values())
    if total == 0:
        return {}

    percentages = {}
    for lang, count in language_counts.items():
        pct = round((count / total) * 100.0, 1)
        percentages[lang] = pct

    # Sort descending by percentage
    return dict(sorted(percentages.items(), key=lambda item: item[1], reverse=True))


def build_file_tree(files_metadata: List[dict]) -> List[dict]:
    """
    Build a nested tree structure suitable for the UI file explorer.
    Input files_metadata format: list of dicts with 'file_path', 'language', 'size_bytes'
    """
    root_nodes: Dict[str, dict] = {}

    for item in sorted(files_metadata, key=lambda x: x["file_path"]):
        rel_path = item["file_path"].replace("\\", "/")
        parts = rel_path.split("/")
        
        current_dict = root_nodes
        accumulated_path = ""

        for i, part in enumerate(parts):
            accumulated_path = f"{accumulated_path}/{part}" if accumulated_path else part
            is_last = (i == len(parts) - 1)

            if part not in current_dict:
                if is_last:
                    current_dict[part] = {
                        "name": part,
                        "path": accumulated_path,
                        "type": "file",
                        "language": item.get("language", "Text"),
                        "size_bytes": item.get("size_bytes", 0),
                        "children": None,
                    }
                else:
                    current_dict[part] = {
                        "name": part,
                        "path": accumulated_path,
                        "type": "directory",
                        "language": None,
                        "size_bytes": None,
                        "_children_map": {},
                    }

            if not is_last:
                current_dict = current_dict[part]["_children_map"]

    def _convert_map_to_list(mapping: Dict[str, dict]) -> List[dict]:
        nodes = []
        # Sort directories first, then files alphabetically
        sorted_keys = sorted(
            mapping.keys(),
            key=lambda k: (0 if mapping[k]["type"] == "directory" else 1, k.lower())
        )
        for k in sorted_keys:
            node = mapping[k]
            if node["type"] == "directory":
                node_copy = {
                    "name": node["name"],
                    "path": node["path"],
                    "type": "directory",
                    "language": None,
                    "size_bytes": None,
                    "children": _convert_map_to_list(node["_children_map"]),
                }
                nodes.append(node_copy)
            else:
                nodes.append(node)
        return nodes

    return _convert_map_to_list(root_nodes)
