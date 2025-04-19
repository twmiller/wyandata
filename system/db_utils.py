import time
import logging
from functools import wraps
from django.db import OperationalError, transaction

logger = logging.getLogger(__name__)

def with_retry(max_retries=5, retry_delay=0.2):
    """
    Decorator to retry database operations that might fail due to database locks
    
    Args:
        max_retries (int): Maximum number of retry attempts
        retry_delay (float): Initial delay between retries (will increase exponentially)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retry_count = 0
            delay = retry_delay
            
            while True:
                try:
                    # Try the database operation in a non-atomic transaction
                    # to avoid holding locks for too long
                    with transaction.atomic(durable=False):
                        return func(*args, **kwargs)
                except OperationalError as e:
                    if "database is locked" not in str(e) or retry_count >= max_retries:
                        # Re-raise if it's not a lock error or we've hit max retries
                        logger.error(f"Database operation failed after {retry_count} retries: {e}")
                        raise
                    
                    # Exponential backoff
                    retry_count += 1
                    logger.warning(f"Database locked, retrying operation (attempt {retry_count}/{max_retries})")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
        
        return wrapper
    return decorator
