"""Edge WebSocket protocol implementation.

Handles the binary WebSocket protocol used by the Microsoft Edge TTS endpoint.
This is the low-level protocol handler — message framing, header parsing, and
audio chunk extraction.
"""

from __future__ import annotations

import hashlib
import logging
import struct
import time
import uuid

from pyagentvox.constants import EDGE_SEC_MS_GEC_VERSION, EDGE_TRUST_TOKEN, EDGE_WSS_URL

__all__ = ['build_config_message', 'build_edge_url', 'build_ssml_message', 'is_turn_end', 'parse_audio_chunk']

logger = logging.getLogger('pyagentvox')


def _generate_sec_ms_gec() -> str:
    """Generate the Sec-MS-GEC token for Edge authentication.

    This is a time-based hash that Edge uses for request validation.
    The algorithm rounds the current time to 5-minute intervals and
    hashes it with a static key.

    Returns:
        Hex-encoded SHA-256 hash string.
    """
    # Round to 5-minute intervals (300 seconds)
    ticks_per_second = 10_000_000
    epoch_ticks = 621_355_968_000_000_000
    now_ticks = int(time.time() * ticks_per_second) + epoch_ticks
    rounded = now_ticks - (now_ticks % (300 * ticks_per_second))

    payload = f'{rounded}{EDGE_TRUST_TOKEN}'
    return hashlib.sha256(payload.encode('utf-8')).hexdigest().upper()


def generate_connection_id() -> str:
    """Generate a unique connection ID for the WebSocket.

    Returns:
        UUID4 hex string without dashes.
    """
    return uuid.uuid4().hex


def build_edge_url() -> str:
    """Build the full Edge WebSocket URL with authentication tokens.

    Returns:
        Complete WebSocket URL ready for connection.
    """
    return EDGE_WSS_URL.format(
        token=EDGE_TRUST_TOKEN,
        sec_ms_gec=_generate_sec_ms_gec(),
        sec_ms_gec_version=EDGE_SEC_MS_GEC_VERSION,
        connection_id=generate_connection_id(),
    )


def build_config_message(audio_format: str) -> str:
    """Build the initial configuration message for the Edge WebSocket.

    This message must be sent immediately after connection to configure
    the audio output format.

    Args:
        audio_format: Audio format string (from AudioFormat enum).

    Returns:
        Formatted config message string.
    """
    return (
        'Content-Type:application/json; charset=utf-8\r\n'
        'Path:speech.config\r\n\r\n'
        '{"context":{"synthesis":{"audio":{"metadataoptions":{'
        '"sentenceBoundaryEnabled":"false","wordBoundaryEnabled":"true"},'
        f'"outputFormat":"{audio_format}"}}}}}}'
    )


def build_ssml_message(ssml: str, request_id: str | None = None) -> str:
    """Build the SSML synthesis request message.

    Args:
        ssml: Complete SSML document string.
        request_id: Optional request ID (generated if not provided).

    Returns:
        Formatted SSML request message string.
    """
    if request_id is None:
        request_id = uuid.uuid4().hex
    return (
        f'X-RequestId:{request_id}\r\n'
        'Content-Type:application/ssml+xml\r\n'
        'Path:ssml\r\n\r\n'
        f'{ssml}'
    )


def parse_audio_chunk(data: bytes) -> bytes | None:
    """Extract audio data from an Edge WebSocket binary message.

    The binary protocol uses a 2-byte header length prefix followed by
    the text header, then the raw audio data.

    Args:
        data: Raw binary WebSocket message.

    Returns:
        Audio bytes if this is an audio message, None otherwise.
    """
    if len(data) < 2:
        return None

    # First 2 bytes are the header length (big-endian unsigned short)
    header_len = struct.unpack('>H', data[:2])[0]

    if len(data) <= 2 + header_len:
        return None

    # The header is ASCII text after the 2-byte length
    header = data[2:2 + header_len].decode('utf-8', errors='replace')

    # Only extract audio from 'audio' path messages
    if 'Path:audio' not in header:
        return None

    # Audio data follows the header
    return data[2 + header_len:]


def is_turn_end(message: str) -> bool:
    """Check if a text WebSocket message signals the end of synthesis.

    Args:
        message: Text message from the WebSocket.

    Returns:
        True if this message indicates synthesis is complete.
    """
    return 'Path:turn.end' in message
