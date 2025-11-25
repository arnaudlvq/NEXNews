"""
Configuration management for NEXNews application.
Loads settings from environment variables and .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings - automatically loaded from environment variables.
    Variable names are case-insensitive (e.g., OPENAI_API_KEY -> openai_api_key).
    """
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)
    
    # OpenAI API key for classification and embeddings
    openai_api_key: str = ""
    
    # SQLite database connection string
    database_url: str = "sqlite:///./data/nexnews.db"
    
    # How often to collect news (in minutes)
    ingestor_interval_minutes: int = 10
    
    # API server configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # OpenAI model for classification
    openai_model: str = "gpt-4.1"
    
    # Predefined categories for article classification
    news_categories: list[str] = [
        "Cybersecurity",
        "Artificial Intelligence & Emerging Tech",
        "Software & Development",
        "Hardware & Devices",
        "Tech Industry & Business",
        "Other"
    ]


# Global settings instance - import this in other modules
settings = Settings()
