"""Edge TTS engine implementation."""

import asyncio
import tempfile
import edge_tts
from pathlib import Path


class EdgeTTSEngine:
    """Edge TTS engine using Microsoft Edge's text-to-speech API."""

    def __init__(self, config: dict):
        """Initialize Edge TTS engine with config."""
        self.config = config

    async def generate_speech(self, text: str, emotion: str | None = None) -> str:
        """Generate speech audio file.

        Args:
            text: Text to convert to speech
            emotion: Emotion tag (neutral, cheerful, etc.)

        Returns:
            Path to generated MP3 file
        """
        # Get voice for emotion
        emotion = emotion or 'neutral'
        voice_config = self.config.get(emotion, self.config.get('neutral', {}))
        voice = voice_config.get('voice', 'en-US-AvaNeural')

        # Create temp file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        output_path = temp_file.name
        temp_file.close()

        # Generate speech
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)

        return output_path

    def is_ready(self) -> bool:
        """Check if engine is ready."""
        return True

    def get_required_models(self) -> list:
        """Get list of required models."""
        return []

    def download_models(self, progress_callback=None):
        """Download required models (Edge TTS needs none)."""
        pass

    def cleanup(self):
        """Cleanup resources."""
        pass
