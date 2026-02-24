"""
Unit tests for the Embedding Generation module.

Tests the sentence transformer-based embedding functionality including:
- Model loading and management
- Text chunking strategies
- Embedding generation (single and batch)
- Text preprocessing
- Token counting and estimation
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from kb.embeddings import EmbeddingGenerator


class TestEmbeddingGenerator:
    """Test suite for EmbeddingGenerator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = EmbeddingGenerator(model_name="all-MiniLM-L6-v2", device="cpu")

    def test_init(self):
        """Test initialization of EmbeddingGenerator."""
        assert self.generator.model_name == "all-MiniLM-L6-v2"
        assert self.generator.device == "cpu"
        assert self.generator.model is None
        assert self.generator.max_seq_length == 512
        assert self.generator.embedding_dimension == 384

    @patch('kb.embeddings.SentenceTransformer')
    def test_load_model(self, mock_sentence_transformer):
        """Test loading the sentence transformer model."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_sentence_transformer.return_value = mock_model

        self.generator.load_model()

        mock_sentence_transformer.assert_called_once_with("all-MiniLM-L6-v2", device="cpu")
        assert self.generator.model == mock_model

    def test_count_tokens_fallback(self):
        """Test token counting with fallback method."""
        text = "Hello world this is a test"
        tokens = self.generator.count_tokens(text)

        # Fallback method: len(text) // 4
        expected = len(text) // 4
        assert tokens == expected

    def test_preprocess_text(self):
        """Test text preprocessing."""
        # Test normal text
        text = "  Hello   world!\n\nThis is a test.  "
        processed = self.generator.preprocess_text(text)
        assert processed == "Hello world! This is a test."

        # Test empty text
        assert self.generator.preprocess_text("") == ""
        assert self.generator.preprocess_text("   ") == ""

    def test_chunk_text_empty(self):
        """Test chunking empty text."""
        chunks = self.generator.chunk_text("")
        assert chunks == []

        chunks = self.generator.chunk_text("   ")
        assert chunks == []

    def test_chunk_by_sentences(self):
        """Test sentence-based chunking."""
        text = "This is the first sentence. This is the second sentence! This is the third sentence?"

        chunks = self.generator.chunk_text(text, chunk_size=10, overlap=2, strategy="sentence")

        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)
        assert all(len(chunk.strip()) > 0 for chunk in chunks)

        # Check that sentences are preserved
        assert "first sentence" in chunks[0].lower()

    def test_chunk_by_paragraphs(self):
        """Test paragraph-based chunking."""
        text = "First paragraph with some content.\n\nSecond paragraph with more content.\n\nThird paragraph."

        chunks = self.generator.chunk_text(text, chunk_size=20, overlap=5, strategy="paragraph")

        assert len(chunks) > 0
        # Should contain paragraph breaks
        assert any("\n\n" in chunk for chunk in chunks)

    def test_chunk_fixed_size(self):
        """Test fixed-size chunking."""
        text = "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10"

        chunks = self.generator.chunk_text(text, chunk_size=5, overlap=2, strategy="fixed")

        assert len(chunks) > 1
        # Check overlap - later chunks should contain words from earlier chunks
        assert "word4" in chunks[1]  # Should overlap with previous chunk

    def test_chunk_text_invalid_strategy(self):
        """Test error for invalid chunking strategy."""
        with pytest.raises(ValueError, match="Unknown chunking strategy"):
            self.generator.chunk_text("test text", strategy="invalid")

    @patch('kb.embeddings.SentenceTransformer')
    def test_generate_embeddings(self, mock_sentence_transformer):
        """Test batch embedding generation."""
        # Mock the model
        mock_model = MagicMock()
        embeddings = np.random.rand(3, 384).astype(np.float32)
        mock_model.encode.return_value = embeddings
        mock_sentence_transformer.return_value = mock_model

        self.generator.load_model()

        texts = ["Text 1", "Text 2", "Text 3"]
        result = self.generator.generate_embeddings(texts, batch_size=2, show_progress=False)

        assert isinstance(result, np.ndarray)
        assert result.shape == (3, 384)
        mock_model.encode.assert_called_once()

    @patch('kb.embeddings.SentenceTransformer')
    def test_generate_embeddings_empty_list(self, mock_sentence_transformer):
        """Test embedding generation with empty text list."""
        mock_model = MagicMock()
        mock_sentence_transformer.return_value = mock_model

        self.generator.load_model()

        result = self.generator.generate_embeddings([], show_progress=False)

        assert isinstance(result, np.ndarray)
        assert result.shape == (0, 384)
        mock_model.encode.assert_not_called()

    @patch('kb.embeddings.SentenceTransformer')
    def test_generate_embedding_single(self, mock_sentence_transformer):
        """Test single text embedding generation."""
        mock_model = MagicMock()
        embedding = np.random.rand(384).astype(np.float32)
        mock_model.encode.return_value = np.array([embedding])
        mock_sentence_transformer.return_value = mock_model

        self.generator.load_model()

        result = self.generator.generate_embedding("Test text")

        assert isinstance(result, np.ndarray)
        assert result.shape == (384,)
        np.testing.assert_array_equal(result, embedding)

    def test_generate_embedding_without_model(self):
        """Test error when generating embeddings without loading model."""
        with pytest.raises(ValueError, match="Model not loaded"):
            self.generator.generate_embeddings(["test"])

    def test_get_model_info_without_model(self):
        """Test getting model info when no model is loaded."""
        info = self.generator.get_model_info()
        assert info["status"] == "model_not_loaded"

    @patch('kb.embeddings.SentenceTransformer')
    def test_get_model_info_with_model(self, mock_sentence_transformer):
        """Test getting model info when model is loaded."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_sentence_transformer.return_value = mock_model

        self.generator.load_model()

        info = self.generator.get_model_info()
        assert info["model_name"] == "all-MiniLM-L6-v2"
        assert info["device"] == "cpu"
        assert info["embedding_dimension"] == 384

    def test_estimate_tokens(self):
        """Test token estimation for text lists."""
        texts = ["Hello world", "This is a test", "Another text here"]

        stats = self.generator.estimate_tokens(texts)

        assert stats["total_texts"] == 3
        assert stats["total_tokens"] > 0
        assert stats["avg_tokens"] > 0
        assert stats["max_tokens"] >= stats["min_tokens"]

    def test_estimate_tokens_empty(self):
        """Test token estimation for empty list."""
        stats = self.generator.estimate_tokens([])

        assert stats["total_texts"] == 0
        assert stats["total_tokens"] == 0
        assert stats["avg_tokens"] == 0
        assert stats["max_tokens"] == 0

    def test_chunk_text_long_document(self):
        """Test chunking a longer document."""
        # Create a longer text with multiple sentences
        sentences = [
            "This is the first sentence in our test document.",
            "It contains multiple sentences that should be chunked appropriately.",
            "The chunking algorithm should handle overlaps correctly.",
            "Each chunk should maintain coherence and context.",
            "This helps ensure that embeddings capture meaningful relationships."
        ]
        text = " ".join(sentences)

        chunks = self.generator.chunk_text(text, chunk_size=20, overlap=5, strategy="sentence")

        assert len(chunks) > 1
        # Verify that chunks contain actual content
        assert all(len(chunk.strip()) > 0 for chunk in chunks)
        # Check that some sentences appear in chunks
        assert any("first sentence" in chunk.lower() for chunk in chunks)

    def test_preprocess_text_special_characters(self):
        """Test preprocessing with special characters."""
        text = "Hello\x00world\x01test\x7fnormal"
        processed = self.generator.preprocess_text(text)

        # Control characters should be removed
        assert "\x00" not in processed
        assert "\x01" not in processed
        assert "\x7f" not in processed
        assert "Helloworldtestnormal" == processed