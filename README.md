# PyAgentVox

Two-way voice communication system for AI agents with speech-to-text input and text-to-speech output.

![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Abstract

Stop typing everything to your AI. PyAgentVox turns Claude Code into a voice-first interface where you speak naturally and Claude responds with emotion-aware speech. The AI can switch between cheerful, calm, or empathetic voices mid-response based on context. Change voice profiles on the fly without restarting. Run multiple Claude Code windows simultaneously, each with its own voice personality. Everything works in the background - keep coding while your voice input types automatically, no window stealing.

Built for developers who want natural conversations with AI without breaking flow. Windows-only, Python 3.12+, works with Claude Code out of the box.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [How It Works](#how-it-works)
- [Runtime Controls](#runtime-controls)
- [Multi-Instance Support](#multi-instance-support)
- [Configuration](#configuration)
- [CLI Examples](#cli-examples)
- [Requirements](#requirements)

## Features

### Core Functionality
- Speech-to-text (STT) input using Google Speech API
- Text-to-speech (TTS) output using Microsoft Edge TTS
- Emotion-based voice switching with inline tags
- Background keyboard automation without window focus changes
- Per-window instance locking for multi-window support

### Runtime Controls
- Toggle TTS/STT states without restarting
- Switch voice profiles during runtime
- Modify voice parameters (pitch, speed) per emotion
- CLI subcommands: `start`, `stop`, `switch`, `tts`, `stt`, `modify`, `status`

### Configuration
- JSON/YAML configuration files with profile support
- Voice profile definitions with per-emotion settings
- CLI overrides for temporary modifications
- Automatic instruction injection into Claude Code

### Platform Support
- Windows-only (requires pywin32 for PostMessage API)
- Python 3.12+ required
- Internet connection required for TTS and STT services

## 📦 Installation

### From GitHub

```bash
# Clone the repository
git clone https://github.com/jmeador/pyagentvox.git
cd pyagentvox

# Install with uv (recommended)
uv pip install -e .

# OR install with pip
pip install -e .
```

### Requirements

- **Python 3.12+**
- **Windows** (voice injector uses keyboard automation)
- **Microphone** for speech input
- **Internet connection** for TTS and speech recognition

If PyAudio installation fails on Windows:
```bash
# Option 1: Use pipwin
pip install pipwin
pipwin install pyaudio

# Option 2: Download wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/
```

## 🚀 Quick Start

```bash
# 1. Start PyAgentVox with default voice
python -m pyagentvox start --debug

# 2. Try different voice profiles
python -m pyagentvox start --profile michelle
python -m pyagentvox start --profile jenny

# 3. Integrate with Claude Code (from your project directory)
# Using skills (after Claude Code restart):
/voice                    # Start with default profile
/voice michelle           # Start with specific profile
/voice-switch jenny       # Switch profiles during runtime
/tts-control off          # Disable TTS output
/stt-control off          # Disable voice input
/voice-modify pitch=+5    # Adjust pitch

# 4. Direct CLI controls (while running)
python -m pyagentvox switch jenny    # Switch voice profile
python -m pyagentvox tts off         # Disable TTS output
python -m pyagentvox stt on          # Enable voice input
python -m pyagentvox modify pitch=+5 # Modify voice settings
python -m pyagentvox status          # Check if running
python -m pyagentvox stop            # Stop PyAgentVox
```

## 📖 Documentation

### 📚 Main Documentation

| Document | Description |
|----------|-------------|
| **[SETUP.md](SETUP.md)** | Complete setup guide with installation, architecture overview, and configuration |
| **[USAGE.md](USAGE.md)** | CLI reference, runtime controls, configuration files, and advanced features |
| **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** | One-page cheat sheet for common commands and skills |
| **[AGENTS.md](AGENTS.md)** | Guide for AI assistants to implement voice communication in one session |

### 🛠️ Development Documentation

| Document | Description |
|----------|-------------|
| **[CONTRIBUTING.md](CONTRIBUTING.md)** | Contribution guidelines and development workflow |
| **[CHANGELOG.md](CHANGELOG.md)** | Version history and release notes |

### 🔗 Quick Links

- [Configuration Guide](USAGE.md#configuration) - Config files, profiles, CLI overrides
- [Available Voices](USAGE.md#available-voices) - All voices with descriptions
- [Emotion Tags](USAGE.md#emotion-tags) - How to use `[cheerful]`, `[calm]`, etc.
- [Troubleshooting](SETUP.md#troubleshooting) - Common issues and solutions
- [Architecture Diagram](SETUP.md#architecture-overview) - How components work together

## How It Works

PyAgentVox integrates with Claude Code through four coordinated components:

1. **PyAgentVox Main** - Listens to microphone, speaks responses with emotion-based voices
2. **TTS Monitor** - Watches Claude Code conversation files, sends responses to PyAgentVox
3. **Voice Injector** - Types recognized speech into Claude Code window (background typing, no focus stealing)
4. **Instructions Manager** - Auto-injects voice tag documentation into CLAUDE.md

Per-window locking allows multiple Claude Code windows to run independent PyAgentVox instances simultaneously. Runtime controls enable TTS/STT toggling, profile switching, and voice modifications without restarting.

See [SETUP.md](SETUP.md#architecture-overview) for detailed architecture diagrams.

## Emotion Tags

AI agents can insert emotion tags to change voice characteristics mid-response:

```
[neutral] Default voice settings.
[cheerful] Higher pitch, faster speed.
[excited] Highest energy level.
[calm] Lower pitch, moderate speed.
[warm] Softer tone.
```

Text is split at emotion tag boundaries. Each segment uses the corresponding emotion's voice settings (pitch, speed, voice actor). Tags are removed during speech generation.

## Runtime Controls

Modify PyAgentVox behavior without restarting:

### Voice Profile Switching

```bash
python -m pyagentvox switch jenny
python -m pyagentvox switch male_voices

# From Claude Code:
/voice-switch jenny
```

Changes take effect after current TTS completes. Profile configuration is reloaded from config file.

### TTS/STT Toggle

```bash
python -m pyagentvox tts off  # Disable text-to-speech
python -m pyagentvox stt off  # Disable speech-to-text

# From Claude Code:
/tts-control off
/stt-control off
```

State changes apply immediately. TTS queue processing continues but audio playback is skipped.

### Voice Settings

```bash
# Global modifications
python -m pyagentvox modify pitch=+5
python -m pyagentvox modify speed=-10

# Per-emotion modifications
python -m pyagentvox modify neutral.pitch=+10
python -m pyagentvox modify cheerful.speed=-5

# From Claude Code:
/voice-modify pitch=+5
/voice-modify neutral.pitch=+10
```

Modifications apply to active voice profile. Values are relative adjustments to existing settings.

## Multi-Instance Support

Per-window locking enables multiple simultaneous PyAgentVox instances:

```bash
# Window 1
cd C:\projects\project1
python -m pyagentvox start --profile michelle

# Window 2
cd C:\projects\project2
python -m pyagentvox start --profile guy_voices
```

Each instance uses a unique PID file based on the conversation file path MD5 hash. Instances operate independently without conflicts. Voice input targets the window that initiated the PyAgentVox process.

## Configuration

### Quick Config (YAML)

```yaml
# Emotion voices (no nesting!)
neutral:
  voice: "en-US-MichelleNeural"
  speed: "+10%"
  pitch: "+10Hz"

cheerful:
  voice: "en-US-JennyNeural"
  speed: "+15%"
  pitch: "+8Hz"

# Optional: Define profiles
profiles:
  male_voices:
    neutral:
      voice: "en-US-GuyNeural"
```

### Quick Config (JSON)

```json
{
  "neutral": {
    "voice": "en-US-MichelleNeural",
    "speed": "+10%",
    "pitch": "+10Hz"
  },
  "cheerful": {
    "voice": "en-US-JennyNeural",
    "speed": "+15%",
    "pitch": "+8Hz"
  }
}
```

## 🎤 Available Voices

### Female Voices
- `en-US-MichelleNeural` - Balanced, default
- `en-US-JennyNeural` - Energetic, upbeat
- `en-US-EmmaNeural` - Warm, caring
- `en-GB-SoniaNeural` - British, calm

### Male Voices
- `en-US-GuyNeural` - Casual, conversational
- `en-US-JasonNeural` - Energetic, enthusiastic
- `en-US-DavisNeural` - Professional, authoritative
- `en-GB-RyanNeural` - British, professional

[See all voices in USAGE.md](USAGE.md#available-voices)

## 🛠️ CLI Examples

### Starting PyAgentVox

```bash
# Start with default voice
python -m pyagentvox start

# Start with specific profile
python -m pyagentvox start --profile michelle

# Start with custom config
python -m pyagentvox start --config my_config.yaml

# Start with overrides
python -m pyagentvox start --set warm.pitch=+20Hz

# Save overrides to config
python -m pyagentvox start --set warm.pitch=+20Hz --save

# TTS-only mode (no voice input)
python -m pyagentvox start --tts-only

# Debug mode with log file
python -m pyagentvox start --debug --log-file pyagentvox.log
```

### Runtime Controls

```bash
# Check if PyAgentVox is running
python -m pyagentvox status

# Switch voice profile without restarting
python -m pyagentvox switch jenny
python -m pyagentvox switch male_voices

# Toggle TTS output on/off
python -m pyagentvox tts off    # Mute TTS (silent mode)
python -m pyagentvox tts on     # Unmute TTS

# Toggle STT (voice input) on/off
python -m pyagentvox stt off    # Disable voice input
python -m pyagentvox stt on     # Enable voice input

# Modify voice settings at runtime
python -m pyagentvox modify pitch=+5        # Global pitch adjustment
python -m pyagentvox modify speed=-10       # Global speed adjustment
python -m pyagentvox modify neutral.pitch=+10   # Emotion-specific
python -m pyagentvox modify all.speed=-15   # All emotions explicitly

# Stop PyAgentVox
python -m pyagentvox stop
```

### Using Skills in Claude Code

```bash
# Start PyAgentVox
/voice                      # Default profile
/voice michelle             # Specific profile
/voice tts-only            # TTS-only mode

# Runtime controls
/voice-switch jenny         # Switch profile
/tts-control off           # Mute TTS
/stt-control off           # Disable voice input
/voice-modify pitch=+5     # Adjust voice

# Stop PyAgentVox
/voice-stop
```

## 📋 Requirements

- **Python:** 3.12 or higher
- **OS:** Windows (voice injector uses win32gui for keyboard automation)
- **Internet:** Required for Edge TTS and Google Speech API
- **Microphone:** For speech input

See [SETUP.md](SETUP.md#prerequisites) for detailed dependency information.

## 🤝 Contributing

Contributions welcome! Please read the contributing guidelines first.

## 📄 License

MIT License - see LICENSE file for details

## 🔗 Links

### For Users & Developers
- [Full Documentation](USAGE.md)
- [Configuration Guide](USAGE.md#configuration)
- [Voice Reference](USAGE.md#available-voices)
- [Troubleshooting](USAGE.md#troubleshooting)

### Project
- [Changelog](CHANGELOG.md) - Version history
- [License](LICENSE) - MIT License
