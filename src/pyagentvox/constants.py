"""Constants and enumerations for pyagentvox.

Defines audio formats, emotion styles, and Edge/Azure endpoint constants.
"""

from enum import Enum

__all__ = [
    'AudioFormat',
    'AZURE_TOKEN_URL',
    'AZURE_TTS_URL',
    'AZURE_VOICES_URL',
    'EDGE_SEC_MS_GEC_VERSION',
    'EDGE_TRUST_TOKEN',
    'EDGE_VOICES_URL',
    'EDGE_WSS_URL',
    'EmotionStyle',
]


class AudioFormat(str, Enum):
    """Supported audio output formats."""

    MP3_24K = 'audio-24khz-48kbitrate-mono-mp3'
    MP3_48K = 'audio-24khz-96kbitrate-mono-mp3'
    MP3_96K = 'audio-48khz-96kbitrate-mono-mp3'
    MP3_192K = 'audio-48khz-192kbitrate-mono-mp3'
    WAV_16K = 'riff-16khz-16bit-mono-pcm'
    WAV_24K = 'riff-24khz-16bit-mono-pcm'
    WAV_48K = 'riff-48khz-16bit-mono-pcm'
    OGG_16K = 'ogg-16khz-16bit-mono-opus'
    OGG_24K = 'ogg-24khz-16bit-mono-opus'
    OGG_48K = 'ogg-48khz-16bit-mono-opus'

    # Azure-specific formats
    RAW_16K = 'raw-16khz-16bit-mono-pcm'
    RAW_24K = 'raw-24khz-16bit-mono-pcm'
    RAW_48K = 'raw-48khz-16bit-mono-pcm'


class EmotionStyle(str, Enum):
    """Express-as emotion styles supported by Azure Neural voices.

    These map directly to Azure's mstts:express-as style values.
    On the free Edge tier, these auto-downgrade to prosody approximations.
    """

    CHEERFUL = 'cheerful'
    SAD = 'sad'
    ANGRY = 'angry'
    EXCITED = 'excited'
    FRIENDLY = 'friendly'
    TERRIFIED = 'terrified'
    SHOUTING = 'shouting'
    UNFRIENDLY = 'unfriendly'
    WHISPERING = 'whispering'
    HOPEFUL = 'hopeful'
    EMPATHETIC = 'empathetic'
    CALM = 'calm'
    DISGRUNTLED = 'disgruntled'
    SERIOUS = 'serious'
    AFFECTIONATE = 'affectionate'
    GENTLE = 'gentle'
    DEPRESSED = 'depressed'
    ENVIOUS = 'envious'
    CHAT = 'chat'
    EMBARRASSED = 'embarrassed'
    FEARFUL = 'fearful'
    LYRICAL = 'lyrical'
    NEWSCAST = 'newscast'
    NEWSCAST_CASUAL = 'newscast-casual'
    NEWSCAST_FORMAL = 'newscast-formal'
    CUSTOMERSERVICE = 'customerservice'
    POETRY_READING = 'poetry-reading'
    NARRATION_PROFESSIONAL = 'narration-professional'
    NARRATION_RELAXED = 'narration-relaxed'
    SPORTS_COMMENTARY = 'sports-commentary'
    SPORTS_COMMENTARY_EXCITED = 'sports-commentary-excited'
    DOCUMENTARY_NARRATION = 'documentary-narration'
    ADVERTISEMENT_UPBEAT = 'advertisement-upbeat'


# Edge WebSocket endpoint constants
EDGE_WSS_URL = (
    'wss://speech.platform.bing.com/consumer/speech/synthesize/readaloud/edge/v1'
    '?TrustedClientToken={token}'
    '&Sec-MS-GEC={sec_ms_gec}'
    '&Sec-MS-GEC-Version={sec_ms_gec_version}'
    '&ConnectionId={connection_id}'
)

EDGE_VOICES_URL = 'https://speech.platform.bing.com/consumer/speech/synthesize/readaloud/voices/list?trustedclienttoken={token}'

# These values are extracted from the Edge browser and may need periodic updates
EDGE_TRUST_TOKEN = '6A5AA1D4EAFF4E9FB37E23D68491D6F4'
EDGE_SEC_MS_GEC_VERSION = '1-130.0.2849.68'

# Azure endpoint templates
AZURE_TTS_URL = 'https://{region}.tts.speech.microsoft.com/cognitiveservices/v1'
AZURE_VOICES_URL = 'https://{region}.tts.speech.microsoft.com/cognitiveservices/voices/list'
AZURE_TOKEN_URL = 'https://{region}.api.cognitive.microsoft.com/sts/v1.0/issueToken'
