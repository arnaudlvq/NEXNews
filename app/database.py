"""
Database models and connection management.
Uses SQLAlchemy ORM with SQLite backend.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings
import os

# SQLAlchemy base class for model definitions
Base = declarative_base()


class Article(Base):
    """
    Article model - represents a single news article in the database.
    URL is unique to prevent duplicate articles.
    """
    __tablename__ = "articles"
    
    # Primary key - auto-incrementing ID
    id = Column(Integer, primary_key=True, index=True)
    
    # Article content
    title = Column(String(500), nullable=False)
    url = Column(String(1000), unique=True, nullable=False, index=True)  # Unique constraint prevents duplicates
    summary = Column(Text, nullable=True)
    
    # Metadata
    source = Column(String(100), nullable=False, index=True)   # e.g., "reddit:r/sysadmin", "rss:Ars Technica"
    category = Column(String(100), nullable=True, index=True)  # e.g., "Cybersecurity", "AI"
    
    # Timestamps
    published_date = Column(DateTime, nullable=True)                    # Original publish date from RSS
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)  # When we saved it
    
    def to_dict(self) -> dict:
        """Convert article to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "source": self.source,
            "category": self.category,
            "published_date": self.published_date.isoformat() if self.published_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ============================================================================
# Database Connection Functions
# ============================================================================

def get_engine():
    """
    Create SQLAlchemy engine with SQLite.
    Automatically creates the data directory if it doesn't exist.
    """
    # Extract path from connection string and ensure directory exists
    db_path = settings.database_url.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    # Create engine - check_same_thread=False allows multi-threaded access for SQLite
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
    )
    return engine


def init_db():
    """Create all database tables if they don't exist."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    return engine


def get_session():
    """
    Get a new database session.
    Remember to close the session after use!
    """
    engine = get_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()
