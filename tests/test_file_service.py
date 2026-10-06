"""
Unit tests for FileService scanning, filtering, and path traversal security.
"""
from pathlib import Path
import pytest
from backend.services.file_service import FileService
from backend.utils.helpers import sanitize_repo_path


def test_file_filtering_and_extraction(tmp_path):
    # Setup test repository structure
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    # Supported files
    (repo_dir / "main.py").write_text("print('hello world')", encoding="utf-8")
    (repo_dir / "README.md").write_text("# Test Repo\nDocumentation", encoding="utf-8")
    
    # Subdirectory
    sub = repo_dir / "src"
    sub.mkdir()
    (sub / "app.js").write_text("console.log('test');", encoding="utf-8")

    # Ignored directory (node_modules)
    nm = repo_dir / "node_modules"
    nm.mkdir()
    (nm / "package.json").write_text("{}", encoding="utf-8")

    # Ignored binary extension
    (repo_dir / "test.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    service = FileService()
    files, lang_counts = service.scan_and_extract(repo_dir, "test_repo")

    # Only main.py, README.md, src/app.js should be extracted
    extracted_paths = [f["file_path"].replace("\\", "/") for f in files]
    assert "main.py" in extracted_paths
    assert "README.md" in extracted_paths
    assert "src/app.js" in extracted_paths
    assert not any("node_modules" in p for p in extracted_paths)
    assert not any(p.endswith(".png") for p in extracted_paths)

    assert lang_counts.get("Python") == 1
    assert lang_counts.get("Markdown") == 1
    assert lang_counts.get("JavaScript") == 1


def test_path_traversal_prevention(tmp_path):
    repo_dir = tmp_path / "safe_repo"
    repo_dir.mkdir()
    (repo_dir / "safe.py").write_text("# safe", encoding="utf-8")

    # Safe access
    resolved = sanitize_repo_path(repo_dir, "safe.py")
    assert resolved.exists()

    # Traversal attack
    with pytest.raises((PermissionError, ValueError)):
        sanitize_repo_path(repo_dir, "../../secret.txt")
