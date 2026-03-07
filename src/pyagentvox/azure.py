"""Azure TTS backend -- full Azure Speech Services with express-as support.

Provides text-to-speech synthesis using Azure Cognitive Services. Requires
an API key and region. Supports the full range of SSML features including
express-as emotion styles.

Usage:
    tts = AzureTTS(key='your-key', region='eastus', voice='en-US-AriaNeural')
    audio = await tts.synthesize('Hello world!')
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator

import httpx

from pyagentvox._protocol import TTSBackend
from pyagentvox.constants import (
    AZURE_TOKEN_URL,
    AZURE_TTS_URL,
    AZURE_VOICES_URL,
    AudioFormat,
)
from pyagentvox.exceptions import AuthenticationError, ConnectionError, SynthesisError
from pyagentvox.models import Voice
from pyagentvox.ssml import SSMLBuilder

__all__ = ['AzureTTS']

logger = logging.getLogger('pyagentvox')

# Azure tokens are valid for 10 minutes; refresh at 9 to be safe
_TOKEN_REFRESH_SECONDS = 540


class AzureTTS(TTSBackend):
    """Azure Speech Services TTS backend.

    Full-featured backend supporting express-as emotion styles, all SSML
    features, and the complete Azure neural voice catalog.

    Attributes:
        voice: The voice short name to use for synthesis.
        audio_format: Default audio format for output.
        region: Azure region (e.g., 'eastus').
    """

    def __init__(
        self,
        key: str,
        region: str = 'eastus',
        voice: str = 'en-US-AriaNeural',
        audio_format: AudioFormat = AudioFormat.MP3_24K,
    ) -> None:
        """Initialize the Azure TTS backend.

        Args:
            key: Azure Speech Services subscription key.
            region: Azure region (e.g., 'eastus', 'westus2').
            voice: Voice short name (e.g., 'en-US-AriaNeural').
            audio_format: Default output format.
        """
        self._key = key
        self.region = region
        self.voice = voice
        self.audio_format = audio_format
        self._token: str | None = None
        self._token_expiry: float = 0.0

    async def _get_token(self) -> str:
        """Get a valid Azure access token, refreshing if needed.

        Returns:
            Valid access token string.

        Raises:
            AuthenticationError: If token acquisition fails.
        """
        if self._token and time.time() < self._token_expiry:
            return self._token

        url = AZURE_TOKEN_URL.format(region=self.region)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    headers={'Ocp-Apim-Subscription-Key': self._key},
                    content='',
                )
                if resp.status_code != 200:
                    raise AuthenticationError(
                        f'Azure token endpoint returned status {resp.status_code}: {resp.text}'
                    )
                self._token = resp.text
                self._token_expiry = time.time() + _TOKEN_REFRESH_SECONDS
                return self._token
        except httpx.HTTPError as e:
            raise AuthenticationError(f'Failed to acquire Azure token: {e}') from e

    async def synthesize(self, text: str, audio_format: AudioFormat | None = None) -> bytes:
        """Synthesize plain text to audio bytes.

        Args:
            text: Text to synthesize.
            audio_format: Output format (uses instance default if None).

        Returns:
            Complete audio data as bytes.

        Raises:
            SynthesisError: If synthesis fails.
            AuthenticationError: If authentication fails.
        """
        ssml = SSMLBuilder().voice(self.voice).say(text).build()
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
            AuthenticationError: If authentication fails.
        """
        fmt = audio_format or self.audio_format
        token = await self._get_token()
        url = AZURE_TTS_URL.format(region=self.region)

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    headers={
                        'Authorization': f'Bearer {token}',
                        'Content-Type': 'application/ssml+xml',
                        'X-Microsoft-OutputFormat': fmt.value,
                        'User-Agent': 'pyagentvox/0.1.0',
                    },
                    content=ssml,
                    timeout=30.0,
                )
                if resp.status_code == 401:
                    # Token may have expired; clear and retry once
                    self._token = None
                    token = await self._get_token()
                    resp = await client.post(
                        url,
                        headers={
                            'Authorization': f'Bearer {token}',
                            'Content-Type': 'application/ssml+xml',
                            'X-Microsoft-OutputFormat': fmt.value,
                            'User-Agent': 'pyagentvox/0.1.0',
                        },
                        content=ssml,
                        timeout=30.0,
                    )

                if resp.status_code != 200:
                    raise SynthesisError(
                        f'Azure TTS returned status {resp.status_code}: {resp.text}'
                    )

                return resp.content

        except httpx.HTTPError as e:
            raise SynthesisError(f'Azure TTS request failed: {e}') from e

    async def stream(self, text: str, audio_format: AudioFormat | None = None) -> AsyncIterator[bytes]:
        """Stream audio chunks as they arrive from synthesis.

        Args:
            text: Text to synthesize.
            audio_format: Output format (uses instance default if None).

        Yields:
            Audio data chunks as bytes.
        """
        ssml = SSMLBuilder().voice(self.voice).say(text).build()
        async for chunk in self.stream_ssml(ssml, audio_format):
            yield chunk

    async def stream_ssml(self, ssml: str, audio_format: AudioFormat | None = None) -> AsyncIterator[bytes]:
        """Stream audio from SSML using chunked transfer.

        Args:
            ssml: SSML document string.
            audio_format: Output format (uses instance default if None).

        Yields:
            Audio data chunks as bytes.

        Raises:
            SynthesisError: If synthesis fails.
            AuthenticationError: If authentication fails.
        """
        fmt = audio_format or self.audio_format
        token = await self._get_token()
        url = AZURE_TTS_URL.format(region=self.region)

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    'POST',
                    url,
                    headers={
                        'Authorization': f'Bearer {token}',
                        'Content-Type': 'application/ssml+xml',
                        'X-Microsoft-OutputFormat': fmt.value,
                        'User-Agent': 'pyagentvox/0.1.0',
                    },
                    content=ssml,
                    timeout=30.0,
                ) as resp:
                    if resp.status_code != 200:
                        body = await resp.aread()
                        raise SynthesisError(
                            f'Azure TTS stream returned status {resp.status_code}: {body.decode()}'
                        )

                    async for chunk in resp.aiter_bytes(chunk_size=4096):
                        yield chunk

        except httpx.HTTPError as e:
            raise SynthesisError(f'Azure TTS stream failed: {e}') from e

    async def list_voices(
        self,
        language: str | None = None,
        gender: str | None = None,
    ) -> list[Voice]:
        """List available voices from Azure Speech Services.

        Args:
            language: Filter by language code (e.g., 'en', 'en-US').
            gender: Filter by gender ('Female' or 'Male').

        Returns:
            List of available Voice objects with full capability info.

        Raises:
            AuthenticationError: If authentication fails.
            ConnectionError: If the endpoint is unreachable.
        """
        token = await self._get_token()
        url = AZURE_VOICES_URL.format(region=self.region)

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    url,
                    headers={'Authorization': f'Bearer {token}'},
                    timeout=15.0,
                )
                if resp.status_code != 200:
                    raise ConnectionError(
                        f'Azure voices endpoint returned status {resp.status_code}'
                    )
                data = resp.json()
        except httpx.HTTPError as e:
            raise ConnectionError(f'Failed to fetch Azure voices: {e}') from e

        voices = [Voice.from_azure_dict(v) for v in data]

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
