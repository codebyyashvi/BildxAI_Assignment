class AdGenException(Exception):
    """Base exception for Ad Generator application."""
    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class TemporaryError(AdGenException):
    """Transient failures that should be retried (network timeouts, 5xx rate limits, temporary glitches)."""
    def __init__(self, message: str, status_code: int = 503, details: dict = None):
        super().__init__(message, status_code=status_code, details=details)


class PermanentError(AdGenException):
    """Permanent errors that should NOT be retried (validation failure, SSRF, non-image response, invalid data)."""
    def __init__(self, message: str, status_code: int = 400, details: dict = None):
        super().__init__(message, status_code=status_code, details=details)


class CapacityExceededError(AdGenException):
    """Thrown when system queue depth or concurrent capacity is exceeded."""
    def __init__(self, message: str = "System is currently at maximum capacity. Please retry shortly.", details: dict = None):
        super().__init__(message, status_code=429, details=details)


class GenerationNotFoundError(AdGenException):
    """Thrown when generation ID is not found."""
    def __init__(self, generation_id: str):
        super().__init__(f"Generation '{generation_id}' not found.", status_code=404)
