"""Edge TTS backend -- free Microsoft Edge WebSocket endpoint.

Provides text-to-speech synthesis using the same WebSocket endpoint that
powers the Microsoft Edge browser's Read Aloud feature. No API key required.

Usage:
    tts = EdgeTTS(voice='en-US-AriaNeural')
    audio = await tts.synthesize('Hello world!')

    async for chunk in tts.stream('Long text here...'):
        player.feed(chunk)
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

import aiohttp

from pyagentvox._edge_protocol import (
    build_config_message,
    build_edge_url,
    build_ssml_message,
    is_turn_end,
    parse_audio_chunk,
)
from pyagentvox._protocol import TTSBackend
from pyagentvox.constants import EDGE_TRUST_TOKEN, EDGE_VOICES_URL, AudioFormat
from pyagentvox.exceptions import ConnectionError, SynthesisError
from pyagentvox.models import Voice
from pyagentvox.ssml import SSMLBuilder

__all__ = ['EdgeTTS']

logger = logging.getLogger('pyagentvox')


class EdgeTTS(TTSBackend):
    """Free TTS backend using the Microsoft Edge WebSocket endpoint.

    This backend connects to the same endpoint that powers Edge's Read Aloud
    feature. It supports neural voices and basic SSML but does NOT support
    Azure express-as emotion styles.

    Attributes:
        voice: The voice short name to use for synthesis.
        audio_format: Default audio format for output.
    """

    def __init__(
        self,
        voice: str = 'en-US-AriaNeural',
        audio_format: AudioFormat = AudioFormat.MP3_24K,
    ) -> None:
        """Initialize the Edge TTS backend.

        Args:
            voice: Voice short name (e.g., 'en-US-AriaNeural').
            audio_format: Default output format.
        """
        self.voice = voice
        self.audio_format = audio_format

    async def synthesize(self, text: str, audio_format: AudioFormat | None = None) -> bytes:
        """Synthesize plain text to audio bytes.

        Args:
            text: Text to synthesize.
            audio_format: Output format (uses instance default if None).

        Returns:
            Complete audio data as bytes.

        Raises:
            SynthesisError: If synthesis fails.
            ConnectionError: If the WebSocket connection fails.
        """
        ssml = SSMLBuilder().voice(self.voice).say(text).build_for_edge()
        return await self.synthesize_ssml(ssml, audio_format)

    async def synthesize_ssml(self, ssml: str, audio_format: AudioFormat | None = None) -> bytes:
        """Synthesize SSML to audio bytes.

        Args:
            ssml: SSML document string.
            audio_format: Output format (uses instance default if None).

        Returns:
            Complete audio data as bytes.

        Raises:
            SynthesisError: If synthesis fails.
            ConnectionError: If the WebSocket connection fails.
        """
        fmt = audio_format or self.audio_format
        chunks: list[bytes] = []

        async for chunk in self._stream_ws(ssml, fmt):
            chunks.append(chunk)

        if not chunks:
            raise SynthesisError('No audio data received from Edge endpoint')

        return b''.join(chunks)

    async def stream(self, text: str, audio_format: AudioFormat | None = None) -> AsyncIterator[bytes]:
        """Stream audio chunks as they arrive from synthesis.

        Args:
            text: Text to synthesize.
            audio_format: Output format (uses instance default if None).

        Yields:
            Audio data chunks as bytes.
        """
        ssml = SSMLBuilder().voice(self.voice).say(text).build_for_edge()
        async for chunk in self.stream_ssml(ssml, audio_format):
            yield chunk

    async def stream_ssml(self, ssml: str, audio_format: AudioFormat | None = None) -> AsyncIterator[bytes]:
        """Stream audio from SSML as chunks arrive.

        Args:
            ssml: SSML document string.
            audio_format: Output format (uses instance default if None).

        Yields:
            Audio data chunks as bytes.
        """
        fmt = audio_format or self.audio_format
        async for chunk in self._stream_ws(ssml, fmt):
            yield chunk

    async def _stream_ws(self, ssml: str, audio_format: AudioFormat) -> AsyncIterator[bytes]:
        """Internal WebSocket streaming implementation.

        Connects to the Edge WebSocket, sends config and SSML, then yields
        audio chunks as they arrive.

        Args:
            ssml: SSML document to synthesize.
            audio_format: Output audio format.

        Yields:
            Raw audio data chunks.

        Raises:
            ConnectionError: If the WebSocket connection fails.
            SynthesisError: If the synthesis encounters an error.
        """
        url = build_edge_url()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(
                    url,
                    headers={
                        'Origin': 'chrome-extension://jdiccldimpdaibmpdkjnbmckianbfold',
                        'User-Agent': (
                            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                            'AppleWebKit/537.36 (KHTML, like Gecko) '
                            'Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0'
                        ),
                    },
                    compress=15,
                ) as ws:
                    # Send configuration
                    config_msg = build_config_message(audio_format.value)
                    await ws.send_str(config_msg)

                    # Send SSML
                    ssml_msg = build_ssml_message(ssml)
                    await ws.send_str(ssml_msg)

                    # Receive audio chunks
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.BINARY:
                            audio = parse_audio_chunk(msg.data)
                            if audio:
                                yield audio
                        elif msg.type == aiohttp.WSMsgType.TEXT:
                            if is_turn_end(msg.data):
                                break
                        elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSED):
                            raise SynthesisError(
                                f'WebSocket error during synthesis: {ws.exception()}'
                            )

        except aiohttp.ClientError as e:
            raise ConnectionError(f'Failed to connect to Edge TTS endpoint: {e}') from e

    @staticmethod
    async def list_voices(language: str | None = None, gender: str | None = None) -> list[Voice]:
        """List available voices from the Edge endpoint.

        Args:
            language: Filter by language code (e.g., 'en', 'en-US').
            gender: Filter by gender ('Female' or 'Male').

        Returns:
            List of available Voice objects.

        Raises:
            ConnectionError: If the voices endpoint is unreachable.
        """
        url = EDGE_VOICES_URL.format(token=EDGE_TRUST_TOKEN)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        raise ConnectionError(
                            f'Edge voices endpoint returned status {resp.status}'
                        )
                    data = await resp.json()
        except aiohttp.ClientError as e:
            raise ConnectionError(f'Failed to fetch Edge voices: {e}') from e

        voices = [Voice.from_edge_dict(v) for v in data]

        if language:
            lang_lower = language.lower()
            voices = [
                v for v in voices
                if v.locale.lower().startswith(lang_lower)
            ]

        if gender:
            gender_lower = gender.lower()
            voices = [v for v in voices if v.gender.lower() == gender_lower]

        return sorted(voices, key=lambda v: v.short_name)
