"""
Metadata Database Module for Smart Study System

This module provides database functionality for storing and managing metadata
about study materials, topics, reviews, and user progress. It uses SQLite
for reliable, file-based storage that integrates well with the vector store.

The module supports:
- Document metadata tracking
- Topic organization and relationships
- Review scheduling and progress tracking
- Full-text search capabilities
- Database backup and restore
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path


class MetadataDB:
    """
    SQLite-based metadata database for the study system.

    Manages all non-vector data including document information, topics,
    review schedules, and user progress tracking.
    """

    def __init__(self, db_path: str):
        """
        Initialize the metadata database.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = None
        self._initialize_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        if self.connection is None:
            self.connection = sqlite3.connect(str(self.db_path))
            self.connection.row_factory = sqlite3.Row
            self.connection.execute("PRAGMA foreign_keys = ON")
        return self.connection

    def _initialize_db(self) -> None:
        """Initialize database tables and indexes."""
        conn = self._get_connection()

        # Check if database is already initialized
        try:
            conn.execute('SELECT 1 FROM documents LIMIT 1')
            # Database exists, check if FTS table is properly configured
            try:
                conn.execute('SELECT 1 FROM documents_fts LIMIT 1')
            except sqlite3.OperationalError:
                # FTS table is missing or malformed, recreate it
                self._recreate_fts_table(conn)
            return
        except sqlite3.OperationalError:
            # Database doesn't exist yet, create all tables
            pass

        # Documents table - stores information about study materials
        conn.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content_preview TEXT,  -- First 500 chars for quick display
                file_path TEXT,        -- Path to original file if applicable
                url TEXT,             -- Source URL if applicable
                document_type TEXT CHECK(document_type IN ('note', 'article', 'book', 'video', 'audio', 'other')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                word_count INTEGER DEFAULT 0,
                reading_time_minutes INTEGER DEFAULT 0,
                tags TEXT,            -- JSON array of tags
                metadata TEXT         -- JSON additional metadata
            )
        ''')

        # Topics table - organizes documents by subject areas
        conn.execute('''
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                parent_topic_id INTEGER,
                color TEXT DEFAULT '#3498db',  -- Hex color for UI
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_topic_id) REFERENCES topics(id) ON DELETE CASCADE
            )
        ''')

        # Document-Topic relationships (many-to-many)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS document_topics (
                document_id INTEGER,
                topic_id INTEGER,
                PRIMARY KEY (document_id, topic_id),
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
            )
        ''')

        # Reviews table - tracks spaced repetition review schedule
        conn.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                review_type TEXT CHECK(review_type IN ('initial', 'spaced_1', 'spaced_2', 'spaced_3', 'maintenance')),
                scheduled_date TIMESTAMP,
                completed_date TIMESTAMP,
                ease_factor REAL DEFAULT 2.5,  -- SM-2 algorithm ease factor
                interval_days INTEGER DEFAULT 1,
                quality_rating INTEGER CHECK(quality_rating BETWEEN 0 AND 5),  -- 0=failed, 5=perfect
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        ''')

        # Study sessions table - tracks actual study time
        conn.execute('''
            CREATE TABLE IF NOT EXISTS study_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                duration_minutes INTEGER,
                session_type TEXT CHECK(session_type IN ('reading', 'review', 'practice', 'quiz', 'other')),
                notes TEXT,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        ''')

        # Users table - user authentication and profiles
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                bio TEXT,
                avatar_url TEXT,
                preferences TEXT,  -- JSON user preferences
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')

        # User sessions table - for authentication tokens
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT NOT NULL UNIQUE,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # Study groups table - collaborative study groups
        conn.execute('''
            CREATE TABLE IF NOT EXISTS study_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                owner_id INTEGER NOT NULL,
                is_public BOOLEAN DEFAULT 1,
                max_members INTEGER DEFAULT 50,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # Group members table - many-to-many relationship between users and groups
        conn.execute('''
            CREATE TABLE IF NOT EXISTS group_members (
                group_id INTEGER,
                user_id INTEGER,
                role TEXT CHECK(role IN ('owner', 'admin', 'member')) DEFAULT 'member',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (group_id, user_id),
                FOREIGN KEY (group_id) REFERENCES study_groups(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # Shared materials table - materials shared within groups
        conn.execute('''
            CREATE TABLE IF NOT EXISTS shared_materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                group_id INTEGER,
                shared_by_user_id INTEGER,
                shared_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (group_id) REFERENCES study_groups(id) ON DELETE CASCADE,
                FOREIGN KEY (shared_by_user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # Full-text search virtual table for documents
        conn.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                title, content_preview, tags,
                content=documents,
                content_rowid=id
            )
        ''')

        # Triggers to keep FTS table in sync
        conn.execute('''
            CREATE TRIGGER IF NOT EXISTS documents_fts_insert AFTER INSERT ON documents
            BEGIN
                INSERT INTO documents_fts(rowid, title, content_preview, tags)
                VALUES (new.id, new.title, new.content_preview, new.tags);
            END
        ''')

        conn.execute('''
            CREATE TRIGGER IF NOT EXISTS documents_fts_delete AFTER DELETE ON documents
            BEGIN
                DELETE FROM documents_fts WHERE rowid = old.id;
            END
        ''')

        conn.execute('''
            CREATE TRIGGER IF NOT EXISTS documents_fts_update AFTER UPDATE ON documents
            BEGIN
                UPDATE documents_fts SET
                    title = new.title,
                    content_preview = new.content_preview,
                    tags = new.tags
                WHERE rowid = new.id;
            END
        ''')

        # Indexes for performance
        conn.execute('CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_documents_created ON documents(created_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_reviews_scheduled ON reviews(scheduled_date)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_reviews_document ON reviews(document_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_topics_parent ON topics(parent_topic_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_study_sessions_document ON study_sessions(document_id)')

        conn.commit()

    def _recreate_fts_table(self, conn: sqlite3.Connection) -> None:
        """Recreate the FTS table and triggers."""
        # Drop existing FTS table and triggers
        try:
            conn.execute('DROP TABLE IF EXISTS documents_fts')
        except:
            pass

        try:
            conn.execute('DROP TRIGGER IF EXISTS documents_fts_insert')
            conn.execute('DROP TRIGGER IF EXISTS documents_fts_delete')
            conn.execute('DROP TRIGGER IF EXISTS documents_fts_update')
        except:
            pass

        # Recreate FTS table
        conn.execute('''
            CREATE VIRTUAL TABLE documents_fts USING fts5(
                title, content_preview, tags,
                content=documents,
                content_rowid=id
            )
        ''')

        # Populate with existing data
        cursor = conn.execute('SELECT id, title, content_preview, tags FROM documents')
        for row in cursor:
            conn.execute('''
                INSERT INTO documents_fts(rowid, title, content_preview, tags)
                VALUES (?, ?, ?, ?)
            ''', (row['id'], row['title'] or '', row['content_preview'] or '', row['tags'] or ''))

        # Recreate triggers
        conn.execute('''
            CREATE TRIGGER documents_fts_insert AFTER INSERT ON documents
            BEGIN
                INSERT INTO documents_fts(rowid, title, content_preview, tags)
                VALUES (new.id, new.title, new.content_preview, new.tags);
            END
        ''')

        conn.execute('''
            CREATE TRIGGER documents_fts_delete AFTER DELETE ON documents
            BEGIN
                DELETE FROM documents_fts WHERE rowid = old.id;
            END
        ''')

        conn.execute('''
            CREATE TRIGGER documents_fts_update AFTER UPDATE ON documents
            BEGIN
                UPDATE documents_fts SET
                    title = new.title,
                    content_preview = new.content_preview,
                    tags = new.tags
                WHERE rowid = new.id;
            END
        ''')

        conn.commit()

    def close(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

    # Document CRUD operations
    def add_document(self, title: str, content_preview: str = "", file_path: str = "",
                    url: str = "", document_type: str = "note", tags: List[str] = None,
                    metadata: Dict[str, Any] = None) -> int:
        """
        Add a new document to the database.

        Returns:
            The ID of the newly created document
        """
        conn = self._get_connection()

        tags_json = json.dumps(tags or [])
        metadata_json = json.dumps(metadata or {})

        # Estimate word count and reading time
        word_count = len(content_preview.split()) if content_preview else 0
        reading_time = max(1, word_count // 200)  # Rough estimate: 200 words per minute

        cursor = conn.execute('''
            INSERT INTO documents (title, content_preview, file_path, url, document_type,
                                 word_count, reading_time_minutes, tags, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, content_preview, file_path, url, document_type,
              word_count, reading_time, tags_json, metadata_json))

        conn.commit()
        return cursor.lastrowid

    def get_document(self, document_id: int) -> Optional[Dict[str, Any]]:
        """Get a document by ID."""
        conn = self._get_connection()
        cursor = conn.execute('SELECT * FROM documents WHERE id = ?', (document_id,))
        row = cursor.fetchone()

        if row:
            return self._row_to_dict(row)
        return None

    def update_document(self, document_id: int, **updates) -> bool:
        """Update document fields."""
        if not updates:
            return False

        conn = self._get_connection()

        # Handle JSON fields
        if 'tags' in updates:
            updates['tags'] = json.dumps(updates['tags'])
        if 'metadata' in updates:
            updates['metadata'] = json.dumps(updates['metadata'])

        updates['updated_at'] = datetime.now().isoformat()

        set_clause = ', '.join(f'{k} = ?' for k in updates.keys())
        values = list(updates.values()) + [document_id]

        cursor = conn.execute(f'UPDATE documents SET {set_clause} WHERE id = ?', values)
        conn.commit()

        return cursor.rowcount > 0

    def delete_document(self, document_id: int) -> bool:
        """Delete a document."""
        conn = self._get_connection()
        cursor = conn.execute('DELETE FROM documents WHERE id = ?', (document_id,))
        conn.commit()
        return cursor.rowcount > 0

    def get_documents(self, limit: int = 50, offset: int = 0,
                     document_type: str = None) -> List[Dict[str, Any]]:
        """Get documents with optional filtering."""
        conn = self._get_connection()

        query = 'SELECT * FROM documents'
        params = []

        if document_type:
            query += ' WHERE document_type = ?'
            params.append(document_type)

        query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        cursor = conn.execute(query, params)
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    # Topic operations
    def add_topic(self, name: str, description: str = "", parent_topic_id: int = None,
                 color: str = "#3498db") -> int:
        """Add a new topic."""
        conn = self._get_connection()
        cursor = conn.execute('''
            INSERT INTO topics (name, description, parent_topic_id, color)
            VALUES (?, ?, ?, ?)
        ''', (name, description, parent_topic_id, color))
        conn.commit()
        return cursor.lastrowid

    def get_topics(self) -> List[Dict[str, Any]]:
        """Get all topics."""
        conn = self._get_connection()
        cursor = conn.execute('SELECT * FROM topics ORDER BY name')
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def assign_document_to_topic(self, document_id: int, topic_id: int) -> bool:
        """Assign a document to a topic."""
        conn = self._get_connection()
        try:
            conn.execute('INSERT INTO document_topics (document_id, topic_id) VALUES (?, ?)',
                        (document_id, topic_id))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Already assigned

    def get_documents_by_topic(self, topic_id: int) -> List[Dict[str, Any]]:
        """Get all documents for a topic."""
        conn = self._get_connection()
        cursor = conn.execute('''
            SELECT d.* FROM documents d
            JOIN document_topics dt ON d.id = dt.document_id
            WHERE dt.topic_id = ?
            ORDER BY d.created_at DESC
        ''', (topic_id,))
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    # Review operations
    def schedule_review(self, document_id: int, review_type: str = "initial",
                       scheduled_date: datetime = None) -> int:
        """Schedule a review for a document."""
        if scheduled_date is None:
            scheduled_date = datetime.now()

        conn = self._get_connection()
        cursor = conn.execute('''
            INSERT INTO reviews (document_id, review_type, scheduled_date)
            VALUES (?, ?, ?)
        ''', (document_id, review_type, scheduled_date.isoformat()))
        conn.commit()
        return cursor.lastrowid

    def get_pending_reviews(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get reviews that are due or overdue."""
        conn = self._get_connection()
        now = datetime.now().isoformat()
        cursor = conn.execute('''
            SELECT r.*, d.title as document_title
            FROM reviews r
            JOIN documents d ON r.document_id = d.id
            WHERE r.completed_date IS NULL AND r.scheduled_date <= ?
            ORDER BY r.scheduled_date ASC
            LIMIT ?
        ''', (now, limit))
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def complete_review(self, review_id: int, quality_rating: int, notes: str = "") -> bool:
        """Mark a review as completed and schedule next review using SM-2 algorithm."""
        conn = self._get_connection()

        # Get current review info
        cursor = conn.execute('SELECT * FROM reviews WHERE id = ?', (review_id,))
        review = cursor.fetchone()
        if not review:
            return False

        completed_date = datetime.now()
        ease_factor = review['ease_factor'] or 2.5
        interval_days = review['interval_days'] or 1

        # SM-2 algorithm for next interval
        if quality_rating >= 3:
            if review['review_type'] == 'initial':
                new_interval = 1
                new_type = 'spaced_1'
            elif review['review_type'] == 'spaced_1':
                new_interval = 6
                new_type = 'spaced_2'
            elif review['review_type'] == 'spaced_2':
                new_interval = 16
                new_type = 'spaced_3'
            else:
                new_interval = interval_days * ease_factor
                new_type = 'maintenance'

            # Adjust ease factor
            new_ease = ease_factor + (0.1 - (5 - quality_rating) * (0.08 + (5 - quality_rating) * 0.02))
            new_ease = max(1.3, new_ease)  # Minimum ease factor
        else:
            # Failed review - reset to initial
            new_interval = 1
            new_type = 'initial'
            new_ease = ease_factor

        next_review_date = completed_date + timedelta(days=new_interval)

        # Update current review
        conn.execute('''
            UPDATE reviews
            SET completed_date = ?, quality_rating = ?, notes = ?,
                ease_factor = ?, interval_days = ?
            WHERE id = ?
        ''', (completed_date.isoformat(), quality_rating, notes, new_ease, new_interval, review_id))

        # Schedule next review if not failed
        if quality_rating >= 3:
            conn.execute('''
                INSERT INTO reviews (document_id, review_type, scheduled_date, ease_factor, interval_days)
                VALUES (?, ?, ?, ?, ?)
            ''', (review['document_id'], new_type, next_review_date.isoformat(), new_ease, new_interval))

        conn.commit()
        return True

    # Full-text search
    def search_documents(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search documents using full-text search."""
        conn = self._get_connection()
        cursor = conn.execute('''
            SELECT d.*, rank
            FROM documents_fts dfts
            JOIN documents d ON d.id = dfts.rowid
            WHERE documents_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        ''', (query, limit))
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    # Study session tracking
    def log_study_session(self, document_id: int, start_time: datetime, end_time: datetime,
                         session_type: str = "reading", notes: str = "") -> int:
        """Log a study session."""
        duration = int((end_time - start_time).total_seconds() / 60)

        conn = self._get_connection()
        cursor = conn.execute('''
            INSERT INTO study_sessions (document_id, start_time, end_time, duration_minutes, session_type, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (document_id, start_time.isoformat(), end_time.isoformat(),
              duration, session_type, notes))
        conn.commit()
        return cursor.lastrowid

    def get_study_stats(self, document_id: int = None) -> Dict[str, Any]:
        """Get study statistics."""
        conn = self._get_connection()

        if document_id:
            cursor = conn.execute('''
                SELECT COUNT(*) as sessions_count,
                       SUM(duration_minutes) as total_minutes,
                       AVG(duration_minutes) as avg_session_minutes
                FROM study_sessions
                WHERE document_id = ?
            ''', (document_id,))
        else:
            cursor = conn.execute('''
                SELECT COUNT(*) as sessions_count,
                       SUM(duration_minutes) as total_minutes,
                       AVG(duration_minutes) as avg_session_minutes
                FROM study_sessions
            ''')

        row = cursor.fetchone()
        return dict(row) if row else {}

    # Backup and restore
    def backup_db(self, backup_path: Union[str, Path]) -> None:
        """Create a backup of the database using SQLite backup API."""
        backup_path = Path(backup_path)

        # Create backup directory if it doesn't exist
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        conn = self._get_connection()
        backup_conn = sqlite3.connect(str(backup_path))

        # Use SQLite's backup API which properly handles virtual tables
        with backup_conn:
            conn.backup(backup_conn)

        backup_conn.close()
        print(f"Database backed up to {backup_path}")

    @classmethod
    def restore_from_backup(cls, db_path: Union[str, Path], backup_path: Union[str, Path]) -> 'MetadataDB':
        """Restore database from backup file and return new instance."""
        db_path = Path(db_path)
        backup_path = Path(backup_path)

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        # Remove existing database if it exists
        if db_path.exists():
            db_path.unlink()

        # Copy the backup database file directly
        import shutil
        shutil.copy2(str(backup_path), str(db_path))

        # Verify the database is valid and complete
        conn = sqlite3.connect(str(db_path))
        try:
            # Check that all expected tables exist
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}

            expected_tables = {'documents', 'topics', 'document_topics', 'reviews', 'study_sessions', 'documents_fts'}
            missing_tables = expected_tables - tables

            if missing_tables:
                raise sqlite3.DatabaseError(f"Backup is missing tables: {missing_tables}")

            # Verify FTS table is functional
            conn.execute('SELECT * FROM documents_fts LIMIT 1')

        except sqlite3.OperationalError as e:
            conn.close()
            db_path.unlink()  # Clean up corrupted restore
            raise sqlite3.DatabaseError(f"Restored database is corrupted: {e}")

        conn.close()

        # Create instance without calling __init__ to avoid double initialization
        instance = cls.__new__(cls)
        instance.db_path = Path(db_path)
        instance.db_path.parent.mkdir(parents=True, exist_ok=True)
        instance.connection = None
        # Don't call _initialize_db since database is already set up

        print(f"Database restored from {backup_path}")
        return instance

    def restore_db(self, backup_path: str) -> None:
        """Restore database from backup (deprecated - use restore_from_backup classmethod)."""
        # For backward compatibility, delegate to the classmethod
        restored_db = self.restore_from_backup(self.db_path, backup_path)
        # Copy the restored database connection
        self.connection = restored_db.connection
        restored_db.connection = None  # Prevent double closing

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a database row to a dictionary."""
        result = dict(row)

        # Parse JSON fields
        if 'tags' in result and result['tags']:
            try:
                result['tags'] = json.loads(result['tags'])
            except:
                result['tags'] = []

        if 'metadata' in result and result['metadata']:
            try:
                result['metadata'] = json.loads(result['metadata'])
            except:
                result['metadata'] = {}

        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        conn = self._get_connection()

        stats = {}

        # Document counts by type
        cursor = conn.execute('''
            SELECT document_type, COUNT(*) as count
            FROM documents
            GROUP BY document_type
        ''')
        stats['documents_by_type'] = {row['document_type']: row['count'] for row in cursor}

        # Total counts
        cursor = conn.execute('SELECT COUNT(*) as count FROM documents')
        stats['total_documents'] = cursor.fetchone()['count']

        cursor = conn.execute('SELECT COUNT(*) as count FROM topics')
        stats['total_topics'] = cursor.fetchone()['count']

        cursor = conn.execute('SELECT COUNT(*) as count FROM reviews WHERE completed_date IS NOT NULL')
        stats['completed_reviews'] = cursor.fetchone()['count']

        cursor = conn.execute('SELECT COUNT(*) as count FROM reviews WHERE completed_date IS NULL')
        stats['pending_reviews'] = cursor.fetchone()['count']

        return stats

    # ===== USER MANAGEMENT METHODS =====

    def create_user(self, username: str, email: str, password_hash: str, full_name: str = None, bio: str = None) -> int:
        """Create a new user account."""
        conn = self._get_connection()
        cursor = conn.execute('''
            INSERT INTO users (username, email, password_hash, full_name, bio)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, email, password_hash, full_name, bio))
        conn.commit()
        return cursor.lastrowid

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        conn = self._get_connection()
        cursor = conn.execute('SELECT * FROM users WHERE username = ? AND is_active = 1', (username,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        conn = self._get_connection()
        cursor = conn.execute('SELECT * FROM users WHERE email = ? AND is_active = 1', (email,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        conn = self._get_connection()
        cursor = conn.execute('SELECT * FROM users WHERE id = ? AND is_active = 1', (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_user_profile(self, user_id: int, full_name: str = None, bio: str = None, avatar_url: str = None, preferences: Dict = None) -> bool:
        """Update user profile information."""
        conn = self._get_connection()
        updates = []
        params = []

        if full_name is not None:
            updates.append('full_name = ?')
            params.append(full_name)
        if bio is not None:
            updates.append('bio = ?')
            params.append(bio)
        if avatar_url is not None:
            updates.append('avatar_url = ?')
            params.append(avatar_url)
        if preferences is not None:
            updates.append('preferences = ?')
            params.append(json.dumps(preferences))

        if not updates:
            return False

        updates.append('updated_at = CURRENT_TIMESTAMP')
        params.append(user_id)

        query = f'UPDATE users SET {", ".join(updates)} WHERE id = ?'
        conn.execute(query, params)
        conn.commit()
        return conn.total_changes > 0

    def update_user_last_login(self, user_id: int) -> bool:
        """Update user's last login timestamp."""
        conn = self._get_connection()
        conn.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user_id,))
        conn.commit()
        return conn.total_changes > 0

    def create_session(self, user_id: int, session_token: str, expires_at: datetime) -> int:
        """Create a new user session."""
        conn = self._get_connection()
        cursor = conn.execute('''
            INSERT INTO user_sessions (user_id, session_token, expires_at)
            VALUES (?, ?, ?)
        ''', (user_id, session_token, expires_at.isoformat()))
        conn.commit()
        return cursor.lastrowid

    def get_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Get session by token."""
        conn = self._get_connection()
        cursor = conn.execute('''
            SELECT s.*, u.username, u.email, u.full_name
            FROM user_sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.session_token = ? AND s.expires_at > CURRENT_TIMESTAMP AND u.is_active = 1
        ''', (session_token,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def delete_session(self, session_token: str) -> bool:
        """Delete a user session."""
        conn = self._get_connection()
        conn.execute('DELETE FROM user_sessions WHERE session_token = ?', (session_token,))
        conn.commit()
        return conn.total_changes > 0

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions. Returns number of sessions deleted."""
        conn = self._get_connection()
        conn.execute('DELETE FROM user_sessions WHERE expires_at <= CURRENT_TIMESTAMP')
        conn.commit()
        return conn.total_changes

    # ===== STUDY GROUP METHODS =====

    def create_study_group(self, name: str, description: str, owner_id: int, is_public: bool = True, max_members: int = 50) -> int:
        """Create a new study group."""
        conn = self._get_connection()
        cursor = conn.execute('''
            INSERT INTO study_groups (name, description, owner_id, is_public, max_members)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, description, owner_id, is_public, max_members))

        group_id = cursor.lastrowid

        # Add owner as a member with 'owner' role
        conn.execute('''
            INSERT INTO group_members (group_id, user_id, role)
            VALUES (?, ?, 'owner')
        ''', (group_id, owner_id))

        conn.commit()
        return group_id

    def get_study_group(self, group_id: int) -> Optional[Dict[str, Any]]:
        """Get study group by ID."""
        conn = self._get_connection()
        cursor = conn.execute('''
            SELECT g.*, u.username as owner_username, u.full_name as owner_name,
                   COUNT(m.user_id) as member_count
            FROM study_groups g
            JOIN users u ON g.owner_id = u.id
            LEFT JOIN group_members m ON g.id = m.group_id
            WHERE g.id = ?
            GROUP BY g.id
        ''', (group_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_user_groups(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all groups for a user."""
        conn = self._get_connection()
        cursor = conn.execute('''
            SELECT g.*, m.role, m.joined_at,
                   u.username as owner_username, u.full_name as owner_name,
                   COUNT(m2.user_id) as member_count
            FROM study_groups g
            JOIN group_members m ON g.id = m.group_id
            JOIN users u ON g.owner_id = u.id
            LEFT JOIN group_members m2 ON g.id = m2.group_id
            WHERE m.user_id = ?
            GROUP BY g.id, m.role, m.joined_at
            ORDER BY m.joined_at DESC
        ''', (user_id,))
        return [dict(row) for row in cursor.fetchall()]

    def join_study_group(self, group_id: int, user_id: int) -> bool:
        """Join a user to a study group."""
        conn = self._get_connection()

        # Check if group exists and is public or user is invited
        cursor = conn.execute('SELECT is_public, max_members FROM study_groups WHERE id = ?', (group_id,))
        group = cursor.fetchone()
        if not group:
            return False

        # Check current member count
        cursor = conn.execute('SELECT COUNT(*) as count FROM group_members WHERE group_id = ?', (group_id,))
        member_count = cursor.fetchone()['count']

        if member_count >= group['max_members']:
            return False  # Group is full

        # Add user to group
        try:
            conn.execute('''
                INSERT INTO group_members (group_id, user_id, role)
                VALUES (?, ?, 'member')
            ''', (group_id, user_id))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # User already in group

    def leave_study_group(self, group_id: int, user_id: int) -> bool:
        """Remove a user from a study group."""
        conn = self._get_connection()

        # Don't allow owner to leave
        cursor = conn.execute('SELECT owner_id FROM study_groups WHERE id = ?', (group_id,))
        owner_id = cursor.fetchone()
        if owner_id and owner_id['owner_id'] == user_id:
            return False  # Owner cannot leave

        conn.execute('DELETE FROM group_members WHERE group_id = ? AND user_id = ?', (group_id, user_id))
        conn.commit()
        return conn.total_changes > 0

    def share_material_with_group(self, document_id: int, group_id: int, user_id: int) -> int:
        """Share a study material with a group."""
        conn = self._get_connection()

        # Verify user is a member of the group
        cursor = conn.execute('SELECT 1 FROM group_members WHERE group_id = ? AND user_id = ?', (group_id, user_id))
        if not cursor.fetchone():
            raise ValueError("User is not a member of this group")

        cursor = conn.execute('''
            INSERT INTO shared_materials (document_id, group_id, shared_by_user_id)
            VALUES (?, ?, ?)
        ''', (document_id, group_id, user_id))
        conn.commit()
        return cursor.lastrowid

    def get_group_shared_materials(self, group_id: int, user_id: int = None) -> List[Dict[str, Any]]:
        """Get materials shared with a group."""
        conn = self._get_connection()

        # If user_id provided, verify they are a member
        if user_id:
            cursor = conn.execute('SELECT 1 FROM group_members WHERE group_id = ? AND user_id = ?', (group_id, user_id))
            if not cursor.fetchone():
                return []  # User not in group

        cursor = conn.execute('''
            SELECT sm.*, d.title, d.content_preview, d.document_type, d.tags,
                   u.username as shared_by_username, u.full_name as shared_by_name,
                   sm.shared_at
            FROM shared_materials sm
            JOIN documents d ON sm.document_id = d.id
            JOIN users u ON sm.shared_by_user_id = u.id
            WHERE sm.group_id = ?
            ORDER BY sm.shared_at DESC
        ''', (group_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_group_members(self, group_id: int) -> List[Dict[str, Any]]:
        """Get all members of a study group."""
        conn = self._get_connection()
        cursor = conn.execute('''
            SELECT u.id, u.username, u.full_name, u.avatar_url, m.role, m.joined_at
            FROM group_members m
            JOIN users u ON m.user_id = u.id
            WHERE m.group_id = ?
            ORDER BY m.joined_at ASC
        ''', (group_id,))
        return [dict(row) for row in cursor.fetchall()]

    def search_public_groups(self, query: str = "", limit: int = 20) -> List[Dict[str, Any]]:
        """Search for public study groups."""
        conn = self._get_connection()
        search_pattern = f"%{query}%" if query else "%"

        cursor = conn.execute('''
            SELECT g.*, u.username as owner_username, u.full_name as owner_name,
                   COUNT(m.user_id) as member_count
            FROM study_groups g
            JOIN users u ON g.owner_id = u.id
            LEFT JOIN group_members m ON g.id = m.group_id
            WHERE g.is_public = 1
              AND (g.name LIKE ? OR g.description LIKE ?)
            GROUP BY g.id
            ORDER BY member_count DESC, g.created_at DESC
            LIMIT ?
        ''', (search_pattern, search_pattern, limit))
        return [dict(row) for row in cursor.fetchall()]

    # Additional user management methods for API
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email address."""
        conn = self._get_connection()
        cursor = conn.execute('SELECT * FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_user_profile(self, user_id: int, full_name: Optional[str] = None, email: Optional[str] = None):
        """Update user profile information."""
        conn = self._get_connection()
        updates = []
        params = []

        if full_name is not None:
            updates.append("full_name = ?")
            params.append(full_name)

        if email is not None:
            # Check if email is already taken by another user
            cursor = conn.execute('SELECT id FROM users WHERE email = ? AND id != ?', (email, user_id))
            if cursor.fetchone():
                raise ValueError("Email already in use by another user")
            updates.append("email = ?")
            params.append(email)

        if not updates:
            return

        params.append(user_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?"
        conn.execute(query, params)
        conn.commit()

    def user_can_access_group(self, user_id: int, group_id: int) -> bool:
        """Check if user can access a study group (member or public)."""
        conn = self._get_connection()

        # Check if user is a member
        cursor = conn.execute('SELECT 1 FROM group_members WHERE user_id = ? AND group_id = ?', (user_id, group_id))
        if cursor.fetchone():
            return True

        # Check if group is public
        cursor = conn.execute('SELECT is_public FROM study_groups WHERE group_id = ?', (group_id,))
        row = cursor.fetchone()
        return bool(row and row[0]) if row else False

    def is_user_in_group(self, user_id: int, group_id: int) -> bool:
        """Check if user is a member of a study group."""
        conn = self._get_connection()
        cursor = conn.execute('SELECT 1 FROM group_members WHERE user_id = ? AND group_id = ?', (user_id, group_id))
        return cursor.fetchone() is not None

    def leave_study_group(self, user_id: int, group_id: int):
        """Remove user from a study group."""
        conn = self._get_connection()
        conn.execute('DELETE FROM group_members WHERE user_id = ? AND group_id = ?', (user_id, group_id))
        conn.commit()

    def update_study_group(self, group_id: int, name: Optional[str] = None, description: Optional[str] = None, is_public: Optional[bool] = None):
        """Update study group information."""
        conn = self._get_connection()
        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)

        if description is not None:
            updates.append("description = ?")
            params.append(description)

        if is_public is not None:
            updates.append("is_public = ?")
            params.append(1 if is_public else 0)

        if not updates:
            return

        params.append(group_id)
        query = f"UPDATE study_groups SET {', '.join(updates)} WHERE group_id = ?"
        conn.execute(query, params)
        conn.commit()

    def delete_study_group(self, group_id: int):
        """Delete a study group and all associated data."""
        conn = self._get_connection()
        # Delete in correct order due to foreign keys
        conn.execute('DELETE FROM shared_materials WHERE group_id = ?', (group_id,))
        conn.execute('DELETE FROM group_members WHERE group_id = ?', (group_id,))
        conn.execute('DELETE FROM study_groups WHERE group_id = ?', (group_id,))
        conn.commit()

    def get_group_member_count(self, group_id: int) -> int:
        """Get the number of members in a study group."""
        conn = self._get_connection()
        cursor = conn.execute('SELECT COUNT(*) FROM group_members WHERE group_id = ?', (group_id,))
        row = cursor.fetchone()
        return row[0] if row else 0

    def unshare_material_from_group(self, material_id: int, group_id: int, shared_by: int):
        """Remove a shared material from a study group."""
        conn = self._get_connection()
        conn.execute('''
            DELETE FROM shared_materials
            WHERE material_id = ? AND group_id = ? AND shared_by_user_id = ?
        ''', (material_id, group_id, shared_by))
        conn.commit()