"""Custom exceptions."""


class SyncServiceException(Exception):
    """Base exception for sync service."""

    pass


class WebhookValidationError(SyncServiceException):
    """Webhook validation failed."""

    pass


class GitHubAPIError(SyncServiceException):
    """GitHub API error."""

    pass


class OneDevAPIError(SyncServiceException):
    """OneDev API error."""

    pass


class GitOperationError(SyncServiceException):
    """Git operation error."""

    pass


class DatabaseError(SyncServiceException):
    """Database operation error."""

    pass

class RetryableError(SyncServiceException):
    """Retryable error - operation can be retried."""

    pass
