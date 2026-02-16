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

## [0.2.0] - 2026-02-16

### Added
- **CLI subcommand architecture** - Clean command interface with 7 subcommands:
  - `start` - Start PyAgentVox with full configuration options
  - `stop` - Stop running instance for current window
  - `switch <profile>` - Hot-swap voice profile without restarting
  - `tts on|off` - Toggle text-to-speech at runtime
  - `stt on|off` - Toggle speech recognition at runtime
  - `modify <setting>` - Modify voice settings on the fly (pitch, speed)
  - `status` - Show running status, PID, memory, and control files
- **Per-window locking** - Multiple Claude Code windows can run independent PyAgentVox instances simultaneously
  - MD5 hash of conversation file path creates unique lock ID per window
  - PID files: `/tmp/pyagentvox_{lock_id}.pid` instead of hardcoded path
  - Automatic stale lock cleanup with psutil validation
- **Runtime voice controls** - Modify voice without restarting:
  - Toggle TTS/STT independently (`/tts-control`, `/stt-control` skills)
  - Adjust pitch globally or per-emotion (`pitch=+5`, `neutral.pitch=+10`)
  - Adjust speed globally or per-emotion (`speed=-10`, `cheerful.speed=-5`)
  - Apply modifications to all emotions at once (`all.pitch=+3`)
- **Profile hot-swapping** - Switch voice profiles seamlessly:
  - Queue-based switching prevents race conditions
  - Processes multiple switches in order
  - Waits for current TTS to finish before switching
  - Updates CLAUDE.md instructions automatically
- **Six Claude Code skills** for easy control:
  - `/voice [profile] [modes...]` - Start with combined options (e.g., `michelle tts-only debug`)
  - `/voice-stop` - Clean shutdown with instruction removal
  - `/voice-switch <profile>` - Hot-swap to different voice profile
  - `/tts-control on|off` - Toggle voice output
  - `/stt-control on|off` - Toggle voice input
  - `/voice-modify <setting>` - Adjust voice settings at runtime
- **Comprehensive documentation** - 5 updated documentation files:
  - README.md with table of contents for all docs (main + development)
  - AGENTS.md completely rewritten (684 lines) for AI agent implementation
  - SETUP.md expanded (536→1107 lines) with runtime controls and troubleshooting
  - USAGE.md with complete CLI reference and IPC deep dive
  - QUICK_REFERENCE.md one-page cheat sheet with all commands
- **Five concurrent watchers** for responsive runtime control:
  - Input file watcher (TTS requests from monitor)
  - Profile control file watcher (hot-swap requests)
  - Control file watcher (TTS/STT on/off commands)
  - Modify file watcher (voice adjustment requests)
  - TTS queue processor (sequential playback)
- **Auto-pause speech recognition** - STT automatically pauses after 10 minutes of inactivity
- **Smart resume on TTS** - STT resumes when AI responds (prevents background noise pickup)
- **TTS-only mode respect** - Auto-resume never activates STT if in TTS-only mode
- **Profile hot-swap testing** - pytest test suite for profile switching
- **Configurable mic sensitivity** - `stt.energy_threshold` setting (lower = more sensitive, default 4000)

### Changed
- **CLI entry point refactored** - Backward compatible with old commands (e.g., `python -m pyagentvox --tts-only` auto-converts to `start` subcommand)
- **Skills simplified** - All skills now use CLI subcommands instead of duplicating logic
- **Background keyboard input** - Voice injector uses Windows messaging API (PostMessage) for no focus stealing
- **Documentation organization** - README.md now has comprehensive table of contents linking all docs
- **Pytest configuration** - Moved from `pytest.ini` to `pyproject.toml` `[tool.pytest.ini_options]`
- **Conversation file detection** - Improved detection excludes subagent files, searches multiple locations

### Fixed
- **Duplicate instance prevention** - Skills now properly check PyAgentVox status before starting
- **Per-window locking bugs** - Fixed conversation file detection on Windows paths
- **Voice profile conflicts** - Queue-based switching eliminates "everything plays in last voice" bug
- **Parallel TTS generation** - All emotion segments generate in parallel, play sequentially
- **Smart path filtering** - TTS output no longer includes verbose file paths

### Removed
- **Obsolete files cleaned up**:
  - `switch_voice.sh` - Replaced by `/voice-switch` skill with hot-swapping
  - `pytest.ini` - Configuration moved to `pyproject.toml`
  - `config.example.yaml` - Redundant with documented config structure
- **Hardcoded PID files** - All skills updated to use per-window locking

### Documentation
- **README.md** - Added "The Wow Factor" section highlighting runtime controls and multi-instance support
- **AGENTS.md** - Complete rewrite with CLI reference, runtime controls, per-window locking, and implementation checklist
- **SETUP.md** - Nearly doubled in size with runtime control sections and comprehensive troubleshooting
- **USAGE.md** - Added complete subcommand reference, control file IPC documentation, per-window locking explanation
- **QUICK_REFERENCE.md** - Updated with all 6 skills and CLI subcommands

### Technical Improvements
- **IPC via control files** - Clean file-based inter-process communication for runtime controls
- **Asyncio queues** - Profile switch queue prevents race conditions
- **Type hints** - Consistent use of `str | None` instead of `Optional[str]`
- **Error handling** - Improved exception handling in all watchers
- **Resource cleanup** - Proper atexit handlers for lock file removal

## [0.2.1] - 2026-02-16

### Documentation
- Applied new documentation standards across all docs
- Added internal table of contents to README
- Added human-friendly abstract explaining value proposition
- Removed casual language and marketing fluff
- Removed links to .gitignore'd files
- Created documentation agent with style guidelines
- Reduced excessive emoji usage (kept section markers only)

## [Unreleased]

### Future Considerations
- macOS/Linux support for voice injector
- Alternative TTS engines (local TTS, other cloud providers)
- Alternative STT engines (Whisper, local models)
- Customizable keyboard shortcuts
- Voice activity detection tuning
- Recording/playback of conversations
- Multiple AI platform integrations
