"""
Unit tests for the Metadata Database module.

Tests the SQLite-based metadata functionality including:
- Document CRUD operations
- Topic management
- Review scheduling and completion
- Full-text search
- Study session tracking
- Backup and restore
"""

import pytest
import tempfile
import os
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from kb.metadata_db import MetadataDB


class TestMetadataDB:
    """Test suite for MetadataDB class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_metadata.db")
        self.db = MetadataDB(self.db_path)

    def teardown_method(self):
        """Clean up test fixtures."""
        self.db.close()
        # Remove test files
        for file in Path(self.temp_dir).glob("*"):
            file.unlink()
        os.rmdir(self.temp_dir)

    def test_add_and_get_document(self):
        """Test adding and retrieving documents."""
        doc_id = self.db.add_document(
            title="Test Document",
            content_preview="This is a test document content.",
            document_type="note",
            tags=["test", "sample"],
            metadata={"author": "Test Author"}
        )

        assert doc_id > 0

        doc = self.db.get_document(doc_id)
        assert doc is not None
        assert doc['title'] == "Test Document"
        assert doc['document_type'] == "note"
        assert doc['tags'] == ["test", "sample"]
        assert doc['metadata']['author'] == "Test Author"
        assert doc['word_count'] == 6  # "This is a test document content."
        assert doc['reading_time_minutes'] == 1

    def test_update_document(self):
        """Test updating document fields."""
        doc_id = self.db.add_document(title="Original Title")

        success = self.db.update_document(doc_id, title="Updated Title", document_type="article")
        assert success

        doc = self.db.get_document(doc_id)
        assert doc['title'] == "Updated Title"
        assert doc['document_type'] == "article"

    def test_delete_document(self):
        """Test deleting documents."""
        doc_id = self.db.add_document(title="Test Document")

        # Verify it exists
        assert self.db.get_document(doc_id) is not None

        # Delete it
        success = self.db.delete_document(doc_id)
        assert success

        # Verify it's gone
        assert self.db.get_document(doc_id) is None

    def test_get_documents(self):
        """Test retrieving multiple documents."""
        # Add some documents
        id1 = self.db.add_document(title="Doc 1", document_type="note")
        id2 = self.db.add_document(title="Doc 2", document_type="article")
        id3 = self.db.add_document(title="Doc 3", document_type="note")

        # Get all documents
        docs = self.db.get_documents()
        assert len(docs) == 3

        # Filter by type
        notes = self.db.get_documents(document_type="note")
        assert len(notes) == 2
        assert all(doc['document_type'] == 'note' for doc in notes)

    def test_topics(self):
        """Test topic management."""
        # Add topics
        topic_id = self.db.add_topic("Mathematics", "Math-related topics")
        subtopic_id = self.db.add_topic("Algebra", "Algebra concepts", parent_topic_id=topic_id)

        topics = self.db.get_topics()
        assert len(topics) == 2

        # Check hierarchy
        math_topic = next(t for t in topics if t['name'] == 'Mathematics')
        algebra_topic = next(t for t in topics if t['name'] == 'Algebra')

        assert algebra_topic['parent_topic_id'] == math_topic['id']

    def test_document_topic_assignment(self):
        """Test assigning documents to topics."""
        doc_id = self.db.add_document(title="Calculus Notes")
        topic_id = self.db.add_topic("Calculus")

        # Assign document to topic
        success = self.db.assign_document_to_topic(doc_id, topic_id)
        assert success

        # Get documents by topic
        docs = self.db.get_documents_by_topic(topic_id)
        assert len(docs) == 1
        assert docs[0]['title'] == "Calculus Notes"

    def test_review_scheduling(self):
        """Test review scheduling."""
        doc_id = self.db.add_document(title="Test Doc")

        # Schedule initial review
        review_id = self.db.schedule_review(doc_id, "initial")
        assert review_id > 0

        # Get pending reviews
        pending = self.db.get_pending_reviews()
        assert len(pending) >= 1

        # Find our review
        review = next((r for r in pending if r['id'] == review_id), None)
        assert review is not None
        assert review['document_title'] == "Test Doc"
        assert review['review_type'] == "initial"

    def test_review_completion(self):
        """Test completing reviews with SM-2 algorithm."""
        doc_id = self.db.add_document(title="Test Doc")
        review_id = self.db.schedule_review(doc_id, "initial")

        # Complete with good rating
        success = self.db.complete_review(review_id, quality_rating=4, notes="Good review")
        assert success

        # Check that review is marked complete and next review is scheduled
        # Get all reviews for this document
        conn = self.db._get_connection()
        cursor = conn.execute('SELECT * FROM reviews WHERE document_id = ? ORDER BY id', (doc_id,))
        all_reviews = [dict(row) for row in cursor.fetchall()]

        # Should have 2 reviews: completed one and scheduled next one
        assert len(all_reviews) == 2
        completed_review = next(r for r in all_reviews if r['id'] == review_id)
        next_review = next(r for r in all_reviews if r['id'] != review_id)

        assert completed_review['completed_date'] is not None
        assert completed_review['quality_rating'] == 4
        assert next_review['review_type'] == 'spaced_1'
        assert next_review['completed_date'] is None

    def test_failed_review_reset(self):
        """Test that failed reviews reset to initial."""
        doc_id = self.db.add_document(title="Test Doc")
        review_id = self.db.schedule_review(doc_id, "spaced_1")

        # Complete with poor rating
        success = self.db.complete_review(review_id, quality_rating=1, notes="Need more practice")
        assert success

        # Check that review is marked as failed but no next review is scheduled
        conn = self.db._get_connection()
        cursor = conn.execute('SELECT * FROM reviews WHERE document_id = ? ORDER BY id', (doc_id,))
        all_reviews = [dict(row) for row in cursor.fetchall()]

        # Should have only 1 review: the completed one (failed reviews don't schedule next)
        assert len(all_reviews) == 1
        completed_review = all_reviews[0]

        assert completed_review['completed_date'] is not None
        assert completed_review['quality_rating'] == 1
        assert completed_review['review_type'] == 'spaced_1'  # Original type

    def test_full_text_search(self):
        """Test full-text search functionality."""
        # Add documents with searchable content
        id1 = self.db.add_document(
            title="Python Programming",
            content_preview="Learn Python programming language basics",
            tags=["python", "programming"]
        )
        id2 = self.db.add_document(
            title="Data Structures",
            content_preview="Understanding algorithms and data structures",
            tags=["algorithms", "data structures"]
        )

        # Search for "python"
        results = self.db.search_documents("python")
        assert len(results) >= 1
        assert any(r['title'] == "Python Programming" for r in results)

        # Search for "algorithms"
        results = self.db.search_documents("algorithms")
        assert len(results) >= 1
        assert any(r['title'] == "Data Structures" for r in results)

    def test_study_session_logging(self):
        """Test logging study sessions."""
        doc_id = self.db.add_document(title="Study Material")
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=30)

        session_id = self.db.log_study_session(
            doc_id, start_time, end_time,
            session_type="reading", notes="Focused study session"
        )
        assert session_id > 0

        # Check stats
        stats = self.db.get_study_stats(doc_id)
        assert stats['sessions_count'] == 1
        assert stats['total_minutes'] == 30

    def test_study_stats(self):
        """Test study statistics calculation."""
        doc_id = self.db.add_document(title="Test Doc")

        # Log multiple sessions
        base_time = datetime.now()
        self.db.log_study_session(doc_id, base_time, base_time + timedelta(minutes=20))
        self.db.log_study_session(doc_id, base_time + timedelta(hours=1), base_time + timedelta(hours=1, minutes=15))

        stats = self.db.get_study_stats(doc_id)
        assert stats['sessions_count'] == 2
        assert stats['total_minutes'] == 35  # 20 + 15
        assert stats['avg_session_minutes'] == 17.5

    def test_backup_and_restore(self):
        """Test database backup and restore."""
        # Add some data
        doc_id = self.db.add_document(title="Backup Test", content_preview="Test content")
        topic_id = self.db.add_topic("Test Topic")

        backup_path = os.path.join(self.temp_dir, "backup.db")

        # Backup
        self.db.backup_db(backup_path)
        assert os.path.exists(backup_path)

        # Create new database and restore
        new_db_path = os.path.join(self.temp_dir, "restored.db")
        new_db = MetadataDB.restore_from_backup(new_db_path, backup_path)

        # Verify data was restored
        docs = new_db.get_documents()
        assert len(docs) == 1
        assert docs[0]['title'] == "Backup Test"

        topics = new_db.get_topics()
        assert len(topics) == 1
        assert topics[0]['name'] == "Test Topic"

        new_db.close()

    def test_get_stats(self):
        """Test database statistics."""
        # Add some test data
        self.db.add_document(title="Note 1", document_type="note")
        self.db.add_document(title="Article 1", document_type="article")
        self.db.add_topic("Topic 1")

        stats = self.db.get_stats()

        assert stats['total_documents'] == 2
        assert stats['total_topics'] == 1
        assert stats['documents_by_type']['note'] == 1
        assert stats['documents_by_type']['article'] == 1
        assert stats['completed_reviews'] == 0
        assert stats['pending_reviews'] == 0

    def test_json_field_handling(self):
        """Test proper handling of JSON fields."""
        # Test with complex metadata
        complex_metadata = {
            "author": "Test Author",
            "publication_year": 2023,
            "references": ["ref1", "ref2"],
            "complex": {"nested": {"value": 42}}
        }

        doc_id = self.db.add_document(
            title="Complex Doc",
            tags=["tag1", "tag2", "tag3"],
            metadata=complex_metadata
        )

        doc = self.db.get_document(doc_id)
        assert doc['tags'] == ["tag1", "tag2", "tag3"]
        assert doc['metadata'] == complex_metadata

    def test_invalid_document_type(self):
        """Test that invalid document types are rejected."""
        with pytest.raises(sqlite3.IntegrityError):
            self.db.add_document(title="Test", document_type="invalid_type")