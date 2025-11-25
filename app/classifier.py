"""
AI-powered article classification using OpenAI GPT-4.1.
Uses the Responses API with structured outputs (Pydantic).
"""
from openai import OpenAI
from pydantic import BaseModel
from app.config import settings
from app.logger import setup_logger

logger = setup_logger(__name__)


# ============================================================================
# Structured Output Schema
# ============================================================================

class CategoryClassification(BaseModel):
    """
    Schema for GPT-4.1 structured output.
    The model returns JSON matching this exact structure.
    """
    category: str       # One of the predefined categories
    confidence: str     # "high", "medium", or "low"


# ============================================================================
# Classification Service
# ============================================================================

class ClassificationService:
    """
    Service for classifying news articles into categories using GPT-4.1.
    Falls back to mock mode if no API key is provided.
    """
    
    def __init__(self, mock_mode: bool = False):
        """
        Initialize the classifier.
        
        Args:
            mock_mode: If True, return random categories (useful for testing)
        """
        # Enable mock mode if no API key provided
        self.mock_mode = mock_mode or not settings.openai_api_key
        
        if not self.mock_mode:
            self.client = OpenAI(api_key=settings.openai_api_key)
            logger.info("Initialized OpenAI classification service")
        else:
            logger.info("Running in MOCK MODE - classifications will be randomized")
    
    def classify_article(self, title: str, summary: str = "") -> str:
        """
        Classify an article into one of the predefined categories.
        
        Args:
            title: Article title (required)
            summary: Article summary (optional, improves accuracy)
            
        Returns:
            Category name (e.g., "Cybersecurity", "AI", etc.)
        """
        if self.mock_mode:
            return self._mock_classify()
        
        try:
            # Combine title and summary for classification
            content = f"Title: {title}"
            if summary:
                content += f"\nSummary: {summary}"
            
            # Build category list for the prompt
            categories_str = ", ".join(settings.news_categories)
            
            # Call GPT-4.1 with structured output (Responses API)
            response = self.client.responses.parse(
                model="gpt-4.1",
                instructions=f"""You are a precise news categorization assistant. 
Analyze articles and classify them into ONE of these categories: {categories_str}.
Provide the category name and your confidence level (high, medium, or low).""",
                input=content,
                text_format=CategoryClassification  # Pydantic model for structured output
            )
            
            # Extract the parsed result
            classification = response.output_parsed
            category = classification.category
            
            # Validate - ensure returned category is in our list
            if category not in settings.news_categories:
                logger.warning(
                    f"LLM returned invalid category '{category}', defaulting to 'Software & Development'",
                    extra={"title": title[:50], "confidence": classification.confidence}
                )
                category = "Software & Development"
            
            logger.info(
                f"Classified article as '{category}' (confidence: {classification.confidence})",
                extra={"title": title[:50], "category": category, "confidence": classification.confidence}
            )
            
            return category
            
        except Exception as e:
            # On any error, default to a safe category
            logger.error(
                f"Error classifying article: {str(e)}",
                extra={"title": title[:50]},
                exc_info=True
            )
            return "Software & Development"
    
    def _mock_classify(self) -> str:
        """Return a random category for testing without API calls."""
        import random
        return random.choice(settings.news_categories)


# Global classifier instance - import this in other modules
classifier = ClassificationService()
