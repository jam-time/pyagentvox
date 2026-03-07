# pyagentvox

Expressive text-to-speech with free Edge WebSocket and paid Azure backends.

## Features

- **Two backends**: Free Edge TTS (no API key) and full Azure Speech Services
- **Fluent SSML builder**: Chainable API with emotion, prosody, breaks, phonemes
- **30+ emotion styles**: cheerful, sad, excited, whispering, and more via Azure express-as
- **Streaming**: Yield audio chunks as they arrive
- **Voice discovery**: List and filter available voices by language and gender
- **Multiple formats**: MP3, WAV, OGG/Opus at various bitrates

## Quick Start

```python
from pyagentvox import EdgeTTS, SSMLBuilder

# Simple synthesis (free, no API key)
tts = EdgeTTS(voice='en-US-AriaNeural')
audio = await tts.synthesize('Hello world!')

# Streaming
async for chunk in tts.stream('Long text here...'):
    player.feed(chunk)

# SSML with emotions (Azure backend)
from pyagentvox import AzureTTS

tts = AzureTTS(key='your-key', region='eastus')
ssml = (
    SSMLBuilder()
    .voice('en-US-AriaNeural')
    .emotion('cheerful')
    .say('Great to see you!')
    .pause(500)
    .emotion('calm')
    .say('How are you today?')
    .build()
)
audio = await tts.synthesize_ssml(ssml)
```

## Installation

```bash
pip install pyagentvox
```

## License

MIT
