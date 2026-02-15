# PyAgentVox Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-02-15

### Added
- **Two-way voice communication** - Full bidirectional voice I/O for AI agents
- **Multi-voice emotion tag system** - Dynamic voice switching with `[cheerful]`, `[calm]`, `[excited]`, etc.
- **Voice profile system** - 8 pre-configured voice profiles (Michelle, Jenny, Emma, Aria, Ava, Sonia, Libby, Maisie)
- **Automatic Claude Code integration** - Seamless integration with Claude Code via subprocesses
- **Voice injector** - Keyboard automation to type speech into target application (Windows only)
- **TTS monitor** - Watches Claude Code conversation files and speaks responses automatically
- **Instruction auto-injection** - Automatically injects voice usage instructions into CLAUDE.md
- **Skills for easy startup** - `/voice` and `/voice-stop` skills for Claude Code
- **TTS-only mode** - Disable speech recognition for remote/noisy environments
- **Single-instance enforcement** - PID-based locking prevents multiple instances
- **Comprehensive documentation**:
  - SETUP.md - Complete setup guide with architecture diagrams
  - USAGE.md - Detailed CLI reference and configuration
  - AGENTS.md - Guide for AI assistants to set up voice for their humans
  - QUICK_REFERENCE.md - Command cheat sheet
- **Flexible configuration system** - JSON/YAML config with profiles and CLI overrides
- **Config discovery** - Auto-finds config in CWD, falls back to package default
- **8 emotion voices** - Neutral, cheerful, excited, empathetic, warm, calm, focused
- **Edge TTS integration** - Microsoft Edge TTS for high-quality natural voices
- **Google Speech API** - Real-time speech recognition
- **Natural pause handling** - TTS engine handles pauses based on text structure (no explicit delays)
- **No startup delay** - Voice injector immediately captures focused window

### Features
- **Speech-to-text (STT)** - Continuous microphone monitoring with Google Speech API
- **Text-to-speech (TTS)** - Emotion-based voice synthesis with Microsoft Edge TTS
- **Emotion tags** - Inline tags like `[cheerful]` to switch voice mid-response
- **Voice profiles** - Single-voice profiles with per-emotion tuning
- **Background subprocesses** - Auto-launches voice injector and TTS monitor
- **Temp file communication** - STT output and TTS input via temp files
- **PID file locking** - Prevents multiple instances
- **Graceful cleanup** - Removes voice instructions from CLAUDE.md on exit
- **Window focus detection** - Voice injector captures focused window on startup
- **Voice command support** - Say "stop listening" to stop PyAgentVox

### Configuration
- **Profile support** - Define multiple config variations in a single file
- **CLI overrides** - `--set` and `--modify` for runtime config changes
- **Shorthands** - `speed=10` applies to all emotions
- **Voice name resolution** - `michelle` → `en-US-MichelleNeural`
- **Auto-normalization** - `10` becomes `+10%` or `+10Hz`
- **Save overrides** - Persist CLI changes with `--save`

### Documentation
- Complete architecture documentation with component diagrams
- Step-by-step setup instructions
- Troubleshooting guide with solutions
- AI agent guidelines with emotion tag best practices
- Example responses for different scenarios
- Quick reference card for common commands

### Platform Support
- Windows support (voice injector requires win32gui and pynput)
- Python 3.12+ required
- Internet connection required (Edge TTS and Google Speech API)

### Dependencies
- edge-tts (Microsoft Edge TTS)
- SpeechRecognition (Google Speech API)
- pygame (audio playback)
- PyAudio (microphone access)
- pynput (keyboard automation)
- pywin32 (Windows API for window management)
- pyyaml (config file support)
- psutil (process management)
- mutagen (audio metadata)

## [Unreleased]

### Added
- **Auto-pause speech recognition** - STT automatically pauses after 10 minutes of inactivity
- **Smart resume on TTS** - STT resumes when AI responds (prevents background noise pickup)
- **TTS-only mode respect** - Auto-resume never activates STT if in TTS-only mode

### Future Considerations
- macOS/Linux support for voice injector
- Alternative TTS engines (local TTS, other cloud providers)
- Alternative STT engines (Whisper, local models)
- Customizable keyboard shortcuts
- Voice activity detection tuning
- Recording/playback of conversations
- Multiple AI platform integrations
