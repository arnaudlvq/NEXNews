"""
FastAPI REST API for NEXNews.
Provides endpoints for searching and retrieving news articles.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.database import get_session, Article
from app.embeddings import embedding_service
from app.config import settings
from app.logger import setup_logger

logger = setup_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="NEXNews API",
    description="AI-powered news aggregation API with semantic search",
    version="1.0.0"
)


# Request model for search endpoint
class SearchRequest(BaseModel):
    """Search query parameters."""
    prompt: str | None = None  # Natural language search prompt
    category: str | None = None  # Optional category filter
    limit: int = 10  # Max results (default 10)


@app.post("/news/search")
def search_news(request: SearchRequest):
    """
    Search articles using semantic search (ChromaDB + OpenAI embeddings).
    
    POST /news/search
    Body: {"prompt": "kubernetes deployment", "category": "Security", "limit": 5}
    
    Returns: List of matching articles with relevance scores
    """
    # Validate: need at least prompt or category
    if not request.prompt and not request.category:
        raise HTTPException(status_code=400, detail="At least one of 'prompt' or 'category' is required")
    
    # Validate category if provided
    valid_categories = settings.news_categories
    if request.category and request.category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid category. Valid options: {valid_categories}")
    
    logger.info(f"Search request: prompt='{request.prompt}', category={request.category}")
    
    session = get_session()
    
    # If prompt provided, use semantic search
    if request.prompt:
        results = embedding_service.search(
            query=request.prompt,
            category=request.category,
            limit=request.limit
        )
        
        # Enrich results with full article data
        articles = []
        for result in results:
            article = session.query(Article).filter(Article.id == result["article_id"]).first()
            if article:
                articles.append(article.to_dict())
        
        search_type = "semantic"
    else:
        # Category-only search: simple DB query
        query = session.query(Article).filter(Article.category == request.category)
        articles = [a.to_dict() for a in query.limit(request.limit).all()]
        search_type = "category"
    
    session.close()
    
    logger.info(f"Search returned {len(articles)} results")
    return {
        "count": len(articles),
        "articles": articles,
        "search_type": search_type
    }


@app.get("/news/{article_id}")
def get_article(article_id: int):
    """
    Retrieve a single article by ID.
    
    GET /news/123
    
    Returns: Full article object or 404
    """
    session = get_session()
    article = session.query(Article).filter(Article.id == article_id).first()
    session.close()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    return article.to_dict()


@app.get("/health")
def health_check():
    """
    Health check endpoint for monitoring.
    
    GET /health
    
    Returns: {"status": "healthy"}
    """
    return {"status": "healthy"}


@app.get("/stats") # Used for monitoring and dashboarding, not for regular user access
def get_stats():
    """
    Get combined statistics (database + embeddings).
    
    GET /stats
    
    Returns: Total count, breakdown by category/source, and embedding stats
    """
    session = get_session()
    
    # Total articles
    total = session.query(Article).count()
    
    # Group by category
    from sqlalchemy import func
    categories = session.query(
        Article.category, func.count(Article.id)
    ).group_by(Article.category).all()
    
    # Group by source
    sources = session.query(
        Article.source, func.count(Article.id)
    ).group_by(Article.source).all()
    
    session.close()
    
    # Get embedding stats
    embedding_stats = embedding_service.get_stats()
    
    return {
        "total_articles": total,
        "by_category": {cat: count for cat, count in categories},
        "by_source": {src: count for src, count in sources},
        "embeddings": embedding_stats
    }