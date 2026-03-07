"""Expressive text-to-speech with free Edge WebSocket and paid Azure backends.

Provides a unified async API for TTS synthesis across two backends:
- EdgeTTS: Free Microsoft Edge WebSocket endpoint (no API key needed)
- AzureTTS: Full Azure Speech Services with express-as emotion styles

Features:
- Fluent SSML builder with emotion, prosody, breaks, and phonemes
- Streaming audio output (yield chunks as they arrive)
- Voice discovery with language/gender filtering
- Multiple output formats (MP3, WAV, OGG)

Usage:
    from pyagentvox import EdgeTTS, AzureTTS, SSMLBuilder

    tts = EdgeTTS(voice='en-US-AriaNeural')
    audio = await tts.synthesize('Hello world!')
"""

from pyagentvox.azure import AzureTTS
from pyagentvox.constants import AudioFormat, EmotionStyle
from pyagentvox.edge import EdgeTTS
from pyagentvox.exceptions import (
    AuthenticationError,
    ConnectionError,
    ExpressiveTTSError,
    SSMLError,
    SynthesisError,
    VoiceNotFoundError,
)
from pyagentvox.models import SynthesisResult, Voice
from pyagentvox.ssml import SSMLBuilder

__all__ = [
    'AudioFormat',
    'AuthenticationError',
    'AzureTTS',
    'ConnectionError',
    'EdgeTTS',
    'EmotionStyle',
    'ExpressiveTTSError',
    'SSMLBuilder',
    'SSMLError',
    'SynthesisError',
    'SynthesisResult',
    'Voice',
    'VoiceNotFoundError',
]

__version__ = '0.1.0'
