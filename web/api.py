#!/usr/bin/env python3
"""
Study System Web API - FastAPI Backend

Provides REST API endpoints for the AI-assisted study system.
Serves the React frontend and handles all study system operations.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kb.study_system import StudySystem
from .auth_api import router as auth_router
from .groups_api import router as groups_router


# Pydantic models for API requests/responses
class StudyMaterialRequest(BaseModel):
    title: str
    content: str
    source_type: str = "note"
    source_path: Optional[str] = None
    source_url: Optional[str] = None
    tags: Optional[List[str]] = None

class StudyMaterialResponse(BaseModel):
    document_id: int
    title: str
    status: str

class SearchRequest(BaseModel):
    query: str
    limit: int = 10

class SearchResult(BaseModel):
    document_id: int
    title: str
    content_preview: str
    similarity_score: float
    tags: List[str]

class TopicRequest(BaseModel):
    name: str
    description: str = ""

class TopicResponse(BaseModel):
    topic_id: int
    name: str
    description: str
    document_count: int

class ContentGenerationRequest(BaseModel):
    topic: str
    content_type: str = "summary"  # summary, flashcards, questions, explanation
    difficulty: str = "intermediate"  # beginner, intermediate, advanced

class ContentGenerationResponse(BaseModel):
    content: str
    content_type: str
    topic: str
    generated_at: str

class StudyStats(BaseModel):
    total_documents: int
    total_topics: int
    pending_reviews: int
    completed_reviews: int
    average_study_time: float


# Global study system instance
study_system: Optional[StudySystem] = None


def get_study_system() -> StudySystem:
    """Get or create the study system instance."""
    global study_system
    if study_system is None:
        # Initialize study system with demo-friendly settings
        study_system = StudySystem(
            db_path="web/study_system.db",
            vector_store_path="web/study_vectors.index",
            enable_copilot=False  # Disable for web demo
        )
    return study_system


# Create main FastAPI app
app = FastAPI(title="AI Study System")

# Create API sub-app
api_app = FastAPI(
    title="AI Study System API",
    description="REST API for the AI-assisted study system",
    version="1.0.0"
)

# Mount API sub-app at /api
app.mount("/api", api_app)

# Include authentication and groups routers
api_app.include_router(auth_router)
api_app.include_router(groups_router)

# CORS middleware for API
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8002", "http://127.0.0.1:8002"],  # React dev server and our frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@api_app.on_event("startup")
async def startup_event():
    """Initialize the study system on startup."""
    try:
        get_study_system()
        print("✅ Study system initialized")
    except Exception as e:
        print(f"❌ Failed to initialize study system: {e}")


@api_app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "AI Study System API", "version": "1.0.0"}


@api_app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        stats = get_study_system().get_study_stats()
        return {"status": "healthy", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")


# Study Materials API
@api_app.post("/materials", response_model=StudyMaterialResponse)
async def add_study_material(material: StudyMaterialRequest):
    """Add a new study material."""
    try:
        system = get_study_system()
        doc_id = system.add_study_material(
            title=material.title,
            content=material.content,
            source_type=material.source_type,
            source_path=material.source_path,
            source_url=material.source_url,
            tags=material.tags
        )
        return StudyMaterialResponse(
            document_id=doc_id,
            title=material.title,
            status="added"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add material: {e}")


@api_app.get("/materials")
async def get_study_materials(limit: int = 50, offset: int = 0):
    """Get all study materials."""
    try:
        system = get_study_system()
        # This would need to be implemented in StudySystem
        # For now, return a placeholder
        return {"materials": [], "total": 0, "limit": limit, "offset": offset}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get materials: {e}")


# Search API
@api_app.post("/search", response_model=List[SearchResult])
async def search_knowledge(search: SearchRequest):
    """Search for knowledge using semantic search."""
    try:
        system = get_study_system()
        results = system.search_knowledge(search.query, search.limit)

        # Convert to response format
        response_results = []
        for result in results:
            doc = result["document"]
            response_results.append(SearchResult(
                document_id=doc["id"],
                title=doc["title"],
                content_preview=doc["content_preview"][:200] + "..." if len(doc["content_preview"]) > 200 else doc["content_preview"],
                similarity_score=result["similarity_score"],
                tags=doc.get("tags", [])
            ))

        return response_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")


@api_app.get("/search/text")
async def search_text(query: str, limit: int = 10):
    """Full-text search in study materials."""
    try:
        system = get_study_system()
        results = system.search_documents(query, limit)

        # Convert to response format
        response_results = []
        for result in results:
            response_results.append({
                "document_id": result["id"],
                "title": result["title"],
                "content_preview": result["content_preview"][:200] + "..." if len(result["content_preview"]) > 200 else result["content_preview"],
                "tags": result.get("tags", [])
            })

        return {"results": response_results, "query": query}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text search failed: {e}")


# Topics API
@api_app.post("/topics", response_model=TopicResponse)
async def create_topic(topic: TopicRequest):
    """Create a new topic."""
    try:
        system = get_study_system()
        topic_id = system.create_topic(topic.name, topic.description)

        return TopicResponse(
            topic_id=topic_id,
            name=topic.name,
            description=topic.description,
            document_count=0
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create topic: {e}")


@api_app.get("/topics")
async def get_topics():
    """Get all topics."""
    try:
        system = get_study_system()
        # This would need to be implemented in StudySystem
        # For now, return a placeholder
        return {"topics": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get topics: {e}")


# Content Generation API (when Copilot is available)
@api_app.post("/generate", response_model=ContentGenerationResponse)
async def generate_content(request: ContentGenerationRequest):
    """Generate study content using AI."""
    try:
        system = get_study_system()
        if system.copilot is None:
            raise HTTPException(status_code=503, detail="AI content generation not available")

        content = system.generate_study_content(
            topic=request.topic,
            content_type=request.content_type,
            difficulty=request.difficulty
        )

        return ContentGenerationResponse(
            content=str(content),
            content_type=request.content_type,
            topic=request.topic,
            generated_at="now"  # Would use proper timestamp
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Content generation failed: {e}")


# Statistics API
@api_app.get("/stats", response_model=StudyStats)
async def get_study_stats():
    """Get study system statistics."""
    try:
        system = get_study_system()
        stats = system.get_study_stats()

        return StudyStats(
            total_documents=stats.get("total_documents", 0),
            total_topics=stats.get("total_topics", 0),
            pending_reviews=stats.get("pending_reviews", 0),
            completed_reviews=stats.get("completed_reviews", 0),
            average_study_time=stats.get("average_study_time", 0.0)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {e}")


# Mount static files for frontend BEFORE API routes
frontend_path = Path(__file__).parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
    print("✅ Frontend static files mounted at root")
else:
    print("⚠️  Frontend directory not found, running API-only mode")


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)