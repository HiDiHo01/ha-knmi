"""KNMI exceptions."""
# exceptions.py

class KNMIError(Exception):
    """Base class for KNMI errors."""

    def __init__(self, message: str) -> None:
        """Initialize the KNMIError."""
        super().__init__(message)
        self.message = message

class ApiError(KNMIError):
    """Raised when a KNMI API request ends in an error."""

class InvalidApiKeyError(KNMIError):
    """Raised when the API Key format is invalid."""

class InvalidCoordinatesError(KNMIError):
    """Raised when the coordinates are invalid."""

class RequestsExceededError(KNMIError):
    """Raised when the allowed number of requests has been exceeded."""


class KnmiApiException(KNMIError):
    """Raised when there is an exception with the KNMI API."""

class KnmiApiClientApiKeyError(KNMIError):
    """Raised when the API Key format is invalid."""

class KnmiApiClientCommunicationError(KNMIError):
    """Raised when there is a Communication error with the Knmi Api Client."""

class KnmiApiRateLimitError(KNMIError):
    """Raised when the allowed number of requests has been exceeded."""