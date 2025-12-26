"""
Production-ready logging configuration
Structured logging with JSON format for GCP Cloud Logging
"""

import logging
import sys
from pythonjsonlogger import jsonlogger
from datetime import datetime


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields"""
    
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        
        # Add timestamp
        if not log_record.get('timestamp'):
            log_record['timestamp'] = datetime.utcnow().isoformat()
        
        # Add severity (for GCP Cloud Logging)
        if log_record.get('levelname'):
            log_record['severity'] = log_record['levelname']
        
        # Add service information
        log_record['service'] = 'multilingual-news-radio'


def setup_logging(log_level: str = "INFO", json_format: bool = True):
    """
    Setup production logging
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Use JSON formatting (True for production, False for dev)
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    
    if json_format:
        # JSON format for production (GCP Cloud Logging)
        formatter = CustomJsonFormatter(
            '%(timestamp)s %(severity)s %(name)s %(message)s'
        )
    else:
        # Human-readable format for development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # Set log levels for noisy libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('kafka').setLevel(logging.WARNING)
    
    logging.info(f"Logging configured: level={log_level}, json_format={json_format}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


# Context manager for request tracing
class LogContext:
    """Add context to logs (e.g., request ID)"""
    
    def __init__(self, **kwargs):
        self.context = kwargs
        self.old_factory = logging.getLogRecordFactory()
    
    def __enter__(self):
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, *args):
        logging.setLogRecordFactory(self.old_factory)


# Example usage
if __name__ == "__main__":
    # Development
    setup_logging("DEBUG", json_format=False)
    logger = get_logger(__name__)
    logger.info("This is a development log")
    
    # Production
    setup_logging("INFO", json_format=True)
    logger = get_logger(__name__)
    logger.info("This is a production log", extra={"user_id": "123", "action": "login"})
    
    # With context
    with LogContext(request_id="abc-123", user_id="456"):
        logger.info("Processing request")