"""
Logging configuration for NEXNews.
Outputs structured JSON logs for easy parsing and analysis.
"""
import logging
import sys
from pythonjsonlogger.json import JsonFormatter


def setup_logger(name: str) -> logging.Logger:
    """
    Create a logger with JSON formatting.
    
    Usage:
        logger = setup_logger(__name__)
        logger.info("Message", extra={"key": "value"})
    
    Output format:
        {"asctime": "2025-11-25 10:30:45", "name": "app.collector", "levelname": "INFO", "message": "..."}
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers to avoid duplicates
    logger.handlers = []
    
    # Create console handler that outputs to stdout
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Use JSON formatter for structured logging
    formatter = JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger
