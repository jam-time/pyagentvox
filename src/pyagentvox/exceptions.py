"""Exception hierarchy for pyagentvox.

All exceptions inherit from ExpressiveTTSError for easy broad catching.
"""

__all__ = [
    'AuthenticationError',
    'ConnectionError',
    'ExpressiveTTSError',
    'SSMLError',
    'SynthesisError',
    'VoiceNotFoundError',
]


class ExpressiveTTSError(Exception):
    """Base exception for all pyagentvox errors."""


class SynthesisError(ExpressiveTTSError):
    """Raised when speech synthesis fails."""


class ConnectionError(ExpressiveTTSError):
    """Raised when WebSocket or HTTP connection fails."""


class AuthenticationError(ExpressiveTTSError):
    """Raised when Azure authentication fails."""


class VoiceNotFoundError(ExpressiveTTSError):
    """Raised when the requested voice is not available."""


class SSMLError(ExpressiveTTSError):
    """Raised when SSML construction or validation fails."""
