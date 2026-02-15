# PyAgentVox Setup Guide

**Two-way voice communication for Claude Code** - Speak to Claude and hear responses spoken aloud!

## 🎯 What is PyAgentVox?

PyAgentVox adds voice I/O to Claude Code:
- **Speak** into your microphone → Your words appear as text in Claude Code
- **Claude responds** → Response is spoken aloud with natural voice
- **Emotion tags** → Claude controls voice personality dynamically (`[cheerful]`, `[calm]`, etc.)

## 🏗️ Architecture Overview

PyAgentVox consists of 4 coordinating components:

```
┌─────────────────────────────────────────────────────────────┐
│                      PyAgentVox Main                        │
│  • Speech-to-text (STT) via Google Speech API              │
│  • Text-to-speech (TTS) via Microsoft Edge TTS              │
│  • Creates temp files for communication                     │
│  • Spawns background subprocesses                           │
└─────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
            ▼                 ▼                 ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │TTS Monitor   │  │Voice Injector│  │Instructions  │
    │              │  │              │  │Manager       │
    │Watches Claude│  │Types speech  │  │              │
    │conversation  │  │into Claude   │  │Auto-injects  │
    │files & sends │  │Code window   │  │voice tags    │
    │responses to  │  │using keyboard│  │into CLAUDE.md│
    │PyAgentVox    │  │automation    │  │              │
    └──────────────┘  └──────────────┘  └──────────────┘
```

### Component Details

1. **PyAgentVox Main** (`pyagentvox.py`)
   - Listens to microphone continuously
   - Writes speech to `agent_output_*.txt` (STT output)
   - Reads from `agent_input_*.txt` (TTS input)
   - Speaks responses using Edge TTS with emotion support
   - Single-instance enforcement via PID file

2. **TTS Monitor** (`tts.py`)
   - Subprocess launched by main process
   - Watches most recent Claude Code conversation JSONL file
   - Extracts assistant responses
   - Cleans markdown/code blocks for TTS
   - Writes cleaned text to PyAgentVox input file
   - Preserves emotion tags for multi-voice support

3. **Voice Injector** (`injection.py`)
   - Subprocess launched by main process
   - Monitors PyAgentVox output file (STT output)
   - Uses Windows messaging API (PostMessage) to type speech
   - Works without stealing focus - you can stay in your current window!
   - Presses Enter to submit to Claude Code
   - Supports "stop listening" voice command

4. **Instructions Manager** (`instruction.py`)
   - Automatically finds CLAUDE.md in project
   - Injects voice usage instructions on startup
   - Removes instructions on clean shutdown
   - Uses HTML comment markers for clean injection

## 📋 Prerequisites

### System Requirements
- **Python:** 3.12 or higher
- **OS:** Windows (voice injector uses win32gui)
- **Internet:** Required for Edge TTS and Google Speech API
- **Microphone:** For speech input

### Python Dependencies
All dependencies are in `pyproject.toml`:
- `edge-tts` - Microsoft Edge TTS engine
- `pygame` - Audio playback
- `SpeechRecognition` - Google Speech API wrapper
- `PyAudio` - Microphone access
- `pywin32` - Windows API (win32gui, win32api, win32con) for background keyboard input
- `psutil` - Process management
- `pyyaml` - Config file support
- `mutagen` - Audio file metadata

## 🚀 Quick Setup

### Step 1: Environment Setup

```bash
# Clone or navigate to pyagentvox directory
cd /path/to/pyagentvox

# Install dependencies (using uv or pip)
uv pip install -e .
# OR
pip install -e .
```

### Step 2: Test PyAgentVox Standalone

```bash
# Run PyAgentVox to test voice I/O
python -m pyagentvox --debug

# You should see:
#   ✓ TTS queue processor started
#   ✓ Started watching input file
#   ✓ Voice recognition ready! (Always listening)
```

Speak into your microphone - you should see:
```
[STT] You: hello testing
```

Write text to the input file to test TTS:
```bash
echo "Hello! [cheerful] This is a test!" > /tmp/agent_input_*.txt
```

You should hear the text spoken aloud.

### Step 3: Configure Voice Profile (Optional)

PyAgentVox comes with pre-configured profiles. Test them:

```bash
# Michelle (balanced)
python -m pyagentvox --profile michelle

# Jenny (energetic)
python -m pyagentvox --profile jenny

# Emma (warm)
python -m pyagentvox --profile emma

# British voices
python -m pyagentvox --profile sonia
python -m pyagentvox --profile libby
```

### Step 4: Integrate with Claude Code

**Method 1: Using Skills (Recommended)**

If your project has Claude Code skills configured:

```bash
# Start voice chat with default (Michelle voice)
/voice

# Or choose a specific voice profile
/voice jenny
/voice emma
/voice sonia

# Stop voice chat
/voice-stop
```

**Method 2: Direct Command**

```bash
# Start with specific profile
python -m pyagentvox --profile michelle

# TTS-only mode (no speech recognition)
python -m pyagentvox --tts-only --profile michelle

# Debug mode
python -m pyagentvox --debug --profile michelle
```

