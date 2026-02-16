# PyAgentVox

**Two-way voice communication for AI agents** - Speak to your AI and hear it respond!

![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## ✨ Features

### 🚀 The Wow Factor
- 🎚️ **Runtime Controls** - Toggle TTS/STT, switch profiles, modify voices **without restarting**
- 🖥️ **Multi-Instance Support** - Run multiple Claude Code windows with **independent voice profiles**
- 🪟 **Background Typing** - Voice input works **without stealing focus** from your current window
- 📡 **CLI Subcommands** - Clean command interface: `start`, `stop`, `switch`, `tts`, `stt`, `modify`, `status`

### 🎭 Voice & Emotion
- 🎤 **Voice Input** - Speak naturally and your words are sent to the AI
- 🔊 **Voice Output** - AI responses are spoken aloud with natural voices
- 🎭 **Emotion Support** - Different voices for different emotions (cheerful, calm, empathetic, etc.)
- 🌍 **Multiple Voices** - Male and female voices in US and British English

### ⚙️ Configuration & Control
- ⚙️ **Highly Configurable** - JSON/YAML config with profiles and CLI overrides
- 🎯 **Auto-Injection** - Automatically injects voice instructions into instruction files
- 🛑 **Voice Commands** - Say "stop listening" to stop PyAgentVox
- ⏸️ **Auto-Pause STT** - Speech recognition auto-pauses after 10 min idle, resumes on TTS

### 🔧 Platform & Integration
- 🔧 **Windows Support** - Voice injector using Windows messaging API (PostMessage, no focus stealing)
- 🔌 **Programmatic API** - Use as a library or CLI tool
- 📦 **Easy Installation** - Install as Python package

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
# 1. Start PyAgentVox with default voice
python -m pyagentvox start --debug

# 2. Try different voice profiles
python -m pyagentvox start --profile michelle
python -m pyagentvox start --profile jenny

# 3. Integrate with Claude Code (from your project directory)
# Using skills (after Claude Code restart):
/voice                    # Start with default profile
/voice michelle           # Start with specific profile
/voice-switch jenny       # Switch profiles at runtime
/tts-control off          # Mute TTS output
/stt-control off          # Disable voice input
/voice-modify pitch=+5    # Adjust pitch on the fly

# 4. Direct CLI controls (while running)
python -m pyagentvox switch jenny    # Hot-swap voice profile
python -m pyagentvox tts off         # Mute TTS output
python -m pyagentvox stt on          # Enable voice input
python -m pyagentvox modify pitch=+5 # Tweak voice settings
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
| **[.claude/docs/style-guide.md](.claude/docs/style-guide.md)** | Code style standards (PEP 8, quotes, naming, docstrings) |
| **[.claude/docs/patterns.md](.claude/docs/patterns.md)** | Common patterns (async, error handling, resource management) |
| **[.claude/docs/testing.md](.claude/docs/testing.md)** | Testing standards, mocking, and assertions |

### 🔗 Quick Links

- [Configuration Guide](USAGE.md#configuration) - Config files, profiles, CLI overrides
- [Available Voices](USAGE.md#available-voices) - All voices with descriptions
- [Emotion Tags](USAGE.md#emotion-tags) - How to use `[cheerful]`, `[calm]`, etc.
- [Troubleshooting](SETUP.md#troubleshooting) - Common issues and solutions
- [Architecture Diagram](SETUP.md#architecture-overview) - How components work together

## 🏗️ How It Works

PyAgentVox integrates with Claude Code through four coordinated components:

1. **PyAgentVox Main** - Listens to microphone, speaks responses with emotion-based voices
2. **TTS Monitor** - Watches Claude Code conversation files, sends responses to PyAgentVox
3. **Voice Injector** - Types recognized speech into Claude Code window (background typing, no focus stealing)
4. **Instructions Manager** - Auto-injects voice tag documentation into CLAUDE.md

**Multi-Instance Support:** Each Claude Code window gets its own PyAgentVox instance with per-window locking. Run multiple Claude Code windows with independent voice profiles simultaneously!

**Runtime Controls:** Toggle TTS/STT, switch voice profiles, and modify voice settings without restarting using CLI subcommands or skills.

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

## 🎚️ Runtime Controls

Control PyAgentVox on the fly without restarting:

### Voice Profile Switching

```bash
# Switch to a different voice profile instantly
python -m pyagentvox switch jenny
python -m pyagentvox switch male_voices

# Or from Claude Code:
/voice-switch jenny
```

**Use case:** Quickly change between different voice personas during a conversation!

### TTS/STT Toggle

```bash
# Mute TTS output (silent mode - text only)
python -m pyagentvox tts off

# Disable voice input (keyboard only)
python -m pyagentvox stt off

# Or from Claude Code:
/tts-control off
/stt-control off
```

**Use case:** Silent mode for public spaces, or keyboard-only when microphone isn't available!

### Voice Modification

```bash
# Adjust pitch/speed for all emotions
python -m pyagentvox modify pitch=+5
python -m pyagentvox modify speed=-10

# Adjust specific emotions
python -m pyagentvox modify neutral.pitch=+10
python -m pyagentvox modify cheerful.speed=-5

# Or from Claude Code:
/voice-modify pitch=+5
/voice-modify neutral.pitch=+10
```

**Use case:** Fine-tune voice to your preferences in real-time without config edits!

## 🖥️ Multi-Instance Support

Run multiple Claude Code windows with independent PyAgentVox instances!

**Per-Window Locking:** Each Claude Code window gets its own PyAgentVox instance using window-specific PID files. No conflicts, no interference.

```bash
# Window 1: Michelle voice
cd C:\projects\project1
python -m pyagentvox start --profile michelle

# Window 2: Guy voice (simultaneously!)
cd C:\projects\project2
python -m pyagentvox start --profile guy_voices
```

**Use case:** Work on multiple projects simultaneously with different voice profiles - one for coding, one for writing, each with their own personality!

**Note:** Each instance monitors its own Claude Code window. Voice input is sent to the specific window that started PyAgentVox.

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
