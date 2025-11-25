"""
Semantic search using ChromaDB (vector database) and OpenAI embeddings.
Converts article text into 1536-dimensional vectors for similarity search.
"""
import os
import chromadb
from openai import OpenAI
from app.config import settings
from app.logger import setup_logger

logger = setup_logger(__name__)

# ChromaDB storage path (same volume as SQLite for persistence)
CHROMA_PERSIST_DIR = "./data/chroma"


class EmbeddingService:
    """
    Service for creating and searching article embeddings.
    Uses OpenAI's text-embedding-3-small model and ChromaDB for storage.
    """
    
    def __init__(self):
        """Initialize ChromaDB and OpenAI clients."""
        # Ensure storage directory exists
        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
        
        # Initialize ChromaDB with persistent storage
        self.chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        
        # Get or create collection for article embeddings
        self.collection = self.chroma_client.get_or_create_collection(
            name="articles",
            metadata={"description": "NEXNews article embeddings for semantic search"}
        )
        
        # Initialize OpenAI client for creating embeddings
        self.openai_client = OpenAI(api_key=settings.openai_api_key)
        logger.info(f"Initialized EmbeddingService with ChromaDB at {CHROMA_PERSIST_DIR}")
    
    def create_embedding(self, text: str) -> list[float]:
        """
        Convert text into a 1536-dimensional vector using OpenAI.
        
        Args:
            text: Text to embed (truncated to 8000 chars)
            
        Returns:
            List of 1536 floats representing the text semantically
        """
        try:
            response = self.openai_client.embeddings.create(
                input=text[:8000],  # OpenAI limit
                model="text-embedding-3-small"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error creating embedding: {str(e)}", exc_info=True)
            return []
    
    def add_article(self, article_id: int, title: str, summary: str, category: str, source: str):
        """
        Add an article embedding to ChromaDB.
        
        Args:
            article_id: Database ID (used as ChromaDB document ID)
            title: Article title
            summary: Article summary
            category: Article category (stored as metadata for filtering)
            source: Article source (stored as metadata)
        """
        try:
            # Combine title and summary for the embedding
            text = f"{title}. {summary}"
            
            # Skip if already exists (idempotent)
            existing = self.collection.get(ids=[str(article_id)])
            if existing and existing['ids']:
                logger.debug(f"Article {article_id} already has embedding")
                return
            
            # Create the embedding vector
            embedding = self.create_embedding(text)
            if not embedding:
                logger.warning(f"Failed to create embedding for article {article_id}: '{title[:50]}...'")
                return
            
            # Store in ChromaDB with metadata for filtering
            self.collection.add(
                ids=[str(article_id)],
                embeddings=[embedding],
                metadatas=[{
                    "title": title[:200],
                    "category": category,
                    "source": source
                }],
                documents=[text[:1000]]  # Store truncated text for reference
            )
            
            logger.debug(f"Added embedding for article {article_id}")
            
        except Exception as e:
            logger.error(f"Error adding embedding for article {article_id}: {str(e)}", exc_info=True)
    
    def delete_article(self, article_id: int):
        """
        Delete an article's embedding from ChromaDB.
        Call this when deleting an article from SQLite.
        """
        try:
            self.collection.delete(ids=[str(article_id)])
            logger.debug(f"Deleted embedding for article {article_id}")
        except Exception as e:
            logger.error(f"Error deleting embedding for article {article_id}: {str(e)}", exc_info=True)
    
    def search(self, query: str, category: str = None, limit: int = 20) -> list[dict]:
        """
        Semantic search for articles similar to the query.
        
        Args:
            query: Natural language search query
            category: Optional category filter
            limit: Maximum number of results
            
        Returns:
            List of {article_id, score, metadata} dicts, sorted by similarity
        """
        try:
            # Convert query to embedding vector
            query_embedding = self.create_embedding(query)
            if not query_embedding:
                logger.warning(f"Failed to create embedding for search query: '{query[:50]}...'")
                return []
            
            # Build category filter if provided
            where_filter = {"category": category} if category else None
            
            # Query ChromaDB for similar vectors
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_filter
            )
            
            # Format results with similarity scores
            matches = []
            if results and results['ids'] and results['ids'][0]:
                for i, article_id in enumerate(results['ids'][0]):
                    # Convert distance to similarity score (1 = identical, 0 = unrelated)
                    score = 1 - results['distances'][0][i] if results['distances'] else 0
                    matches.append({
                        "article_id": int(article_id),
                        "score": score,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {}
                    })
            
            logger.info(f"Semantic search for '{query[:50]}' found {len(matches)} results")
            return matches
            
        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}", exc_info=True)
            return []
    
    def get_stats(self) -> dict:
        """Get statistics about the embedding collection."""
        try:
            return {
                "total_embeddings": self.collection.count(),
                "storage_path": CHROMA_PERSIST_DIR
            }
        except Exception as e:
            logger.error(f"Error getting embedding stats: {str(e)}")
            return {"error": str(e)}
    
    def sync_missing_embeddings(self):
        """
        Verify all articles have embeddings, recompute any missing ones.
        Called at startup to ensure consistency between DB and ChromaDB.
        """
        from app.database import get_session, Article
        
        session = get_session()
        try:
            # Get all article IDs from the database
            all_articles = session.query(Article).all()
            db_count = len(all_articles)
            
            # Get all IDs that already have embeddings
            existing_ids = set()
            if self.collection.count() > 0:
                # ChromaDB get() with no filter returns all
                all_embeddings = self.collection.get()
                existing_ids = set(all_embeddings['ids']) if all_embeddings['ids'] else set()
            
            # Find articles missing embeddings
            missing_count = 0
            for article in all_articles:
                if str(article.id) not in existing_ids:
                    missing_count += 1
                    logger.info(f"Recomputing embedding for article {article.id}: '{article.title[:50]}...'")
                    self.add_article(
                        article_id=article.id,
                        title=article.title,
                        summary=article.summary or "",
                        category=article.category,
                        source=article.source
                    )
            
            logger.info(f"Embedding sync complete: {db_count} articles in DB, {missing_count} embeddings recomputed")
            
        except Exception as e:
            logger.error(f"Error syncing embeddings: {str(e)}", exc_info=True)
        finally:
            session.close()


# Global instance - import this in other modules
embedding_service = EmbeddingService()
