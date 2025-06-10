import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging(log_level: str = "INFO", log_file: str = None):
    """Setup logging configuration with proper Unicode support for Windows"""
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Set encoding based on platform
    if sys.platform.startswith('win'):
        # Force UTF-8 encoding on Windows
        encoding = 'utf-8'
        # Set console to UTF-8 if possible
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except AttributeError:
            # For older Python versions, use environment variable
            os.environ['PYTHONIOENCODING'] = 'utf-8'
    else:
        encoding = 'utf-8'
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S',
        handlers=[
            # Console handler with UTF-8 encoding
            logging.StreamHandler(sys.stdout),
        ],
        force=True
    )
    
    # Add file handler if log_file is specified
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding=encoding  # Explicit UTF-8 encoding
        )
        file_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        )
        logging.getLogger().addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

# Emoji-safe logging functions
def safe_log_info(logger, message: str):
    """Log info message with emoji fallback for Windows"""
    try:
        logger.info(message)
    except UnicodeEncodeError:
        # Remove emojis and log plain text
        safe_message = remove_emojis(message)
        logger.info(f"[INFO] {safe_message}")

def safe_log_error(logger, message: str):
    """Log error message with emoji fallback for Windows"""
    try:
        logger.error(message)
    except UnicodeEncodeError:
        # Remove emojis and log plain text
        safe_message = remove_emojis(message)
        logger.error(f"[ERROR] {safe_message}")

def safe_log_warning(logger, message: str):
    """Log warning message with emoji fallback for Windows"""
    try:
        logger.warning(message)
    except UnicodeEncodeError:
        # Remove emojis and log plain text
        safe_message = remove_emojis(message)
        logger.warning(f"[WARNING] {safe_message}")

def remove_emojis(text: str) -> str:
    """Remove emojis from text for safe logging"""
    import re
    # Remove emoji characters
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+", 
        flags=re.UNICODE
    )
    return emoji_pattern.sub(r'', text).strip()

# Create a safe logger class
class SafeLogger:
    """Logger wrapper that handles Unicode encoding issues"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def info(self, message: str):
        safe_log_info(self.logger, message)
    
    def error(self, message: str):
        safe_log_error(self.logger, message)
    
    def warning(self, message: str):
        safe_log_warning(self.logger, message)
    
    def debug(self, message: str):
        try:
            self.logger.debug(message)
        except UnicodeEncodeError:
            safe_message = remove_emojis(message)
            self.logger.debug(f"[DEBUG] {safe_message}")

def get_safe_logger(name: str = __name__) -> SafeLogger:
    """Get a Unicode-safe logger"""
    return SafeLogger(logging.getLogger(name))
