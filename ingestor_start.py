"""
Background ingestor service for NEXNews.
Runs on a schedule to collect and process news articles.

Usage: python ingestor_start.py (or via Docker)
"""
import time
import schedule
from app.config import settings
from app.database import init_db
from app.collector import NewsCollector
from app.embeddings import embedding_service
from app.logger import setup_logger

logger = setup_logger(__name__)


def run_ingestor():
    """
    Main entry point for the background ingestor service.
    
    - Initializes database tables
    - Runs initial collection immediately
    - Schedules periodic collection based on config
    - Runs forever until killed
    """
    logger.info("=" * 80)
    logger.info("Starting NEXNews Ingestor Service")
    logger.info(f"Collection interval: {settings.ingestor_interval_minutes} minutes")
    logger.info(f"Categories: {settings.news_categories}")
    logger.info("=" * 80)
    
    # Ensure database tables exist
    init_db()
    logger.info("Database initialized")
    
    # Verify all articles have embeddings, recompute if missing
    logger.info("Checking for missing embeddings...")
    embedding_service.sync_missing_embeddings()
    
    # Create collector instance
    collector = NewsCollector()
    
    # Run immediately on startup
    logger.info("Running initial collection cycle...")
    collector.run_collection_cycle()
    
    # Schedule recurring collections
    schedule.every(settings.ingestor_interval_minutes).minutes.do(
        collector.run_collection_cycle
    )
    logger.info(f"Scheduled collection every {settings.ingestor_interval_minutes} minutes")
    
    # Run scheduler loop forever
    logger.info("Entering scheduler loop (Ctrl+C to stop)")
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    run_ingestor()
