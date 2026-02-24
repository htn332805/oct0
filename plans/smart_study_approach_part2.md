# Smart Study Approach Implementation Plan - Part 2

## Part 2: Core Modules Development

This part focuses on building the fundamental modules that power the smart study system: Copilot integration for AI assistance, vector store for knowledge retrieval, embedding generation for semantic search, and metadata management for tracking study materials.

### Main Task 2.1: Develop Copilot Integration Module
**Objective:** Create a module to interact with Copilot for generating study materials.  
**Purpose:** Enable automated content generation and AI-assisted learning.  
**Role:** Core component for all AI-powered features in the system.  

#### Subtask 2.1.1: Create Copilot Client Class
**Objective:** Implement a class to handle OpenAI API calls.  
**Purpose:** Abstract API interactions for reusability.  
**Role:** Used by all generation scripts.  
**How to complete:** Create `scripts/copilot_client.py` with class `CopilotClient` having methods for chat completion. Use `openai.ChatCompletion.create()`.

#### Subtask 2.1.2: Add Prompt Template Management
**Objective:** Create a system for storing and loading prompt templates.  
**Purpose:** Standardize prompts for consistent outputs.  
**Role:** Ensures quality and reproducibility of AI responses.  
**How to complete:** Add `prompts/` directory with JSON files for each prompt type (e.g., `summary_prompt.json`). Load in the client class.

#### Subtask 2.1.3: Implement Error Handling and Retries
**Objective:** Add robust error handling for API calls.  
**Purpose:** Handle rate limits and network issues gracefully.  
**Role:** Prevents script failures due to temporary issues.  
**How to complete:** Wrap API calls in try-except with exponential backoff using `tenacity` library. Add logging for failures.

#### Subtask 2.1.4: Create Response Parser
**Objective:** Parse and structure Copilot responses.  
**Purpose:** Convert raw text into usable data structures.  
**Role:** Enables integration with other modules.  
**How to complete:** Add methods to extract flashcards, summaries, etc., from responses. Use regex or JSON parsing where applicable.

#### Subtask 2.1.5: Test Copilot Integration
**Objective:** Verify the module works with sample prompts.  
**Purpose:** Ensure API connectivity and response handling.  
**Role:** Validates the core AI functionality.  
**How to complete:** Write `test_copilot.py` with unit tests for each method. Run with `python -m pytest test_copilot.py`.

### Main Task 2.2: Implement Vector Store Module
**Objective:** Build a module for storing and retrieving vector embeddings.  
**Purpose:** Enable semantic search over study materials.  
**Role:** Foundation for the knowledge base search functionality.  

#### Subtask 2.2.1: Set Up FAISS Index Creation
**Objective:** Create functions to initialize FAISS indexes.  
**Purpose:** Prepare for vector storage.  
**Role:** Required for adding vectors to the store.  
**How to complete:** Create `kb/vector_store.py` with `create_index()` function using `faiss.IndexFlatIP` for cosine similarity.

#### Subtask 2.2.2: Implement Vector Addition
**Objective:** Add vectors and metadata to the store.  
**Purpose:** Store new study materials.  
**Role:** Used when processing new notes.  
**How to complete:** Add `add_vectors()` method that takes embeddings and IDs, updates the index and saves to disk.

#### Subtask 2.2.3: Create Vector Search Functionality
**Objective:** Implement nearest neighbor search.  
**Purpose:** Find relevant documents by similarity.  
**Role:** Powers query responses.  
**How to complete:** Add `search_vectors()` method using `index.search()` to return top-k similar vectors with scores.

#### Subtask 2.2.4: Add Index Persistence
**Objective:** Save and load FAISS indexes.  
**Purpose:** Maintain state across sessions.  
**Role:** Ensures data persistence.  
**How to complete:** Implement `save_index()` and `load_index()` using `faiss.write_index()` and `faiss.read_index()`.

#### Subtask 2.2.5: Test Vector Store Operations
**Objective:** Validate add, search, and persistence.  
**Purpose:** Ensure correctness of vector operations.  
**Role:** Confirms the module is ready for integration.  
**How to complete:** Create `test_vector_store.py` with tests for adding vectors, searching, and reloading from disk.

### Main Task 2.3: Develop Embedding Generation Module
**Objective:** Create a module to generate embeddings from text.  
**Purpose:** Convert study materials into vector representations.  
**Role:** Bridges text content to vector search.  

#### Subtask 2.3.1: Integrate Sentence Transformers
**Objective:** Set up the embedding model.  
**Purpose:** Generate high-quality embeddings.  
**Role:** Core for semantic understanding.  
**How to complete:** Create `kb/embeddings.py` with `SentenceTransformer` initialization using 'all-MiniLM-L6-v2' model.

#### Subtask 2.3.2: Implement Text Chunking
**Objective:** Split long texts into manageable pieces.  
**Purpose:** Handle large documents efficiently.  
**Role:** Prepares text for embedding.  
**How to complete:** Add `chunk_text()` function that splits by sentences or tokens, respecting max length.

#### Subtask 2.3.3: Create Embedding Generation
**Objective:** Convert text chunks to vectors.  
**Purpose:** Produce embeddings for storage.  
**Role:** Used in processing pipeline.  
**How to complete:** Implement `generate_embeddings()` that takes text list and returns numpy array of vectors.

#### Subtask 2.3.4: Add Batch Processing
**Objective:** Handle multiple texts efficiently.  
**Purpose:** Optimize for large note sets.  
**Role:** Improves performance for bulk operations.  
**How to complete:** Modify generation to process in batches, using model's encode() with batch_size parameter.

#### Subtask 2.3.5: Test Embedding Quality
**Objective:** Verify embeddings capture semantic meaning.  
**Purpose:** Ensure search relevance.  
**Role:** Validates the embedding approach.  
**How to complete:** Create `test_embeddings.py` with similarity tests between related and unrelated texts.

### Main Task 2.4: Build Metadata Database Module
**Objective:** Implement a database for tracking study materials metadata.  
**Purpose:** Store information about documents, topics, and review status.  
**Role:** Provides context and organization for the knowledge base.  

#### Subtask 2.4.1: Set Up SQLite Database Schema
**Objective:** Design tables for metadata storage.  
**Purpose:** Structure data relationships.  
**Role:** Foundation for data management.  
**How to complete:** Create `kb/metadata_db.py` with schema for documents, topics, reviews tables using SQLAlchemy or raw SQL.

#### Subtask 2.4.2: Implement CRUD Operations
**Objective:** Add create, read, update, delete functions.  
**Purpose:** Manage metadata programmatically.  
**Role:** Used by all data manipulation scripts.  
**How to complete:** Add methods like `add_document()`, `get_documents_by_topic()`, `update_review_status()`.

#### Subtask 2.4.3: Add Full-Text Search
**Objective:** Enable text search on metadata.  
**Purpose:** Find documents by keywords.  
**Role:** Complements vector search.  
**How to complete:** Use SQLite FTS5 extension for title, content, and topic searches.

#### Subtask 2.4.4: Implement Backup and Restore
**Objective:** Create database backup functionality.  
**Purpose:** Prevent data loss.  
**Role:** Supports system reliability.  
**How to complete:** Add `backup_db()` and `restore_db()` methods using SQLite dump and restore.

#### Subtask 2.4.5: Test Database Operations
**Objective:** Validate all CRUD and search functions.  
**Purpose:** Ensure data integrity.  
**Role:** Confirms module readiness.  
**How to complete:** Write `test_metadata_db.py` with comprehensive tests for all operations.