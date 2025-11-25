"""
Basic functionality tests for NEXNews API

Tests core endpoints:
- POST /news/search - Search functionality
- GET /news/{id} - Article retrieval
- GET /health - Health check
- GET /stats - Statistics
"""
import pytest
from fastapi.testclient import TestClient
from app.api import app
from datetime import datetime, timezone
from app.database import init_db, get_session, Article
from app.embeddings import embedding_service
from app.config import settings

# Create test client
client = TestClient(app)


@pytest.fixture(scope="module")
def setup_database():
    """Initialize test database"""
    init_db()
    yield
    # Cleanup: remove test articles from SQLite AND ChromaDB
    session = get_session()
    test_articles = session.query(Article).filter(Article.source == "test:source").all()
    for article in test_articles:
        embedding_service.delete_article(article.id)  # Remove from ChromaDB
        session.delete(article)  # Remove from SQLite
    session.commit()
    session.close()


@pytest.fixture
def sample_article(setup_database):
    """Create a sample article for testing, cleaned up after module"""
    session = get_session()
    try:
        # Check if test article already exists
        existing = session.query(Article).filter(Article.url == "https://example.com/test-article").first()
        if existing:
            return existing.id
        
        article = Article(
            title="Test Security Article",
            url="https://example.com/test-article",
            summary="This is a test article about cybersecurity and data protection.",
            source="test:source",
            category="Cybersecurity",
            created_at=datetime.now(timezone.utc)
        )
        session.add(article)
        session.commit()
        session.refresh(article)
        return article.id
    finally:
        session.close()


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check(self):
        """Test GET /health returns healthy status"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestStatsEndpoint:
    """Test statistics endpoint"""
    
    def test_stats_structure(self, setup_database):
        """Test GET /stats returns correct structure"""
        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "total_articles" in data
        assert "by_category" in data
        assert "by_source" in data
        
        # Check types
        assert isinstance(data["total_articles"], int)
        assert isinstance(data["by_category"], dict)
        assert isinstance(data["by_source"], dict)


class TestArticleRetrieval:
    """Test article retrieval endpoint"""
    
    def test_get_article_by_id(self, setup_database, sample_article):
        """Test GET /news/{id} returns article"""
        response = client.get(f"/news/{sample_article}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == sample_article
        assert "title" in data
        assert "url" in data
        assert "summary" in data
        assert "category" in data
        assert "source" in data
    
    def test_get_nonexistent_article(self, setup_database):
        """Test GET /news/{id} with invalid ID returns 404"""
        response = client.get("/news/999999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestSearchEndpoint:
    """Test search functionality"""
    
    def test_search_with_prompt(self, setup_database, sample_article):
        """Test POST /news/search with prompt"""
        response = client.post(
            "/news/search",
            json={"prompt": "security", "limit": 10}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "count" in data
        assert "articles" in data
        assert "search_type" in data
        assert isinstance(data["articles"], list)
    
    def test_search_with_category(self, setup_database, sample_article):
        """Test POST /news/search with category filter"""
        response = client.post(
            "/news/search",
            json={"category": "Cybersecurity", "limit": 10}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] >= 0
        assert isinstance(data["articles"], list)
        
        # All returned articles should match category
        for article in data["articles"]:
            assert article["category"] == "Cybersecurity"
    
    def test_search_with_prompt_and_category(self, setup_database, sample_article):
        """Test POST /news/search with both prompt and category"""
        response = client.post(
            "/news/search",
            json={
                "prompt": "data protection",
                "category": "Cybersecurity",
                "limit": 5
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "articles" in data
    
    def test_search_without_filters(self, setup_database):
        """Test POST /news/search without prompt or category returns error"""
        response = client.post(
            "/news/search",
            json={"limit": 10}
        )
        assert response.status_code == 400
        assert "at least one" in response.json()["detail"].lower()
    
    def test_search_with_invalid_category(self, setup_database):
        """Test POST /news/search with invalid category returns error"""
        response = client.post(
            "/news/search",
            json={"category": "InvalidCategory", "limit": 10}
        )
        assert response.status_code == 400
        assert "invalid category" in response.json()["detail"].lower()
    
    def test_search_respects_limit(self, setup_database, sample_article):
        """Test POST /news/search respects limit parameter"""
        response = client.post(
            "/news/search",
            json={"prompt": "test", "limit": 3}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["articles"]) <= 3


class TestRootEndpoint:
    """Test root endpoint"""
    
    def test_root_returns_api_info(self):
        """Test GET / returns API information"""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "service" in data
        assert data["service"] == "NEXNews API"
        assert "version" in data
        assert "endpoints" in data
        assert "categories" in data
        
        # Check endpoints are documented
        assert "POST /news/search" in data["endpoints"]
        assert "GET /news/{article_id}" in data["endpoints"]
    
    def test_categories_list(self):
        """Test root endpoint returns valid categories"""
        response = client.get("/")
        assert response.status_code == 200
        
        categories = response.json()["categories"]
        assert isinstance(categories, list)
        assert len(categories) > 0
        assert "Cybersecurity" in categories


class TestEmbeddingsEndpoint:
    """Test embeddings statistics endpoint"""
    
    def test_embeddings_stats(self, setup_database):
        """Test GET /embeddings/stats returns statistics"""
        response = client.get("/embeddings/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_embeddings" in data
        assert isinstance(data["total_embeddings"], int)
        assert data["total_embeddings"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
