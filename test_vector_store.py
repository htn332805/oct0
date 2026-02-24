"""
Unit tests for the Vector Store module.

Tests the FAISS-based vector store functionality including:
- Index creation and management
- Vector addition and search
- Persistence and loading
- Error handling
"""

import pytest
import numpy as np
import tempfile
import os
import json
from pathlib import Path
from kb.vector_store import VectorStore


class TestVectorStore:
    """Test suite for VectorStore class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.index_path = os.path.join(self.temp_dir, "test_index.faiss")
        self.dimension = 384

    def teardown_method(self):
        """Clean up test fixtures."""
        # Remove test files
        for file in Path(self.temp_dir).glob("*"):
            file.unlink()
        os.rmdir(self.temp_dir)

    def test_create_index(self):
        """Test creating a new FAISS index."""
        store = VectorStore(self.index_path, self.dimension)
        store.create_index()

        assert store.index is not None
        assert store.index.d == self.dimension
        assert store.index.ntotal == 0

    def test_add_vectors(self):
        """Test adding vectors to the index."""
        store = VectorStore(self.index_path, self.dimension)
        store.create_index()

        # Create test vectors
        vectors = np.random.rand(3, self.dimension).astype(np.float32)
        metadata = [
            {"text": "First document", "type": "note"},
            {"text": "Second document", "type": "flashcard"},
            {"text": "Third document", "type": "summary"}
        ]

        # Add vectors
        ids = store.add_vectors(vectors, metadata)

        # Verify
        assert len(ids) == 3
        assert ids == [0, 1, 2]
        assert store.index.ntotal == 3
        assert len(store.metadata) == 3

        # Check metadata storage
        for i, meta in enumerate(metadata):
            assert store.metadata[i] == meta

    def test_add_vectors_dimension_mismatch(self):
        """Test error when vector dimension doesn't match index."""
        store = VectorStore(self.index_path, self.dimension)
        store.create_index()

        # Create vectors with wrong dimension
        vectors = np.random.rand(2, self.dimension + 1).astype(np.float32)
        metadata = [{"text": "test"}] * 2

        with pytest.raises(ValueError, match="Vector dimension .* does not match"):
            store.add_vectors(vectors, metadata)

    def test_add_vectors_metadata_mismatch(self):
        """Test error when number of vectors doesn't match metadata."""
        store = VectorStore(self.index_path, self.dimension)
        store.create_index()

        vectors = np.random.rand(2, self.dimension).astype(np.float32)
        metadata = [{"text": "test"}]  # Only one metadata entry

        with pytest.raises(ValueError, match="Number of vectors must match"):
            store.add_vectors(vectors, metadata)

    def test_search_vectors(self):
        """Test searching for similar vectors."""
        store = VectorStore(self.index_path, self.dimension)
        store.create_index()

        # Add some test vectors
        vectors = np.array([
            [1.0] + [0.0] * (self.dimension - 1),  # Unit vector along x-axis
            [0.0, 1.0] + [0.0] * (self.dimension - 2),  # Unit vector along y-axis
            [0.5, 0.5] + [0.0] * (self.dimension - 2),  # 45-degree vector
        ], dtype=np.float32)

        metadata = [
            {"text": "x-axis vector"},
            {"text": "y-axis vector"},
            {"text": "diagonal vector"}
        ]

        store.add_vectors(vectors, metadata)

        # Search with the x-axis vector as query
        query = np.array([1.0] + [0.0] * (self.dimension - 1), dtype=np.float32)
        results = store.search_vectors(query, k=2)

        # Should find the x-axis vector as most similar
        assert len(results) == 2
        assert results[0][0] == 0  # First vector (x-axis) should be most similar
        assert results[0][1] > 0.99  # High similarity score
        assert results[0][2]["text"] == "x-axis vector"

    def test_search_vectors_empty_index(self):
        """Test searching in an empty index."""
        store = VectorStore(self.index_path, self.dimension)
        store.create_index()

        query = np.random.rand(self.dimension).astype(np.float32)
        results = store.search_vectors(query, k=5)

        assert len(results) == 0

    def test_save_and_load_index(self):
        """Test saving and loading index with metadata."""
        # Create and populate index
        store = VectorStore(self.index_path, self.dimension)
        store.create_index()

        vectors = np.random.rand(2, self.dimension).astype(np.float32)
        metadata = [
            {"text": "Document 1", "type": "note"},
            {"text": "Document 2", "type": "flashcard"}
        ]

        ids = store.add_vectors(vectors, metadata)
        store.save_index()

        # Create new store and load
        new_store = VectorStore(self.index_path, self.dimension)
        loaded = new_store.load_index()

        assert loaded
        assert new_store.index.ntotal == 2
        assert len(new_store.metadata) == 2
        assert new_store.id_counter == 2

        # Verify metadata
        assert new_store.metadata[0] == metadata[0]
        assert new_store.metadata[1] == metadata[1]

    def test_load_nonexistent_index(self):
        """Test loading an index that doesn't exist."""
        store = VectorStore("/nonexistent/path/index.faiss", self.dimension)
        loaded = store.load_index()

        assert not loaded
        assert store.index is None

    def test_save_without_index(self):
        """Test error when trying to save without an index."""
        store = VectorStore(self.index_path, self.dimension)

        with pytest.raises(ValueError, match="No index to save"):
            store.save_index()

    def test_get_stats(self):
        """Test getting index statistics."""
        store = VectorStore(self.index_path, self.dimension)

        # No index
        stats = store.get_stats()
        assert stats["status"] == "no_index"

        # With index
        store.create_index()
        vectors = np.random.rand(3, self.dimension).astype(np.float32)
        metadata = [{"text": f"doc{i}"} for i in range(3)]
        store.add_vectors(vectors, metadata)

        stats = store.get_stats()
        assert stats["total_vectors"] == 3
        assert stats["dimension"] == self.dimension
        assert stats["metadata_entries"] == 3

    def test_clear_index(self):
        """Test clearing all vectors and metadata."""
        store = VectorStore(self.index_path, self.dimension)
        store.create_index()

        # Add some data
        vectors = np.random.rand(2, self.dimension).astype(np.float32)
        metadata = [{"text": "test"}] * 2
        store.add_vectors(vectors, metadata)

        assert store.index.ntotal == 2
        assert len(store.metadata) == 2

        # Clear
        store.clear_index()

        assert store.index.ntotal == 0
        assert len(store.metadata) == 0
        assert store.id_counter == 0

    def test_zero_vector_handling(self):
        """Test handling of zero vectors in search."""
        store = VectorStore(self.index_path, self.dimension)
        store.create_index()

        # Add a normal vector
        vectors = np.random.rand(1, self.dimension).astype(np.float32)
        metadata = [{"text": "normal vector"}]
        store.add_vectors(vectors, metadata)

        # Search with zero vector
        query = np.zeros(self.dimension, dtype=np.float32)
        results = store.search_vectors(query, k=1)

        # Should still return results (though similarity might be low)
        assert len(results) == 1