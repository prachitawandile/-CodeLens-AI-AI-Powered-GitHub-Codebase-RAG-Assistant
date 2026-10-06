"""
Unit tests for line-based overlapping ChunkingService.
"""
import pytest
from backend.services.chunking_service import ChunkingService


def test_chunking_small_file():
    service = ChunkingService(chunk_size=100, chunk_overlap=15)
    file_info = {
        "repository": "my_repo",
        "file_path": "main.py",
        "file_name": "main.py",
        "language": "Python",
        "content": "line 1\nline 2\nline 3\nline 4\nline 5",
    }
    chunks = service.chunk_file(file_info)
    assert len(chunks) == 1
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 5
    assert chunks[0].chunk_index == 0
    assert "line 1" in chunks[0].text
    assert "File: main.py" in chunks[0].text


def test_chunking_large_file_with_overlap():
    service = ChunkingService(chunk_size=50, chunk_overlap=10)
    # Generate 120 lines
    content = "\n".join([f"code_statement_{i}" for i in range(1, 121)])
    file_info = {
        "repository": "my_repo",
        "file_path": "service.py",
        "file_name": "service.py",
        "language": "Python",
        "content": content,
    }
    chunks = service.chunk_file(file_info)

    # Step is 50 - 10 = 40 lines
    # Chunk 0: lines 1-50
    # Chunk 1: lines 41-90
    # Chunk 2: lines 81-120
    assert len(chunks) == 3
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 50

    assert chunks[1].start_line == 41
    assert chunks[1].end_line == 90

    assert chunks[2].start_line == 81
    assert chunks[2].end_line == 120

    # Overlap check
    assert "code_statement_45" in chunks[0].text
    assert "code_statement_45" in chunks[1].text


def test_chunking_invalid_parameters():
    with pytest.raises(ValueError):
        ChunkingService(chunk_size=0)

    with pytest.raises(ValueError):
        ChunkingService(chunk_size=50, chunk_overlap=50)

    with pytest.raises(ValueError):
        ChunkingService(chunk_size=50, chunk_overlap=60)