PyAgentVox will:
1. Start main process with selected voice profile
2. Auto-launch TTS monitor (watches Claude conversations)
3. Auto-launch voice injector (types speech into Claude Code)
4. Auto-inject voice instructions into CLAUDE.md
5. Begin listening to microphone immediately

**No startup delay needed!** The voice injector automatically captures the focused window.

### Step 5: Talk to Claude!

With everything running:
1. **Speak** into your microphone (make sure Claude Code window is focused)
2. Your speech is automatically typed into Claude Code and submitted
3. Claude responds with text (using emotion tags)
4. Response is spoken aloud with emotion-based voices

## ⚙️ Configuration

### Config File Location

PyAgentVox searches for config in this order:
1. `--config /path/to/config.yaml` (CLI argument)
2. `pyagentvox.json` in current directory
3. `pyagentvox.yaml` in current directory
4. `pyagentvox.yaml` in package directory (default)

### Config Format

```yaml
# Emotion-specific voice settings
neutral:
  voice: "en-US-MichelleNeural"
  speed: "+10%"
  pitch: "+10Hz"

cheerful:
  voice: "en-US-JennyNeural"
  speed: "+18%"
  pitch: "+12Hz"

excited:
  voice: "en-US-JennyNeural"
  speed: "+25%"
  pitch: "+15Hz"

empathetic:
  voice: "en-US-EmmaNeural"
  speed: "+0%"
  pitch: "+3Hz"

warm:
  voice: "en-US-EmmaNeural"
  speed: "+5%"
  pitch: "+8Hz"

calm:
  voice: "en-GB-SoniaNeural"
  speed: "+0%"
  pitch: "+3Hz"

focused:
  voice: "en-GB-SoniaNeural"
  speed: "+8%"
  pitch: "+0Hz"

# Profiles (alternative configs)
profiles:
  michelle:
    neutral:
      voice: "en-US-MichelleNeural"
      speed: "+10%"
      pitch: "+10Hz"
    cheerful:
      voice: "en-US-MichelleNeural"
      speed: "+18%"
      pitch: "+12Hz"
    # ... other emotions
```

### CLI Configuration

```bash
# Use specific profile
python -m pyagentvox --profile michelle

# Override specific values
python -m pyagentvox --set "speed=15 pitch=5"

# Modify existing values (adds to current)
python -m pyagentvox --modify "speed=+5 pitch=-3"

# Save overrides to config file
python -m pyagentvox --set "speed=15" --save

# TTS-only mode (disable speech recognition)
python -m pyagentvox --tts-only

# Debug logging
python -m pyagentvox --debug
```

## 🎭 Emotion Tags

Claude can use emotion tags to change voice dynamically:

```markdown
[neutral] This is the default voice.
[cheerful] This sounds happy and upbeat!
[excited] This is very enthusiastic!
[empathetic] This sounds caring and understanding.
[warm] This is gentle and kind.
[calm] This is professional and relaxed.
[focused] This is concentrated and steady.
```

**How it works:**
- Emotion tags split text into segments
- Each segment uses the specified emotion's voice settings
- Tags are removed before speaking
- Natural pauses between segments (handled by TTS engine)

## 🛠️ Advanced Usage

### TTS-Only Mode

Disable speech recognition (useful when working remotely):

```bash
python -m pyagentvox --tts-only
```

This mode:
- Disables microphone listening completely
- Only speaks Claude's responses
- Reduces CPU usage
- Useful for environments with background noise

### Auto-Pause Speech Recognition

**NEW:** Speech recognition automatically pauses after 10 minutes of inactivity!

**How it works:**
- STT pauses after 10 minutes with no speech detected
- Automatically resumes when TTS plays a response
- Prevents background audio pickup during idle periods
- Respects TTS-only mode (never resumes STT if disabled)

**Benefits:**
- No more accidental background audio
- Conversation-driven listening
- Automatic idle management

### Background Mode (Windows)

Run PyAgentVox as a hidden background process:

```bash
python -m pyagentvox --background --log-file pyagentvox.log

# Stop with:
taskkill /PID <pid>
```

### Custom Temp File Locations

PyAgentVox creates temp files automatically:
- `agent_input_*.txt` - TTS input (write here to speak)
- `agent_output_*.txt` - STT output (speech appears here)

Location: System temp directory (`/tmp` on Unix, `%TEMP%` on Windows)

### Manual Component Control

You can run components separately for debugging:

```bash
# Run only TTS monitor
python -m pyagentvox.tts --input-file /tmp/agent_input_12345.txt

# Run only voice injector
python -m pyagentvox.injection --output-file /tmp/agent_output_12345.txt --use-foreground --startup-delay 3
```

## 🐛 Troubleshooting

### PyAgentVox won't start

**Error:** `PyAgentVox is already running`

**Solution:**
```bash
# Find and kill existing process
ps aux | grep pyagentvox
kill <pid>

# Or on Windows:
taskkill /F /IM python.exe /FI "WINDOWTITLE eq PyAgentVox*"

# Remove stale lock file
rm /tmp/pyagentvox_v2.pid  # Unix
del %TEMP%\pyagentvox_v2.pid  # Windows
```

