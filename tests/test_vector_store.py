"""
Unit tests for VectorStoreService using ChromaDB.
"""
from backend.services.vector_store import VectorStoreService


def test_vector_store_add_and_query(tmp_path):
    store = VectorStoreService(persist_dir=str(tmp_path / "chroma_test"))
    repo_id = "test_owner__test_repo"

    # Dummy chunks and 4-dimensional normalized embeddings for testing
    chunks = [
        {
            "chunk_id": "chunk_auth_1",
            "text": "def login_user(username, password): pass",
            "metadata": {
                "file_path": "auth.py",
                "file_name": "auth.py",
                "language": "Python",
                "start_line": 1,
                "end_line": 10,
                "chunk_index": 0,
            },
        },
        {
            "chunk_id": "chunk_db_1",
            "text": "def connect_postgres(db_url): pass",
            "metadata": {
                "file_path": "database.py",
                "file_name": "database.py",
                "language": "Python",
                "start_line": 1,
                "end_line": 12,
                "chunk_index": 0,
            },
        },
    ]

    # Two distinct vectors
    embeddings = [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
    ]

    added = store.add_chunks(repo_id, chunks, embeddings)
    assert added == 2
    assert store.collection_exists(repo_id) is True
    assert store.get_collection_count(repo_id) == 2

    # Query matching chunk 1
    query_vector = [0.95, 0.05, 0.0, 0.0]
    results = store.query(repo_id, query_vector, top_k=1)

    assert len(results) == 1
    assert results[0]["file_name"] == "auth.py"
    assert results[0]["similarity_score"] > 0.8
