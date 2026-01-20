"""Retry logic utilities."""

import asyncio
import functools
import logging
from typing import Callable, Type, Tuple, Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

logger = logging.getLogger(__name__)


def async_retry(
    max_attempts: int = 3,
    exponential_base: int = 2,
    exponential_max: int = 10,
    retry_on: Tuple[Type[Exception], ...] = (Exception,),
):
    """Decorator for async functions with exponential backoff retry.

    Args:
        max_attempts: Maximum number of retry attempts
        exponential_base: Base for exponential backoff
        exponential_max: Maximum wait time in seconds
        retry_on: Tuple of exception types to retry on

    Returns:
        Decorated function with retry logic
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=1, max=exponential_max, exp_base=exponential_base),
        retry=retry_if_exception_type(retry_on),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


def sync_retry(
    max_attempts: int = 3,
    exponential_base: int = 2,
    exponential_max: int = 10,
    retry_on: Tuple[Type[Exception], ...] = (Exception,),
):
    """Decorator for sync functions with exponential backoff retry.

    Args:
        max_attempts: Maximum number of retry attempts
        exponential_base: Base for exponential backoff
        exponential_max: Maximum wait time in seconds
        retry_on: Tuple of exception types to retry on

    Returns:
        Decorated function with retry logic
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=1, max=exponential_max, exp_base=exponential_base),
        retry=retry_if_exception_type(retry_on),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


class RetryableError(Exception):
    """Base exception for retryable errors."""
    pass


class NonRetryableError(Exception):
    """Base exception for non-retryable errors."""
    pass
