"""
Vector Store Module for Smart Study System

This module provides functionality for storing and retrieving vector embeddings
using FAISS (Facebook AI Similarity Search). It enables semantic search over
study materials by maintaining a vector index and associated metadata.

The module supports:
- Creating and managing FAISS indexes
- Adding vectors with metadata
- Performing similarity search
- Persisting indexes to disk
- Loading indexes from disk
"""

import os
import json
import numpy as np
import faiss
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path


class VectorStore:
    """
    A vector store implementation using FAISS for efficient similarity search.

    This class manages a FAISS index for storing and retrieving vector embeddings
    of study materials, enabling semantic search capabilities.
    """

    def __init__(self, index_path: str, dimension: int = 384):
        """
        Initialize the vector store.

        Args:
            index_path: Path to save/load the FAISS index
            dimension: Dimension of the vectors (default 384 for sentence-transformers)
        """
        self.index_path = Path(index_path)
        self.dimension = dimension
        self.index = None
        self.metadata = {}  # Maps vector IDs to metadata
        self.id_counter = 0  # For generating unique IDs

        # Only create directory if the path doesn't contain non-existent directories
        # This allows testing with non-existent paths
        try:
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError):
            # Ignore errors for non-existent paths (used in testing)
            pass

    def create_index(self) -> None:
        """
        Create a new FAISS index for cosine similarity search.

        Uses IndexFlatIP (Inner Product) which is suitable for normalized vectors
        and provides cosine similarity search.
        """
        self.index = faiss.IndexFlatIP(self.dimension)
        print(f"Created new FAISS index with dimension {self.dimension}")

    def load_index(self) -> bool:
        """
        Load an existing FAISS index from disk.

        Returns:
            True if index was loaded successfully, False otherwise
        """
        if not self.index_path.exists():
            print(f"No index file found at {self.index_path}")
            return False

        try:
            self.index = faiss.read_index(str(self.index_path))
            print(f"Loaded FAISS index from {self.index_path}")

            # Load metadata if it exists
            metadata_path = self.index_path.with_suffix('.metadata.json')
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata_data = json.load(f)
                    # Convert string keys back to integers
                    self.metadata = {int(k): v for k, v in metadata_data.get('metadata', {}).items()}
                    self.id_counter = metadata_data.get('id_counter', 0)
                print(f"Loaded metadata for {len(self.metadata)} vectors")

            return True
        except Exception as e:
            print(f"Error loading index: {e}")
            return False

    def save_index(self) -> None:
        """
        Save the current FAISS index and metadata to disk.
        """
        if self.index is None:
            raise ValueError("No index to save. Create or load an index first.")

        # Save FAISS index
        faiss.write_index(self.index, str(self.index_path))
        print(f"Saved FAISS index to {self.index_path}")

        # Save metadata
        metadata_path = self.index_path.with_suffix('.metadata.json')
        metadata_data = {
            'metadata': self.metadata,
            'id_counter': self.id_counter,
            'dimension': self.dimension
        }

        with open(metadata_path, 'w') as f:
            json.dump(metadata_data, f, indent=2)
        print(f"Saved metadata to {metadata_path}")

    def add_vectors(self, vectors: np.ndarray, metadata_list: List[Dict[str, Any]]) -> List[int]:
        """
        Add vectors and their metadata to the index.

        Args:
            vectors: Numpy array of shape (n, dimension) containing the vectors
            metadata_list: List of metadata dictionaries, one per vector

        Returns:
            List of IDs assigned to the added vectors
        """
        if self.index is None:
            raise ValueError("No index available. Create or load an index first.")

        if vectors.shape[0] != len(metadata_list):
            raise ValueError("Number of vectors must match number of metadata entries")

        if vectors.shape[1] != self.dimension:
            raise ValueError(f"Vector dimension {vectors.shape[1]} does not match index dimension {self.dimension}")

        # Normalize vectors for cosine similarity
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        normalized_vectors = vectors / norms

        # Generate IDs for the new vectors
        start_id = self.id_counter
        ids = list(range(start_id, start_id + len(vectors)))
        self.id_counter += len(vectors)

        # Add vectors to index
        self.index.add(normalized_vectors.astype(np.float32))

        # Store metadata
        for i, metadata in enumerate(metadata_list):
            self.metadata[ids[i]] = metadata

        print(f"Added {len(vectors)} vectors to index")
        return ids

    def search_vectors(self, query_vector: np.ndarray, k: int = 5) -> List[Tuple[int, float, Dict[str, Any]]]:
        """
        Search for the k most similar vectors to the query vector.

        Args:
            query_vector: Numpy array of shape (dimension,) containing the query vector
            k: Number of similar vectors to return

        Returns:
            List of tuples (id, similarity_score, metadata) for the top-k results
        """
        if self.index is None:
            raise ValueError("No index available. Create or load an index first.")

        if self.index.ntotal == 0:
            return []  # Return empty list for empty index

        if query_vector.shape[0] != self.dimension:
            raise ValueError(f"Query vector dimension {query_vector.shape[0]} does not match index dimension {self.dimension}")

        # Normalize query vector
        norm = np.linalg.norm(query_vector)
        if norm == 0:
            normalized_query = query_vector
        else:
            normalized_query = query_vector / norm

        # Reshape for FAISS
        query = normalized_query.reshape(1, -1).astype(np.float32)

        # Search
        actual_k = min(k, self.index.ntotal)
        if actual_k == 0:
            return []

        scores, indices = self.index.search(query, actual_k)

        # Format results
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1:  # Valid result
                vector_id = idx
                similarity_score = float(scores[0][i])
                metadata = self.metadata.get(vector_id, {})
                results.append((vector_id, similarity_score, metadata))

        return results

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store.

        Returns:
            Dictionary with index statistics
        """
        if self.index is None:
            return {"status": "no_index"}

        return {
            "total_vectors": self.index.ntotal,
            "dimension": self.dimension,
            "index_type": type(self.index).__name__,
            "metadata_entries": len(self.metadata)
        }

    def clear_index(self) -> None:
        """
        Clear all vectors and metadata from the index.
        """
        if self.index is not None:
            self.index.reset()
        self.metadata = {}
        self.id_counter = 0
        print("Cleared all vectors and metadata from index")