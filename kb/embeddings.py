"""
Embedding Generation Module for Smart Study System

This module provides functionality for generating vector embeddings from text
using sentence transformers. It handles text preprocessing, chunking for long
documents, and batch processing for efficiency.

The module supports:
- Loading and managing sentence transformer models
- Text chunking with configurable strategies
- Batch embedding generation
- Memory-efficient processing
- Integration with the vector store
"""

import re
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from sentence_transformers import SentenceTransformer
import tiktoken  # For token counting
from pathlib import Path


class EmbeddingGenerator:
    """
    A text embedding generator using sentence transformers.

    This class handles converting text documents into vector embeddings
    that can be stored and searched in the vector database.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "cpu"):
        """
        Initialize the embedding generator.

        Args:
            model_name: Name of the sentence transformer model to use
            device: Device to run the model on ('cpu' or 'cuda')
        """
        self.model_name = model_name
        self.device = device
        self.model = None
        self.tokenizer = None

        # Model parameters
        self.max_seq_length = 512  # Maximum sequence length for the model
        self.embedding_dimension = 384  # Dimension for all-MiniLM-L6-v2

    def load_model(self) -> None:
        """
        Load the sentence transformer model.

        This is a separate method to allow lazy loading and better control
        over when the model is loaded into memory.
        """
        if self.model is None:
            print(f"Loading sentence transformer model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name, device=self.device)

            # Initialize tokenizer for token counting
            try:
                self.tokenizer = tiktoken.get_encoding("cl100k_base")  # GPT-3.5/4 tokenizer
            except:
                # Fallback if tiktoken is not available
                self.tokenizer = None

            print(f"Model loaded successfully. Embedding dimension: {self.model.get_sentence_embedding_dimension()}")

    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text string.

        Args:
            text: Input text

        Returns:
            Number of tokens
        """
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Rough approximation: 1 token ≈ 4 characters for English text
            return len(text) // 4

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50,
                   strategy: str = "sentence") -> List[str]:
        """
        Split long text into smaller chunks for embedding.

        Args:
            text: The text to chunk
            chunk_size: Maximum number of tokens per chunk
            overlap: Number of tokens to overlap between chunks
            strategy: Chunking strategy ('sentence', 'paragraph', 'fixed')

        Returns:
            List of text chunks
        """
        if not text.strip():
            return []

        if strategy == "sentence":
            return self._chunk_by_sentences(text, chunk_size, overlap)
        elif strategy == "paragraph":
            return self._chunk_by_paragraphs(text, chunk_size, overlap)
        elif strategy == "fixed":
            return self._chunk_fixed_size(text, chunk_size, overlap)
        else:
            raise ValueError(f"Unknown chunking strategy: {strategy}")

    def _chunk_by_sentences(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Chunk text by sentences."""
        # Split by sentence endings
        sentence_pattern = r'(?<=[.!?])\s+'
        sentences = re.split(sentence_pattern, text.strip())

        chunks = []
        current_chunk = ""
        current_tokens = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_tokens = self.count_tokens(sentence)

            # If adding this sentence would exceed chunk size
            if current_tokens + sentence_tokens > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                # Start new chunk with overlap from previous chunk
                overlap_text = self._get_overlap_text(current_chunk, overlap)
                current_chunk = overlap_text + " " + sentence
                current_tokens = self.count_tokens(current_chunk)
            else:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
                current_tokens += sentence_tokens

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _chunk_by_paragraphs(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Chunk text by paragraphs."""
        paragraphs = text.split('\n\n')
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        chunks = []
        current_chunk = ""
        current_tokens = 0

        for paragraph in paragraphs:
            paragraph_tokens = self.count_tokens(paragraph)

            if current_tokens + paragraph_tokens > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                overlap_text = self._get_overlap_text(current_chunk, overlap)
                current_chunk = overlap_text + "\n\n" + paragraph
                current_tokens = self.count_tokens(current_chunk)
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
                current_tokens += paragraph_tokens

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _chunk_fixed_size(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Chunk text into fixed-size pieces."""
        words = text.split()
        chunks = []
        i = 0

        while i < len(words):
            chunk_words = words[i:i + chunk_size]
            chunk_text = " ".join(chunk_words)
            chunks.append(chunk_text)

            # Move forward by chunk_size - overlap
            i += max(1, chunk_size - overlap)

        return chunks

    def _get_overlap_text(self, text: str, overlap_tokens: int) -> str:
        """Extract overlap text from the end of a chunk."""
        words = text.split()
        overlap_words = []
        current_tokens = 0

        for word in reversed(words):
            word_tokens = self.count_tokens(word)
            if current_tokens + word_tokens > overlap_tokens:
                break
            overlap_words.insert(0, word)
            current_tokens += word_tokens

        return " ".join(overlap_words)

    def generate_embeddings(self, texts: List[str], batch_size: int = 32,
                           show_progress: bool = True) -> np.ndarray:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed
            batch_size: Number of texts to process in each batch
            show_progress: Whether to show progress information

        Returns:
            Numpy array of shape (n_texts, embedding_dimension)
        """
        if self.model is None:
            raise ValueError("Model not loaded. Call load_model() first.")

        if not texts:
            return np.array([]).reshape(0, self.embedding_dimension)

        if show_progress:
            print(f"Generating embeddings for {len(texts)} texts using batch size {batch_size}")

        # Generate embeddings
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=True  # Normalize for cosine similarity
        )

        if show_progress:
            print(f"Generated embeddings with shape: {embeddings.shape}")

        return embeddings

    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Numpy array of shape (embedding_dimension,)
        """
        embeddings = self.generate_embeddings([text], batch_size=1, show_progress=False)
        return embeddings[0] if len(embeddings) > 0 else np.array([])

    def preprocess_text(self, text: str) -> str:
        """
        Preprocess text before embedding.

        Args:
            text: Raw text

        Returns:
            Preprocessed text
        """
        if not text:
            return ""

        # Basic preprocessing
        text = text.strip()

        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove control characters but keep newlines
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)

        return text

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model.

        Returns:
            Dictionary with model information
        """
        if self.model is None:
            return {"status": "model_not_loaded"}

        return {
            "model_name": self.model_name,
            "device": self.device,
            "embedding_dimension": self.model.get_sentence_embedding_dimension(),
            "max_seq_length": self.max_seq_length,
            "tokenizer_available": self.tokenizer is not None
        }

    def estimate_tokens(self, texts: List[str]) -> Dict[str, Any]:
        """
        Estimate token counts for a list of texts.

        Args:
            texts: List of texts to analyze

        Returns:
            Dictionary with token statistics
        """
        if not texts:
            return {"total_texts": 0, "total_tokens": 0, "avg_tokens": 0, "max_tokens": 0}

        token_counts = [self.count_tokens(text) for text in texts]

        return {
            "total_texts": len(texts),
            "total_tokens": sum(token_counts),
            "avg_tokens": sum(token_counts) / len(token_counts),
            "max_tokens": max(token_counts),
            "min_tokens": min(token_counts)
        }