"""Shared protocol and base class for TTS backends.

Defines the abstract interface that both EdgeTTS and AzureTTS implement.
"""

from __future__ import annotations

import abc
from collections.abc import AsyncIterator
from pathlib import Path

from pyagentvox.constants import AudioFormat
from pyagentvox.models import SynthesisResult, Voice

__all__ = ['TTSBackend']


class TTSBackend(abc.ABC):
    """Abstract base class for TTS backends.

    Both EdgeTTS and AzureTTS implement this interface, providing a unified
    async API regardless of the underlying service.
    """

    @abc.abstractmethod
    async def synthesize(self, text: str, audio_format: AudioFormat | None = None) -> bytes:
        """Synthesize text to audio bytes.

        Args:
            text: Plain text to synthesize.
            audio_format: Output audio format (default: MP3_24K).

        Returns:
            Raw audio bytes in the requested format.
        """

    @abc.abstractmethod
    async def synthesize_ssml(self, ssml: str, audio_format: AudioFormat | None = None) -> bytes:
        """Synthesize SSML to audio bytes.

        Args:
            ssml: SSML document string.
            audio_format: Output audio format (default: MP3_24K).

        Returns:
            Raw audio bytes in the requested format.
        """

    @abc.abstractmethod
    async def stream(self, text: str, audio_format: AudioFormat | None = None) -> AsyncIterator[bytes]:
        """Stream audio chunks as they arrive.

        Args:
            text: Plain text to synthesize.
            audio_format: Output audio format (default: MP3_24K).

        Yields:
            Audio data chunks as bytes.
        """
        yield b''  # pragma: no cover

    @abc.abstractmethod
    async def stream_ssml(self, ssml: str, audio_format: AudioFormat | None = None) -> AsyncIterator[bytes]:
        """Stream audio from SSML as chunks arrive.

        Args:
            ssml: SSML document string.
            audio_format: Output audio format (default: MP3_24K).

        Yields:
            Audio data chunks as bytes.
        """
        yield b''  # pragma: no cover

    async def synthesize_to_file(
        self,
        text: str,
        path: str | Path,
        audio_format: AudioFormat | None = None,
    ) -> Path:
        """Synthesize text and write to a file.

        Args:
            text: Plain text to synthesize.
            path: Output file path.
            audio_format: Output audio format (inferred from extension if None).

        Returns:
            The Path the audio was written to.
        """
        if audio_format is None:
            audio_format = self._infer_format(path)
        audio_data = await self.synthesize(text, audio_format)
        out_path = Path(path)
        out_path.write_bytes(audio_data)
        return out_path

    async def synthesize_ssml_to_file(
        self,
        ssml: str,
        path: str | Path,
        audio_format: AudioFormat | None = None,
    ) -> Path:
        """Synthesize SSML and write to a file.

        Args:
            ssml: SSML document string.
            path: Output file path.
            audio_format: Output audio format (inferred from extension if None).

        Returns:
            The Path the audio was written to.
        """
        if audio_format is None:
            audio_format = self._infer_format(path)
        audio_data = await self.synthesize_ssml(ssml, audio_format)
        out_path = Path(path)
        out_path.write_bytes(audio_data)
        return out_path

    @staticmethod
    def _infer_format(path: str | Path) -> AudioFormat:
        """Infer audio format from file extension.

        Args:
            path: File path to infer format from.

        Returns:
            Best-matching AudioFormat for the file extension.
        """
        suffix = Path(path).suffix.lower()
        match suffix:
            case '.mp3':
                return AudioFormat.MP3_24K
            case '.wav':
                return AudioFormat.WAV_24K
            case '.ogg' | '.opus':
                return AudioFormat.OGG_24K
            case _:
                return AudioFormat.MP3_24K
