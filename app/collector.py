"""
News collection service.
Fetches articles from RSS feeds (Reddit, tech news sites).
No API keys needed - uses public RSS feeds only.
"""
import re
import time
import feedparser
import requests
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.config import settings
from app.database import get_session, Article
from app.classifier import classifier
from app.embeddings import embedding_service
from app.logger import setup_logger

logger = setup_logger(__name__)


class NewsCollector:
    """
    Collects news articles from RSS feeds.
    Handles fetching, parsing, classification, and storage.
    """
    
    def __init__(self):
        """Initialize collector with list of RSS feed URLs."""
        # RSS feeds - no API keys required!
        self.rss_feeds = [
            # Reddit (has public RSS feeds)
            "https://www.reddit.com/r/sysadmin/new.rss",
            # Tech news sites
            "https://feeds.arstechnica.com/arstechnica/index",
            "https://www.tomshardware.com/feeds/all",
            # Uncomment to add this source:
            # "https://hnrss.org/frontpage",
        ]
        logger.info(f"Initialized NewsCollector with {len(self.rss_feeds)} RSS feeds")
    
    def _extract_subreddit_name(self, feed_url: str) -> str:
        """Extract subreddit name from Reddit RSS URL for source labeling."""
        if "reddit.com/r/" in feed_url:
            parts = feed_url.split("/r/")
            if len(parts) > 1:
                subreddit = parts[1].split("/")[0]
                return f"reddit:r/{subreddit}"
        return "rss:reddit"
    
    def collect_from_rss(self) -> list[dict]:
        """
        Fetch articles from all configured RSS feeds.
        
        Returns:
            List of article dicts with title, url, summary, source, published_date
        """
        articles = []
        
        # Custom User-Agent to avoid being blocked (Useful for Reddit ! Otherwise we get 403)
        headers = {
            "User-Agent": "NEXNewsBot/1.0 (AI-powered news aggregator; https://github.com/arnaudlvq/NEXNews)"
        }
        
        for feed_url in self.rss_feeds:
            try:
                logger.info(f"Fetching articles from RSS feed: {feed_url}")
                
                # Fetch feed with custom headers
                response = requests.get(feed_url, headers=headers, timeout=10)
                
                # Handle HTTP errors gracefully
                if response.status_code == 429:
                    logger.warning(f"Rate limited (429) by {feed_url}")
                    continue
                elif response.status_code == 403:
                    logger.warning(f"Access forbidden (403) by {feed_url}")
                    continue
                elif response.status_code >= 400:
                    logger.warning(f"HTTP error {response.status_code} from {feed_url}")
                    continue
                
                # Parse RSS/Atom feed
                feed = feedparser.parse(response.content)
                
                if not feed.entries:
                    logger.warning(f"No entries found in feed: {feed_url}")
                    continue
                
                # Determine source label
                if "reddit.com" in feed_url:
                    source = self._extract_subreddit_name(feed_url)
                else:
                    source = f"rss:{feed.feed.title if hasattr(feed.feed, 'title') else 'unknown'}"
                
                # Process each entry (limit to 15 per feed to avoid overload)
                for entry in feed.entries[:15]:
                    # Extract published date
                    published_date = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        try:
                            published_date = datetime(*entry.published_parsed[:6])
                        except:
                            pass
                    
                    # Extract summary (try multiple RSS fields)
                    summary = ""
                    if hasattr(entry, "summary"):
                        summary = entry.summary[:500]
                    elif hasattr(entry, "description"):
                        summary = entry.description[:500]
                    elif hasattr(entry, "content"):
                        summary = entry.content[0].value[:500] if entry.content else ""
                    
                    # Strip HTML tags from summary
                    summary = re.sub(r'<[^>]+>', '', summary)
                    
                    articles.append({
                        "title": entry.title,
                        "url": entry.link,
                        "summary": summary.strip(),
                        "source": source,
                        "published_date": published_date
                    })
                
                logger.info(f"Collected {len(feed.entries[:15])} articles from {feed_url}")
                
            except Exception as e:
                logger.error(f"Error collecting from RSS feed {feed_url}: {str(e)}", exc_info=True)
        
        return articles
    
    def save_articles(self, articles: list[dict]) -> int:
        """
        Save articles to database with AI classification.
        
        Args:
            articles: List of article dicts from collect_from_rss()
            
        Returns:
            Number of new articles saved (duplicates skipped)
        """
        session = get_session()
        saved_count = 0
        
        for article_data in articles:
            try:
                # Classify the article using GPT-4.1
                category = classifier.classify_article(
                    title=article_data["title"],
                    summary=article_data.get("summary", "")
                )
                
                # Create database record
                article = Article(
                    title=article_data["title"],
                    url=article_data["url"],
                    summary=article_data.get("summary", ""),
                    source=article_data["source"],
                    category=category,
                    published_date=article_data.get("published_date")
                )
                
                session.add(article)
                session.commit()
                saved_count += 1
                
                # Create embedding for semantic search
                embedding_service.add_article(
                    article_id=article.id,
                    title=article.title,
                    summary=article.summary or "",
                    category=category,
                    source=article.source
                )
                
                logger.info(
                    f"Saved article: '{article.title[:50]}...' [Category: {category}]",
                    extra={"article_id": article.id, "category": category, "source": article.source}
                )
                
            except IntegrityError:
                # URL already exists - skip silently
                session.rollback()
                logger.debug(f"Article already exists: {article_data['url']}")
            except Exception as e:
                session.rollback()
                logger.error(
                    f"Error saving article: {str(e)}",
                    extra={"title": article_data.get("title", "")[:50]},
                    exc_info=True
                )
        
        session.close()
        return saved_count
    
    def run_collection_cycle(self):
        """
        Run a complete collection cycle: fetch -> classify -> save.
        Called periodically by the scheduler.
        """
        logger.info("=" * 80)
        logger.info("Starting news collection cycle")
        logger.info("=" * 80)
        
        start_time = time.time()
        
        # Collect from all RSS feeds
        all_articles = self.collect_from_rss()
        logger.info(f"Total articles collected: {len(all_articles)}")
        
        # Save with classification
        saved_count = self.save_articles(all_articles)
        
        elapsed_time = time.time() - start_time
        
        logger.info("=" * 80)
        logger.info(f"Collection cycle completed: {saved_count} new articles saved in {elapsed_time:.2f}s")
        logger.info("=" * 80)
        
        return saved_count
