from __future__ import annotations


class ProviderError(Exception):
    """Base class for provider errors."""

    status = "failed"
    error_type = "provider_error"
    retriable = False


class ProviderTimeoutError(ProviderError):
    status = "unknown"
    error_type = "timeout"
    retriable = True


class ProviderRateLimitError(ProviderError):
    status = "failed"
    error_type = "rate_limit"
    retriable = True


class ProviderAuthenticationError(ProviderError):
    status = "failed"
    error_type = "authentication"
    retriable = False


class ProviderUnavailableError(ProviderError):
    status = "failed"
    error_type = "unavailable"
    retriable = True


class ProviderNetworkError(ProviderError):
    status = "failed"
    error_type = "network"
    retriable = True


class ProviderHTTPError(ProviderError):
    status = "failed"
    error_type = "http"

    def __init__(self, status_code: int, message: str = ""):
        self.status_code = status_code
        super().__init__(message)
        if status_code in (401, 403):
            self.error_type = "authentication"
            self.retriable = False
        elif status_code == 429:
            self.error_type = "rate_limit"
            self.retriable = True
        elif status_code == 408:
            self.error_type = "timeout"
            self.retriable = True
        elif status_code in (500, 502, 503, 504):
            self.error_type = "unavailable"
            self.retriable = True
        else:
            self.error_type = "http"
            self.retriable = False


class ContextError(Exception):
    pass


class DatabaseError(Exception):
    pass


class TelegramError(Exception):
    pass
