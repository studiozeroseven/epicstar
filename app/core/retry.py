"""Retry logic with exponential backoff."""

import asyncio
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Type

from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.logging import get_logger
from app.utils.exceptions import GitOperationError, OneDevAPIError, RetryableError

logger = get_logger(__name__)


# Default retry configuration
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_MIN_WAIT = 4  # seconds
DEFAULT_MAX_WAIT = 60  # seconds
DEFAULT_MULTIPLIER = 2


def get_retry_config(
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    min_wait: int = DEFAULT_MIN_WAIT,
    max_wait: int = DEFAULT_MAX_WAIT,
    multiplier: int = DEFAULT_MULTIPLIER,
    retry_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
) -> AsyncRetrying:
    """
    Get retry configuration with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time in seconds
        max_wait: Maximum wait time in seconds
        multiplier: Exponential backoff multiplier
        retry_exceptions: Tuple of exception types to retry on
        
    Returns:
        AsyncRetrying instance configured with specified parameters
    """
    if retry_exceptions is None:
        retry_exceptions = (RetryableError, GitOperationError, OneDevAPIError)
    
    return AsyncRetrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(
            multiplier=multiplier,
            min=min_wait,
            max=max_wait,
        ),
        retry=retry_if_exception_type(retry_exceptions),
        reraise=True,
    )


def with_retry(
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    min_wait: int = DEFAULT_MIN_WAIT,
    max_wait: int = DEFAULT_MAX_WAIT,
    multiplier: int = DEFAULT_MULTIPLIER,
    retry_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
) -> Callable:
    """
    Decorator to add retry logic to async functions.
    
    Usage:
        @with_retry(max_attempts=5)
        async def my_function():
            # Your code here
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            retry_config = get_retry_config(
                max_attempts=max_attempts,
                min_wait=min_wait,
                max_wait=max_wait,
                multiplier=multiplier,
                retry_exceptions=retry_exceptions,
            )
            
            attempt = 0
            async for attempt_state in retry_config:
                with attempt_state:
                    attempt += 1
                    try:
                        logger.info(
                            f"Executing {func.__name__} (attempt {attempt}/{max_attempts})"
                        )
                        result = await func(*args, **kwargs)
                        if attempt > 1:
                            logger.info(
                                f"{func.__name__} succeeded after {attempt} attempts"
                            )
                        return result
                    except Exception as e:
                        logger.warning(
                            f"{func.__name__} failed on attempt {attempt}: {str(e)}"
                        )
                        if attempt >= max_attempts:
                            logger.error(
                                f"{func.__name__} failed after {max_attempts} attempts"
                            )
                        raise
            
            # This should never be reached due to reraise=True
            raise RetryError("Retry failed")
        
        return wrapper
    return decorator


async def retry_with_backoff(
    func: Callable,
    *args: Any,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    min_wait: int = DEFAULT_MIN_WAIT,
    max_wait: int = DEFAULT_MAX_WAIT,
    multiplier: int = DEFAULT_MULTIPLIER,
    retry_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    **kwargs: Any,
) -> Any:
    """
    Execute a function with retry logic.
    
    This is a functional alternative to the @with_retry decorator.
    
    Args:
        func: Async function to execute
        *args: Positional arguments for func
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time in seconds
        max_wait: Maximum wait time in seconds
        multiplier: Exponential backoff multiplier
        retry_exceptions: Tuple of exception types to retry on
        **kwargs: Keyword arguments for func
        
    Returns:
        Result of func execution
        
    Raises:
        RetryError: If all retry attempts fail
    """
    retry_config = get_retry_config(
        max_attempts=max_attempts,
        min_wait=min_wait,
        max_wait=max_wait,
        multiplier=multiplier,
        retry_exceptions=retry_exceptions,
    )
    
    attempt = 0
    async for attempt_state in retry_config:
        with attempt_state:
            attempt += 1
            try:
                logger.info(
                    f"Executing {func.__name__} (attempt {attempt}/{max_attempts})"
                )
                result = await func(*args, **kwargs)
                if attempt > 1:
                    logger.info(
                        f"{func.__name__} succeeded after {attempt} attempts"
                    )
                return result
            except Exception as e:
                logger.warning(
                    f"{func.__name__} failed on attempt {attempt}: {str(e)}"
                )
                if attempt >= max_attempts:
                    logger.error(
                        f"{func.__name__} failed after {max_attempts} attempts"
                    )
                raise
    
    # This should never be reached due to reraise=True
    raise RetryError("Retry failed")

