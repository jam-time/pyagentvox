# PyAgentVox

**Two-way voice communication for AI agents** - Speak to your AI and hear it respond!

![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## ✨ Features

- 🎤 **Voice Input** - Speak naturally and your words are sent to the AI
- 🔊 **Voice Output** - AI responses are spoken aloud with natural voices
- 🎭 **Emotion Support** - Different voices for different emotions (cheerful, calm, empathetic, etc.)
- 🌍 **Multiple Voices** - Male and female voices in US and British English
- ⚙️ **Highly Configurable** - JSON/YAML config with profiles and CLI overrides
- 🔌 **Programmatic API** - Use as a library or CLI tool
- 📦 **Easy Installation** - Install as Python package
- 🎯 **Auto-Injection** - Automatically injects voice instructions into instruction files
- 🛑 **Voice Commands** - Say "stop listening" to stop PyAgentVox
- ⏸️ **Auto-Pause STT** - Speech recognition auto-pauses after 10 min idle, resumes on TTS
- 🪟 **Background Typing** - Voice input works without stealing focus from your current window
- 🔧 **Windows Support** - Voice injector using Windows messaging API

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

**Note:** PyAudio can be tricky to install on Windows. If you encounter issues:
```bash
# Try pipwin
pip install pipwin
pipwin install pyaudio

# OR download wheel from:
# https://www.lfd.uci.edu/~gohlke/pythonlibs/
```

## 🚀 Quick Start

```bash
# 1. Test standalone (speak and hear responses)
python -m pyagentvox --debug

# 2. Try different voice profiles
python -m pyagentvox --profile michelle
python -m pyagentvox --profile jenny

# 3. Integrate with Claude Code (from your project directory)
# Using skills (after Claude Code restart):
/voice michelle

# OR directly:
python -m pyagentvox --profile michelle
```

## 📖 Documentation

**For Users:**
- **[SETUP.md](SETUP.md)** - Complete setup guide with architecture overview
- **[USAGE.md](USAGE.md)** - CLI options, configuration, and advanced features
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Cheat sheet for common commands

**For AI Agents:**
- **[AGENTS.md](AGENTS.md)** - Guide for AI assistants to set up voice communication for their humans

**Quick Links:**
- [Configuration Guide](USAGE.md#configuration) - Config files, profiles, CLI overrides
- [Available Voices](USAGE.md#available-voices) - All voices with descriptions
- [Emotion Tags](USAGE.md#emotion-tags) - How to use `[cheerful]`, `[calm]`, etc.
- [Troubleshooting](SETUP.md#troubleshooting) - Common issues and solutions
- [Architecture Diagram](SETUP.md#architecture-overview) - How components work together

## 🏗️ How It Works

PyAgentVox integrates with Claude Code through four coordinated components:

1. **PyAgentVox Main** - Listens to microphone, speaks responses with emotion-based voices
2. **TTS Monitor** - Watches Claude Code conversation files, sends responses to PyAgentVox
3. **Voice Injector** - Types recognized speech into Claude Code window
4. **Instructions Manager** - Auto-injects voice tag documentation into CLAUDE.md

See [SETUP.md](SETUP.md#architecture-overview) for detailed architecture diagrams.

## 🎭 Emotion Tags

Claude can use emotion tags to dynamically change voice:

```
[neutral] This is the default voice.
[cheerful] This sounds happy and upbeat!
[excited] This is very enthusiastic!
[calm] This is professional and relaxed.
[warm] This is gentle and kind.
```

**How it works:** Text is split into segments at emotion tags. Each segment uses that emotion's voice settings (pitch, speed, voice actor). Tags are removed before speaking.

## ⚙️ Configuration

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

```bash
# Use a specific config file
pyagentvox --config my_config.yaml

# Load a profile
pyagentvox --profile male_voices

# Override specific values
pyagentvox --set warm.pitch=+20Hz

# Save overrides to config
pyagentvox --set warm.pitch=+20Hz --save

# Debug mode
pyagentvox --debug
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
