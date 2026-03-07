"""Data models for pyagentvox.

Defines Voice and SynthesisResult dataclasses used across backends.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ['SynthesisResult', 'Voice']


@dataclass(frozen=True, slots=True)
class Voice:
    """Represents a TTS voice with its capabilities.

    Attributes:
        short_name: Short identifier like 'en-US-AriaNeural'.
        display_name: Human-readable name like 'Aria'.
        locale: Language locale like 'en-US'.
        gender: Voice gender — 'Female' or 'Male'.
        voice_type: Type of voice — 'Neural', 'Standard', etc.
        style_list: List of supported express-as styles (Azure only).
        role_play_list: List of supported role-play personas (Azure only).
        sample_rate_hertz: Native sample rate of the voice.
        words_per_minute: Approximate speaking rate.
    """

    short_name: str
    display_name: str = ''
    locale: str = ''
    gender: str = ''
    voice_type: str = 'Neural'
    style_list: tuple[str, ...] = ()
    role_play_list: tuple[str, ...] = ()
    sample_rate_hertz: int = 24000
    words_per_minute: int = 0

    @property
    def language(self) -> str:
        """Extract the language code from the locale (e.g., 'en' from 'en-US')."""
        return self.locale.split('-')[0] if self.locale else ''

    @property
    def supports_styles(self) -> bool:
        """Whether this voice supports express-as emotion styles."""
        return len(self.style_list) > 0

    def supports_style(self, style: str) -> bool:
        """Check if this voice supports a specific emotion style.

        Args:
            style: The style name to check (e.g., 'cheerful').

        Returns:
            True if the voice supports the given style.
        """
        return style.lower() in (s.lower() for s in self.style_list)

    @classmethod
    def from_edge_dict(cls, data: dict) -> Voice:
        """Create a Voice from the Edge voices list API response.

        Args:
            data: Raw dict from the Edge voices list endpoint.

        Returns:
            A Voice instance populated from the Edge response data.
        """
        return cls(
            short_name=data.get('ShortName', ''),
            display_name=data.get('FriendlyName', ''),
            locale=data.get('Locale', ''),
            gender=data.get('Gender', ''),
            voice_type=data.get('VoiceTag', {}).get('VoicePersonalities', ['Neural'])[0]
            if 'VoiceTag' in data
            else 'Neural',
            sample_rate_hertz=int(data.get('SuggestedCodec', '24khz').replace('khz', '000')[:5])
            if 'SuggestedCodec' in data
            else 24000,
        )

    @classmethod
    def from_azure_dict(cls, data: dict) -> Voice:
        """Create a Voice from the Azure voices list API response.

        Args:
            data: Raw dict from the Azure voices list endpoint.

        Returns:
            A Voice instance populated from the Azure response data.
        """
        style_list = data.get('StyleList', [])
        role_play_list = data.get('RolePlayList', [])
        return cls(
            short_name=data.get('ShortName', ''),
            display_name=data.get('DisplayName', ''),
            locale=data.get('Locale', ''),
            gender=data.get('Gender', ''),
            voice_type=data.get('VoiceType', 'Neural'),
            style_list=tuple(style_list) if style_list else (),
            role_play_list=tuple(role_play_list) if role_play_list else (),
            sample_rate_hertz=int(data.get('SampleRateHertz', 24000)),
            words_per_minute=int(data.get('WordsPerMinute', 0)),
        )


@dataclass(slots=True)
class SynthesisResult:
    """Result of a TTS synthesis operation.

    Attributes:
        audio_data: Raw audio bytes in the requested format.
        audio_format: The format of the audio data.
        duration_ms: Estimated duration in milliseconds (if available).
        voice: The voice used for synthesis.
    """

    audio_data: bytes
    audio_format: str = ''
    duration_ms: float = 0.0
    voice: str = ''
