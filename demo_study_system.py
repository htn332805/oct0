#!/usr/bin/env python3
"""
Study System Integration Demo - Part 3

Demonstrates the integrated AI-assisted study system with all components working together:
- Copilot client for content generation
- Vector store for knowledge retrieval
- Embedding generator for text vectorization
- Metadata database for study tracking and spaced repetition

This demo shows the main workflows without requiring actual API keys.
"""

import os
import sys
import json
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from kb.study_system import StudySystem


def demo_study_system():
    """Demonstrate the integrated study system functionality."""

    print("🎓 AI-Assisted Study System Integration Demo")
    print("=" * 50)

    # Create demo directories
    demo_dir = Path("demo_data")
    demo_dir.mkdir(exist_ok=True)

    db_path = demo_dir / "demo_study.db"
    vector_path = demo_dir / "demo_vectors.index"

    print("📁 Setting up demo environment...")
    print(f"   Database: {db_path}")
    print(f"   Vectors: {vector_path}")

    try:
        # Initialize the study system
        print("\n🔧 Initializing Study System...")
        study_system = StudySystem(db_path=str(db_path), enable_copilot=False)

        print("✅ Study System initialized successfully!")

        # Demo 1: Add study materials
        print("\n📚 Demo 1: Adding Study Materials")
        print("-" * 30)

        materials = [
            {
                "title": "Introduction to Machine Learning",
                "content": "Machine learning is a method of data analysis that automates analytical model building. It is a branch of artificial intelligence based on the idea that systems can learn from data, identify patterns and make decisions with minimal human intervention.",
                "tags": ["ml", "ai", "data-science"]
            },
            {
                "title": "Neural Networks Basics",
                "content": "A neural network is a series of algorithms that endeavors to recognize underlying relationships in a set of data through a process that mimics the way the human brain operates. Neural networks consist of layers of interconnected nodes.",
                "tags": ["neural-networks", "deep-learning", "ai"]
            },
            {
                "title": "Python Programming Fundamentals",
                "content": "Python is a high-level, interpreted programming language known for its simplicity and readability. It supports multiple programming paradigms including procedural, object-oriented, and functional programming.",
                "tags": ["python", "programming", "basics"]
            }
        ]

        doc_ids = []
        for material in materials:
            print(f"Adding: {material['title']}")
            doc_id = study_system.add_study_material(
                title=material["title"],
                content=material["content"],
                source_type="article",
                tags=material["tags"]
            )
            doc_ids.append(doc_id)
            print(f"   → Document ID: {doc_id}")

        # Demo 2: Search functionality
        print("\n🔍 Demo 2: Knowledge Search")
        print("-" * 30)

        search_queries = [
            "artificial intelligence",
            "programming languages",
            "data analysis"
        ]

        for query in search_queries:
            print(f"\nSearching for: '{query}'")
            results = study_system.search_knowledge(query, limit=2)
            if results:
                for i, result in enumerate(results, 1):
                    doc = result["document"]
                    score = result["similarity_score"]
                    print(f"   {i}. {doc['title']} (score: {score:.3f})")
            else:
                print("   No results found")

        # Demo 3: Full-text search
        print("\n📖 Demo 3: Full-Text Search")
        print("-" * 30)

        fts_results = study_system.search_documents("neural networks", limit=5)
        print(f"Found {len(fts_results)} documents matching 'neural networks'")
        for result in fts_results:
            print(f"   → {result['title']}")

        # Demo 4: Topic management
        print("\n🏷️  Demo 4: Topic Management")
        print("-" * 30)

        # Create topics
        ai_topic = study_system.create_topic("Artificial Intelligence", "AI and machine learning concepts")
        prog_topic = study_system.create_topic("Programming", "Programming languages and techniques")

        print(f"Created topics: AI (ID: {ai_topic}), Programming (ID: {prog_topic})")

        # Assign documents to topics
        study_system.assign_document_to_topic(doc_ids[0], ai_topic)  # ML article
        study_system.assign_document_to_topic(doc_ids[1], ai_topic)  # Neural networks
        study_system.assign_document_to_topic(doc_ids[2], prog_topic)  # Python

        print("Assigned documents to topics")

        # Get documents by topic
        ai_docs = study_system.get_documents_by_topic(ai_topic)
        print(f"AI topic has {len(ai_docs)} documents")

        # Demo 5: Spaced repetition setup
        print("\n🧠 Demo 5: Spaced Repetition Setup")
        print("-" * 30)

        # Schedule reviews for documents
        for i, doc_id in enumerate(doc_ids):
            review_id = study_system.schedule_review(doc_id, "initial")
            print(f"Scheduled review for '{materials[i]['title']}' (Review ID: {review_id})")

        # Get pending reviews
        pending_reviews = study_system.get_pending_reviews(limit=10)
        print(f"Total pending reviews: {len(pending_reviews)}")

        # Demo 6: Study statistics
        print("\n📊 Demo 6: Study Statistics")
        print("-" * 30)

        stats = study_system.get_study_stats()
        print("Study System Statistics:")
        for key, value in stats.items():
            print(f"   {key}: {value}")

        # Demo 7: Backup and restore
        print("\n💾 Demo 7: Backup and Restore")
        print("-" * 30)

        backup_file = study_system.backup_system(str(demo_dir / "backups"))
        print(f"System backed up to: {backup_file}")

        # Create new instance and restore
        restore_db = demo_dir / "restored_demo.db"
        restored_system = StudySystem(db_path=str(restore_db))
        restored_system.restore_system(backup_file)

        # Verify restore
        restored_stats = restored_system.get_study_stats()
        print(f"Restored system has {restored_stats.get('total_documents', 0)} documents")

        # Clean up
        restored_system.metadata_db.connection.close()

        print("\n🎉 Demo completed successfully!")
        print("\nThe integrated study system demonstrates:")
        print("   ✅ Component integration (Copilot + Vectors + Embeddings + Database)")
        print("   ✅ End-to-end workflows (add → search → review → backup)")
        print("   ✅ Spaced repetition and study tracking")
        print("   ✅ Full-text and semantic search capabilities")
        print("   ✅ Data persistence and backup/restore")

    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Clean up demo data
        print(f"\n🧹 Cleaning up demo data...")
        import shutil
        if demo_dir.exists():
            shutil.rmtree(demo_dir, ignore_errors=True)
        print("   Demo data cleaned up")


if __name__ == "__main__":
    demo_study_system()