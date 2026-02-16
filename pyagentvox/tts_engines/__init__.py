"""TTS engine factory."""

from .edge import EdgeTTSEngine


def create_engine(engine_type: str, config: dict):
    """Create TTS engine instance."""
    if engine_type == 'edge':
        return EdgeTTSEngine(config)
    else:
        raise ValueError(f'Unknown TTS engine: {engine_type}')
