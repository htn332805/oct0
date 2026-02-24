"""
Study System Integration Layer - Part 3

Combines all core modules into a cohesive AI-assisted study system:
- Copilot integration for content generation
- Vector store for knowledge retrieval
- Embeddings for text vectorization
- Metadata database for study tracking and spaced repetition

Provides the main API for the study system with methods for:
- Adding study materials
- Generating study content
- Conducting study sessions
- Managing spaced repetition reviews
- Searching and retrieving knowledge
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from config import config as config_module
from scripts.copilot_client import CopilotClient
from kb.vector_store import VectorStore
from kb.embeddings import EmbeddingGenerator
from kb.metadata_db import MetadataDB


class StudySystem:
    """
    Main integration class for the AI-assisted study system.

    Orchestrates interactions between:
    - Copilot client for content generation
    - Vector store for knowledge retrieval
    - Embedding generator for text vectorization
    - Metadata database for study tracking
    """

    def __init__(self, config_path: Optional[str] = None, db_path: Optional[str] = None,
                 vector_store_path: Optional[str] = None, enable_copilot: bool = True):
        """
        Initialize the study system with all components.

        Args:
            config_path: Path to configuration file (optional, uses default)
            db_path: Path to metadata database (optional, uses default)
            vector_store_path: Path to vector store index (optional, uses default)
            enable_copilot: Whether to initialize CopilotClient (default: True)
        """
        # Load configuration
        self.config = config_module.load()

        # Set default paths if not provided
        if db_path is None:
            db_path = "kb/metadata/study_system.db"
        if vector_store_path is None:
            vector_store_path = "kb/vectors/study_vectors.index"

        # Initialize components
        self.copilot = None
        if enable_copilot:
            try:
                self.copilot = CopilotClient(api_key=self.config.get('openai_api_key'))
            except ValueError:
                print("⚠️  Copilot disabled: OpenAI API key not configured")
                self.copilot = None

        self.embeddings = EmbeddingGenerator()
        self.embeddings.load_model()  # Load the sentence transformer model
        self.vector_store = VectorStore(vector_store_path)
        self.metadata_db = MetadataDB(db_path)

        # Initialize vector store index
        if os.path.exists(vector_store_path + ".faiss"):
            try:
                self.vector_store.load_index()
            except Exception as e:
                print(f"Could not load existing vector store: {e}")
                print("Creating new vector index...")
                self.vector_store.create_index(dimension=384)  # all-MiniLM-L6-v2 dimension
        else:
            print("Creating new vector index...")
            self.vector_store.create_index()

        print("Study System initialized successfully")

    def add_study_material(self, title: str, content: str, source_type: str = "note",
                          source_path: Optional[str] = None, source_url: Optional[str] = None,
                          tags: Optional[List[str]] = None) -> int:
        """
        Add study material to the system.

        Args:
            title: Title of the study material
            content: Full text content
            source_type: Type of source ('note', 'article', 'book', 'video', 'audio', 'other')
            source_path: File path if applicable
            source_url: URL if applicable
            tags: List of tags for categorization

        Returns:
            Document ID of the added material
        """
        # Add to metadata database
        doc_id = self.metadata_db.add_document(
            title=title,
            content_preview=content[:500],  # First 500 chars as preview
            file_path=source_path,
            url=source_url,
            document_type=source_type,
            tags=tags
        )

        # Generate embeddings and store in vector database
        chunks = self.embeddings.chunk_text(content)
        embeddings = self.embeddings.generate_embeddings(chunks)

        # Store vectors with metadata
        metadata = {
            "document_id": doc_id,
            "title": title,
            "source_type": source_type,
            "tags": tags or []
        }

        self.vector_store.add_vectors(embeddings, [metadata] * len(embeddings))

        print(f"Added study material: {title} (ID: {doc_id})")
        return doc_id

    def generate_study_content(self, topic: str, content_type: str = "flashcards",
                              difficulty: str = "intermediate") -> Dict[str, Any]:
        """
        Generate study content using Copilot.

        Args:
            topic: Topic to generate content for
            content_type: Type of content ('flashcards', 'summary', 'questions', 'explanation')
            difficulty: Difficulty level ('beginner', 'intermediate', 'advanced')

        Returns:
            Generated content with metadata
        """
        if self.copilot is None:
            raise ValueError("Copilot is not available. Configure OpenAI API key to use content generation.")

        # Generate content using Copilot
        if content_type == "flashcards":
            content = self.copilot.generate_flashcards(topic, difficulty)
        elif content_type == "summary":
            content = self.copilot.generate_summary(topic)
        elif content_type == "questions":
            content = self.copilot.generate_questions(topic, difficulty)
        elif content_type == "explanation":
            content = self.copilot.generate_explanation(topic, difficulty)
        else:
            raise ValueError(f"Unsupported content type: {content_type}")

        # Store generated content as study material
        title = f"Generated {content_type.title()}: {topic}"
        doc_id = self.add_study_material(
            title=title,
            content=json.dumps(content),
            source_type="generated",
            tags=[content_type, topic, difficulty]
        )

        return {
            "document_id": doc_id,
            "content": content,
            "topic": topic,
            "content_type": content_type,
            "difficulty": difficulty,
            "generated_at": datetime.now().isoformat()
        }

    def search_knowledge(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for relevant knowledge using vector similarity.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of relevant documents with similarity scores
        """
        # Generate embedding for query
        query_embedding = self.embeddings.generate_embeddings([query])[0]

        # Search vector store
        results = self.vector_store.search_vectors(query_embedding, limit)

        # Enrich results with document metadata
        enriched_results = []
        for vector_id, score, metadata in results:
            doc_id = metadata["document_id"]
            doc_info = self.metadata_db.get_document(doc_id)
            if doc_info:
                enriched_results.append({
                    "document": doc_info,
                    "similarity_score": score,
                    "metadata": metadata
                })

        return enriched_results

    def search_documents(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search documents using full-text search.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching documents
        """
        return self.metadata_db.search_documents(query, limit)

    def start_study_session(self, document_id: int, session_type: str = "reading") -> int:
        """
        Start a study session for a document.

        Args:
            document_id: ID of the document being studied
            session_type: Type of study session

        Returns:
            Session ID
        """
        # This would be implemented to track study sessions
        # For now, just return a placeholder
        print(f"Started study session for document {document_id}")
        return 0  # Placeholder

    def schedule_review(self, document_id: int, review_type: str = "initial") -> int:
        """
        Schedule a spaced repetition review for a document.

        Args:
            document_id: ID of the document to review
            review_type: Type of review ('initial', 'spaced_1', 'spaced_2', 'spaced_3', 'maintenance')

        Returns:
            Review ID
        """
        return self.metadata_db.schedule_review(document_id, review_type)

    def complete_review(self, review_id: int, quality_rating: int) -> Dict[str, Any]:
        """
        Complete a review with quality rating for spaced repetition.

        Args:
            review_id: ID of the review to complete
            quality_rating: Quality of recall (0-5)

        Returns:
            Review completion data
        """
        return self.metadata_db.complete_review(review_id, quality_rating)

    def get_pending_reviews(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get reviews that are due or overdue.

        Args:
            limit: Maximum number of reviews to return

        Returns:
            List of pending reviews
        """
        return self.metadata_db.get_pending_reviews(limit)

    def get_study_stats(self) -> Dict[str, Any]:
        """
        Get overall study statistics.

        Returns:
            Dictionary with study statistics
        """
        return self.metadata_db.get_stats()

    def create_topic(self, name: str, description: Optional[str] = None,
                    parent_topic_id: Optional[int] = None, color: str = "#3498db") -> int:
        """
        Create a new topic for organizing study materials.

        Args:
            name: Topic name
            description: Topic description
            parent_topic_id: Parent topic ID for hierarchy
            color: Color for UI display

        Returns:
            Topic ID
        """
        return self.metadata_db.add_topic(name, description, parent_topic_id, color)

    def assign_document_to_topic(self, document_id: int, topic_id: int) -> bool:
        """
        Assign a document to a topic.

        Args:
            document_id: Document ID
            topic_id: Topic ID

        Returns:
            Success status
        """
        return self.metadata_db.assign_document_to_topic(document_id, topic_id)

    def get_documents_by_topic(self, topic_id: int) -> List[Dict[str, Any]]:
        """
        Get all documents for a topic.

        Args:
            topic_id: Topic ID

        Returns:
            List of documents in the topic
        """
        return self.metadata_db.get_documents_by_topic(topic_id)

    def backup_system(self, backup_dir: str = "backups") -> str:
        """
        Create a complete backup of the study system.

        Args:
            backup_dir: Directory to store backups

        Returns:
            Path to the backup file
        """
        # Create backup directory
        backup_path = Path(backup_dir)
        backup_path.mkdir(exist_ok=True)

        # Generate timestamp for backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_path / f"study_system_backup_{timestamp}.db"

        # Backup metadata database
        self.metadata_db.backup_db(str(backup_file))

        # Backup vector store (this would need to be implemented in VectorStore)
        # For now, just note that vector store backup would be needed

        print(f"Study system backed up to {backup_file}")
        return str(backup_file)

    def restore_system(self, backup_file: str) -> None:
        """
        Restore the study system from a backup.

        Args:
            backup_file: Path to backup file
        """
        # Restore metadata database
        new_db_path = self.metadata_db.db_path.parent / "restored_metadata.db"
        restored_db = MetadataDB.restore_from_backup(str(new_db_path), backup_file)

        # Replace current database connection
        self.metadata_db.connection.close()
        self.metadata_db = restored_db

        # Vector store restoration would need to be implemented
        # For now, just note that vector store restore would be needed

        print(f"Study system restored from {backup_file}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - clean up resources."""
        # Close database connection
        if hasattr(self.metadata_db, 'connection') and self.metadata_db.connection:
            self.metadata_db.connection.close()

        # Vector store cleanup if needed
        if hasattr(self.vector_store, 'cleanup'):
            self.vector_store.cleanup()