### Voice not speaking

**Symptoms:** Speech recognized but no audio output

**Checks:**
1. Verify input file exists: `ls /tmp/agent_input_*.txt`
2. Test manual write: `echo "Test" > /tmp/agent_input_*.txt`
3. Check internet connection (Edge TTS requires online access)
4. Look for TTS errors: `python -m pyagentvox --debug`

**Common causes:**
- Input file deleted (PyAgentVox will exit)
- Internet connection lost
- Audio device issues

### Speech not recognized

**Symptoms:** Microphone works but text doesn't appear

**Checks:**
1. Verify output file exists: `ls /tmp/agent_output_*.txt`
2. Check microphone permissions
3. Test with `python -m speech_recognition` (test script)
4. Adjust `energy_threshold` in config

**Solutions:**
```bash
# Increase microphone sensitivity
# Edit pyagentvox.py line ~619:
recognizer.energy_threshold = 150  # Lower = more sensitive
```

### Voice injector not typing

**Symptoms:** Speech recognized but not appearing in Claude Code

**Checks:**
1. Verify voice injector is running
2. **Claude Code window must be focused when PyAgentVox starts** (for window detection)
3. After startup, voice input works even when you're in other windows!

**Note:** The voice injector uses Windows messaging API to type into Claude Code without stealing focus. You can work in your browser, IDE, or any other window and still have your speech typed into Claude Code in the background!

**Solutions:**
```bash
# Focus Claude Code window briefly, then start PyAgentVox
# The injector captures the window handle on startup
python -m pyagentvox --profile michelle

# After startup, you can switch to other windows freely!
```

### Multiple instances running

**Symptoms:** Multiple PyAgentVox processes, temp file conflicts

**Solution:**
```bash
# Kill all python processes (WARNING: kills ALL python)
pkill -f pyagentvox

# Or more surgical (find PIDs first):
ps aux | grep pyagentvox
kill <pid1> <pid2> <pid3>
```

### Audio playback issues

**Symptoms:** TTS generates audio but pygame can't play it

**Solutions:**
```bash
# Verify pygame can access audio device
python -c "import pygame; pygame.mixer.init(); print('OK')"

# Check for conflicting audio applications
# Close other apps using audio device

# Try different audio backend (Linux):
SDL_AUDIODRIVER=alsa python -m pyagentvox
```

### Config not loading

**Symptoms:** Voice settings not applied

**Debug:**
```bash
python -m pyagentvox --debug

# Look for these messages:
# [Config] Loading: config.yaml
# [Config] Loading profile: michelle
# [Config] Applying overrides: {...}
```

**Common issues:**
- YAML syntax errors (use YAML validator)
- Profile name typo
- Config in wrong location

## 📁 Project Structure

```
pyagentvox/
├── pyagentvox/
│   ├── __init__.py          # Package exports
│   ├── __main__.py          # CLI entry point
│   ├── pyagentvox.py        # Main PyAgentVox class
│   ├── tts.py               # TTS monitor subprocess
│   ├── injection.py         # Voice injector subprocess
│   ├── instruction.py       # CLAUDE.md manager
│   ├── config.py            # Config loading/merging
│   └── pyagentvox.yaml      # Default config with profiles
├── SETUP.md                 # This file
├── README.md                # Quick start guide
├── USAGE.md                 # Detailed usage documentation
├── pyproject.toml           # Dependencies and package metadata
└── .claude/
    ├── voice-chat.sh        # Startup script for Claude Code
    └── voice-stop.sh        # Shutdown script
```

## 🔗 Related Files

**For Users:**
- **[README.md](README.md)** - Quick start and feature overview
- **[USAGE.md](USAGE.md)** - Comprehensive usage guide with examples
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Command cheat sheet
- **[pyagentvox.yaml](pyagentvox/pyagentvox.yaml)** - Default config with all voice profiles

**For AI Agents:**
- **[AGENTS.md](AGENTS.md)** - Setup guide for AI assistants to configure PyAgentVox for their humans

## 💡 Tips & Best Practices

1. **Start with a profile** - Easier than configuring voices manually
2. **Use --debug** - See exactly what's happening
3. **Test voices standalone first** - Verify PyAgentVox works before integrating with Claude
4. **Adjust energy_threshold** - If mic too sensitive or not sensitive enough
5. **Use TTS-only mode remotely** - Avoid picking up background audio
6. **Check temp files** - When debugging, examine `/tmp/agent_*.txt` directly
7. **Clean up stale locks** - If startup fails, remove PID file manually
8. **Work without interruption** - Voice input types into Claude Code in the background while you stay focused on other windows!

## 🎯 Next Steps

1. **Test standalone** - Run `python -m pyagentvox --debug`
2. **Try profiles** - Find your favorite voice with `--profile <name>`
3. **Integrate with Claude** - Use `voice-chat.sh` script
4. **Customize config** - Copy `pyagentvox.yaml` to project directory
5. **Read USAGE.md** - Learn advanced features and CLI options

Enjoy your voice-enabled AI conversations! 🎤✨
