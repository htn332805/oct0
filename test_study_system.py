"""
Tests for Study System Integration Layer - Part 3

Tests the integration of all core modules:
- Copilot client integration
- Vector store operations
- Embedding generation
- Metadata database operations
- End-to-end study workflows
"""

import os
import tempfile
import unittest
import json
from unittest.mock import patch, MagicMock
import numpy as np
from datetime import datetime

from kb.study_system import StudySystem


class TestStudySystem(unittest.TestCase):
    """Test cases for the integrated study system."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_study.db")
        self.vector_store_path = os.path.join(self.temp_dir, "vectors.index")

        # Initialize study system with mocked components
        with patch('kb.study_system.CopilotClient'), \
             patch('kb.study_system.EmbeddingGenerator'), \
             patch('kb.study_system.VectorStore') as mock_vector_store, \
             patch('kb.study_system.MetadataDB') as mock_metadata_db:

            # Configure mocks
            self.mock_copilot = MagicMock()
            self.mock_embeddings = MagicMock()
            self.mock_vector_store = MagicMock()
            self.mock_metadata_db = MagicMock()

            # Set up mock returns
            mock_vector_store.return_value = self.mock_vector_store
            mock_metadata_db.return_value = self.mock_metadata_db

            self.study_system = StudySystem(db_path=self.db_path)
            self.study_system.copilot = self.mock_copilot
            self.study_system.embeddings = self.mock_embeddings
            self.study_system.vector_store = self.mock_vector_store
            self.study_system.metadata_db = self.mock_metadata_db

    def tearDown(self):
        """Clean up test environment."""
        if hasattr(self.study_system, 'metadata_db') and self.study_system.metadata_db.connection:
            self.study_system.metadata_db.connection.close()

        # Clean up temp files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('scripts.copilot_client.CopilotClient.generate_flashcards')
    def test_generate_study_content_flashcards(self, mock_generate):
        """Test generating flashcard content."""
        mock_generate.return_value = {
            "cards": [
                {"question": "What is AI?", "answer": "Artificial Intelligence"}
            ]
        }

        result = self.study_system.generate_study_content(
            topic="Artificial Intelligence",
            content_type="flashcards",
            difficulty="intermediate"
        )

        self.assertIn("document_id", result)
        self.assertEqual(result["topic"], "Artificial Intelligence")
        self.assertEqual(result["content_type"], "flashcards")
        self.assertEqual(result["difficulty"], "intermediate")
        mock_generate.assert_called_once_with("Artificial Intelligence", "intermediate")

    @patch('scripts.copilot_client.CopilotClient.generate_summary')
    def test_generate_study_content_summary(self, mock_generate):
        """Test generating summary content."""
        mock_generate.return_value = {"summary": "AI is the simulation of human intelligence."}

        result = self.study_system.generate_study_content(
            topic="AI Overview",
            content_type="summary"
        )

        self.assertIn("document_id", result)
        self.assertEqual(result["content_type"], "summary")
        mock_generate.assert_called_once_with("AI Overview")

    def test_add_study_material(self):
        """Test adding study material to the system."""
        # Mock the embeddings and vector store
        self.mock_embeddings.generate_embeddings.return_value = [np.random.rand(384) for _ in range(1)]
        self.mock_metadata_db.add_document.return_value = 1

        doc_id = self.study_system.add_study_material(
            title="Test Document",
            content="This is a test document with some content for testing purposes.",
            source_type="note",
            tags=["test", "sample"]
        )

        # Verify metadata database was called
        self.mock_metadata_db.add_document.assert_called_once()
        args = self.mock_metadata_db.add_document.call_args[1]
        self.assertEqual(args["title"], "Test Document")
        self.assertEqual(args["document_type"], "note")

        # Verify embeddings were generated
        self.mock_embeddings.generate_embeddings.assert_called_once()

        # Verify vector store was updated
        self.mock_vector_store.add_vectors.assert_called_once()

    def test_search_knowledge(self):
        """Test knowledge search using vector similarity."""
        # Add some test content
        content1 = "Machine learning is a subset of artificial intelligence."
        content2 = "Deep learning uses neural networks with multiple layers."

        doc_id1 = self.study_system.add_study_material("ML Intro", content1, tags=["ml", "ai"])
        doc_id2 = self.study_system.add_study_material("Deep Learning", content2, tags=["deep-learning", "ai"])

        # Search for related content
        results = self.study_system.search_knowledge("artificial intelligence", limit=2)

        self.assertIsInstance(results, list)
        self.assertGreaterEqual(len(results), 1)  # At least one result

        # Check result structure
        if results:
            result = results[0]
            self.assertIn("document", result)
            self.assertIn("similarity_score", result)
            self.assertIn("metadata", result)

    def test_search_documents(self):
        """Test document search using full-text search."""
        # Add test documents
        self.study_system.add_study_material(
            "Python Programming",
            "Python is a high-level programming language known for its simplicity.",
            tags=["programming", "python"]
        )
        self.study_system.add_study_material(
            "Java Programming",
            "Java is an object-oriented programming language used for enterprise applications.",
            tags=["programming", "java"]
        )

        # Search for programming content
        results = self.study_system.search_documents("programming", limit=5)

        self.assertIsInstance(results, list)
        self.assertGreaterEqual(len(results), 2)  # Should find both documents

        # Check that results contain the search term
        titles = [r["title"] for r in results]
        self.assertIn("Python Programming", titles)
        self.assertIn("Java Programming", titles)

    def test_topic_management(self):
        """Test topic creation and document assignment."""
        # Create a topic
        topic_id = self.study_system.create_topic(
            name="Programming Languages",
            description="Various programming languages and their uses",
            color="#FF6B6B"
        )

        self.assertIsInstance(topic_id, int)
        self.assertGreater(topic_id, 0)

        # Add documents to the topic
        doc_id1 = self.study_system.add_study_material("Python Guide", "Python programming guide")
        doc_id2 = self.study_system.add_study_material("Java Guide", "Java programming guide")

        # Assign documents to topic
        success1 = self.study_system.assign_document_to_topic(doc_id1, topic_id)
        success2 = self.study_system.assign_document_to_topic(doc_id2, topic_id)

        self.assertTrue(success1)
        self.assertTrue(success2)

        # Get documents by topic
        docs = self.study_system.get_documents_by_topic(topic_id)
        self.assertEqual(len(docs), 2)

        doc_titles = [d["title"] for d in docs]
        self.assertIn("Python Guide", doc_titles)
        self.assertIn("Java Guide", doc_titles)

    def test_spaced_repetition_workflow(self):
        """Test the complete spaced repetition workflow."""
        # Add a document
        doc_id = self.study_system.add_study_material(
            "Test Topic",
            "This is content for testing spaced repetition."
        )

        # Schedule initial review
        review_id = self.study_system.schedule_review(doc_id, "initial")
        self.assertIsInstance(review_id, int)

        # Get pending reviews
        pending = self.study_system.get_pending_reviews()
        self.assertGreaterEqual(len(pending), 1)

        # Complete the review
        result = self.study_system.complete_review(review_id, quality_rating=4)  # Good recall

        self.assertIn("next_review_date", result)
        self.assertIn("ease_factor", result)
        self.assertIn("interval_days", result)

        # Verify ease factor improved
        self.assertGreater(result["ease_factor"], 2.5)  # Default ease factor

    def test_study_stats(self):
        """Test retrieving study statistics."""
        # Add some test data
        self.study_system.add_study_material("Doc 1", "Content 1")
        self.study_system.add_study_material("Doc 2", "Content 2")
        self.study_system.create_topic("Test Topic")

        # Get stats
        stats = self.study_system.get_study_stats()

        self.assertIsInstance(stats, dict)
        self.assertIn("total_documents", stats)
        self.assertIn("total_topics", stats)
        self.assertIn("total_reviews", stats)

        self.assertGreaterEqual(stats["total_documents"], 2)
        self.assertGreaterEqual(stats["total_topics"], 1)

    def test_backup_and_restore(self):
        """Test system backup and restore functionality."""
        # Add some test data
        doc_id = self.study_system.add_study_material(
            "Backup Test",
            "This document should survive backup and restore."
        )
        topic_id = self.study_system.create_topic("Backup Topic")
        self.study_system.assign_document_to_topic(doc_id, topic_id)

        # Create backup
        backup_file = self.study_system.backup_system(self.temp_dir)
        self.assertTrue(os.path.exists(backup_file))

        # Create new study system instance
        new_db_path = os.path.join(self.temp_dir, "restored.db")
        new_config_path = os.path.join(self.temp_dir, "restored_config.json")
        with open(new_config_path, 'w') as f:
            json.dump({"openai_api_key": "test_key"}, f)

        restored_system = StudySystem(db_path=new_db_path)
        restored_system.restore_system(backup_file)

        # Verify data was restored
        docs = restored_system.metadata_db.get_documents()
        self.assertGreaterEqual(len(docs), 1)

        topics = restored_system.metadata_db.get_topics()
        self.assertGreaterEqual(len(topics), 1)

        # Check specific document
        restored_doc = restored_system.metadata_db.get_document(doc_id)
        self.assertIsNotNone(restored_doc)
        self.assertEqual(restored_doc["title"], "Backup Test")

        # Clean up
        if hasattr(restored_system, 'metadata_db') and restored_system.metadata_db.connection:
            restored_system.metadata_db.connection.close()

    def test_context_manager(self):
        """Test that the study system works as a context manager."""
        with StudySystem(db_path=self.db_path) as system:
            # Add some data
            doc_id = system.add_study_material("Context Test", "Testing context manager")

            # Verify it works
            doc = system.metadata_db.get_document(doc_id)
            self.assertIsNotNone(doc)

        # System should be properly closed after context


if __name__ == '__main__':
    unittest.main()