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

**Method 2: CLI Subcommands**

PyAgentVox now uses a subcommand-based CLI for better control:

```bash
# Start with specific profile
python -m pyagentvox start --profile michelle

# Start in background (Windows only)
python -m pyagentvox start --profile michelle --background

# TTS-only mode (no speech recognition)
python -m pyagentvox start --tts-only --profile michelle

# Debug mode
python -m pyagentvox start --debug --profile michelle

# Stop running instance
python -m pyagentvox stop

# Check status
python -m pyagentvox status
```

**Backward Compatibility:** Running `python -m pyagentvox` without a subcommand defaults to `start` for backward compatibility.

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

# Speech recognition settings
stt:
  energy_threshold: 4000  # Lower = more sensitive microphone

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
python -m pyagentvox start --profile michelle

# Override specific values
python -m pyagentvox start --set "speed=15 pitch=5"

# Modify existing values (adds to current)
python -m pyagentvox start --modify "speed=+5 pitch=-3"

# Save overrides to config file
python -m pyagentvox start --set "speed=15" --save

# Adjust microphone sensitivity (lower = more sensitive)
python -m pyagentvox start --set "stt.energy_threshold=2000"

# TTS-only mode (disable speech recognition)
python -m pyagentvox start --tts-only

# Debug logging
python -m pyagentvox start --debug
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

## 🎮 Runtime Control

PyAgentVox supports comprehensive runtime control without restarting. All commands work on the instance for your current Claude Code window.

### Check Status

```bash
# View running status and control file paths
python -m pyagentvox status
```

Output shows:
- Lock ID (unique per Claude Code window)
- Running status (PID, memory, CPU)
- Control file paths for runtime commands

### Switch Voice Profile

```bash
# Hot-swap voice profile without restarting
python -m pyagentvox switch michelle
python -m pyagentvox switch jenny
python -m pyagentvox switch emma
python -m pyagentvox switch sonia
python -m pyagentvox switch libby
```

**How it works:**
- Profile switch queued immediately
- Changes apply after current TTS message finishes
- All 7 emotions updated simultaneously
- No interruption of audio playback

**Use cases:**
- Test different voices quickly
- Match voice to mood/context
- Switch between formal and casual tones

### Control TTS Output

```bash
# Disable voice output temporarily
python -m pyagentvox tts off

# Re-enable voice output
python -m pyagentvox tts on
```

**When to use:**
- Privacy (someone enters the room)
- Focus (reading Claude's response silently)
- Testing (verify text output without audio)
- Meetings (Claude still responds, just silently)

### Control Speech Recognition

```bash
# Stop listening to microphone
python -m pyagentvox stt off

# Resume listening
python -m pyagentvox stt on
```

**When to use:**
- Background noise (construction, music)
- Phone calls (prevent accidental triggers)
- Screensharing (avoid transmitting your voice commands)
- Battery saving (STT uses CPU)

### Modify Voice Settings

```bash
# Adjust pitch for all emotions
python -m pyagentvox modify pitch=+5     # Higher pitch
python -m pyagentvox modify pitch=-3     # Lower pitch

# Adjust speed for all emotions
python -m pyagentvox modify speed=+10    # Faster
python -m pyagentvox modify speed=-15    # Slower

# Adjust specific emotion
python -m pyagentvox modify neutral.pitch=+5
python -m pyagentvox modify cheerful.speed=+20
python -m pyagentvox modify calm.pitch=-3

# Adjust microphone sensitivity
python -m pyagentvox modify stt.energy_threshold=3000  # Less sensitive
python -m pyagentvox modify stt.energy_threshold=2000  # More sensitive

# Multiple adjustments at once
python -m pyagentvox modify "pitch=+5 speed=-10"
```

**How it works:**
- Changes apply to the next TTS message
- Relative adjustments (+/-) or absolute values
- Can target all emotions or specific ones
- Persists until PyAgentVox restarts (use `--set --save` for permanent)

**Use cases:**
- Tweak voice to your preference in real-time
- Adjust for room acoustics/speaker quality
- Compensate for microphone sensitivity
- Experiment with voice characteristics

### Stop Instance

```bash
# Gracefully stop PyAgentVox
python -m pyagentvox stop
```

**What it does:**
- Terminates main process
- Stops TTS monitor subprocess
- Stops voice injector subprocess
- Removes voice instructions from CLAUDE.md
- Cleans up PID file and temp files

**Always use this instead of:**
- Ctrl+C (may leave subprocesses running)
- `kill -9` (no cleanup)
- Closing terminal (orphans subprocesses)

## 🛠️ Advanced Usage

### CLI Subcommands

PyAgentVox uses a subcommand-based CLI for comprehensive control:

#### Start Command

```bash
# Start with default settings
python -m pyagentvox start

# Start with specific profile
python -m pyagentvox start --profile michelle

# Start in background (Windows only - no console window)
python -m pyagentvox start --profile michelle --background

# TTS-only mode (no speech recognition)
python -m pyagentvox start --tts-only

# Debug logging
python -m pyagentvox start --debug

# Custom config file
python -m pyagentvox start --config /path/to/config.yaml

# Override settings
python -m pyagentvox start --set "speed=15 pitch=5"

# Modify settings
python -m pyagentvox start --modify "speed=+5 pitch=-3"

# Save overrides to config file
python -m pyagentvox start --set "speed=15" --save
```

#### Stop Command

```bash
# Stop running instance for current window
python -m pyagentvox stop
```

Gracefully terminates PyAgentVox and cleans up:
- Stops TTS monitor subprocess
- Stops voice injector subprocess
- Removes voice instructions from CLAUDE.md
- Cleans up PID file

#### Status Command

```bash
# Check if PyAgentVox is running
python -m pyagentvox status
```

Shows:
- Running status (PID, memory usage, CPU usage)
- Lock ID (unique per Claude Code window)
- Control file paths for runtime commands

#### Switch Command

```bash
# Switch voice profile without restarting
python -m pyagentvox switch jenny
python -m pyagentvox switch emma
python -m pyagentvox switch sonia
```

Hot-swaps voice profile at runtime:
- No interruption of current TTS playback
- Changes apply after current message finishes
- All 7 emotions updated simultaneously

#### TTS/STT Control Commands

```bash
# Disable TTS (stop speaking responses)
python -m pyagentvox tts off

# Re-enable TTS
python -m pyagentvox tts on

# Disable STT (stop listening to microphone)
python -m pyagentvox stt off

# Re-enable STT
python -m pyagentvox stt on
```

Runtime control features:
- Changes take effect immediately
- No need to restart PyAgentVox
- Useful for temporary silence or privacy

#### Modify Command

```bash
# Adjust pitch for all emotions
python -m pyagentvox modify pitch=+5

# Adjust speed for all emotions
python -m pyagentvox modify speed=-10

# Adjust specific emotion
python -m pyagentvox modify neutral.pitch=+3
python -m pyagentvox modify cheerful.speed=+20

# Multiple adjustments
python -m pyagentvox modify "pitch=+5 speed=-10"
```

Voice modification features:
- Changes apply to next TTS message
- Can target all emotions or specific ones
- Supports relative adjustments (+/-)
- No restart required

### Per-Window Locking

PyAgentVox now supports running multiple instances for different Claude Code windows:

**How it works:**
- Each instance locks to a specific Claude Code conversation file
- Lock ID is an 8-character hash of the conversation file path
- Multiple windows = multiple PyAgentVox instances running simultaneously
- Each instance only monitors its own Claude Code window

**Benefits:**
- Run PyAgentVox in multiple Claude Code windows at the same time
- Each window gets its own voice profile
- Independent control per window (stop, switch, modify)
- No conflicts or cross-window interference

**Example:**
```bash
# Window 1 - Python project with Michelle voice
cd /projects/python-app
python -m pyagentvox start --profile michelle

# Window 2 - Node.js project with Jenny voice
cd /projects/node-app
python -m pyagentvox start --profile jenny

# Check status for current window
python -m pyagentvox status  # Shows unique lock ID

# Stop only this window's instance
python -m pyagentvox stop
```

### TTS-Only Mode

Disable speech recognition (useful when working remotely):

```bash
python -m pyagentvox start --tts-only
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
python -m pyagentvox start --background --log-file pyagentvox.log

# Stop with:
python -m pyagentvox stop
```

Background mode features:
- No console window (completely hidden)
- Logs written to file instead of console
- Use `--log-file` to specify log location
- Control with CLI subcommands (stop, switch, modify, etc.)

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
# Check status first
python -m pyagentvox status

# Stop the running instance cleanly
python -m pyagentvox stop

# If stop fails, find and kill process manually
ps aux | grep pyagentvox
kill <pid>

# Or on Windows:
tasklist | findstr python
taskkill /F /PID <pid>

# Remove stale lock file if needed
python -m pyagentvox stop  # Automatically cleans up
```

**Note:** With per-window locking, you can run multiple instances in different Claude Code windows. Each window gets its own lock based on the conversation file path.

### Voice not speaking

**Symptoms:** Speech recognized but no audio output

**Checks:**
```bash
# Check status
python -m pyagentvox status

# Enable TTS if disabled
python -m pyagentvox tts on

# Verify with debug logging
python -m pyagentvox start --debug
```

**Common causes:**
- TTS disabled with `python -m pyagentvox tts off`
- Internet connection lost (Edge TTS requires online access)
- Audio device issues
- Input file deleted (PyAgentVox will exit)

**Solutions:**
1. Re-enable TTS: `python -m pyagentvox tts on`
2. Check internet connection
3. Verify audio device works: `python -c "import pygame; pygame.mixer.init(); print('OK')"`
4. Restart PyAgentVox: `python -m pyagentvox stop && python -m pyagentvox start`

### Speech not recognized

**Symptoms:** Microphone works but text doesn't appear

**Checks:**
```bash
# Check status
python -m pyagentvox status

# Enable STT if disabled
python -m pyagentvox stt on

# Verify output file exists
ls /tmp/agent_output_*.txt  # Unix
dir %TEMP%\agent_output_*.txt  # Windows
```

**Solutions:**
```bash
# Adjust microphone sensitivity (lower = more sensitive)
python -m pyagentvox start --set "stt.energy_threshold=2000"

# Or modify at runtime
python -m pyagentvox modify stt.energy_threshold=2000

# Debug mode to see what's happening
python -m pyagentvox start --debug
```

**Common causes:**
- STT disabled with `python -m pyagentvox stt off`
- Microphone sensitivity too low (increase energy_threshold)
- Microphone permissions not granted
- Background noise causing false triggers
- STT auto-paused after 10 minutes of inactivity (will resume after TTS plays)

### Voice injector not typing

**Symptoms:** Speech recognized but not appearing in Claude Code

**Checks:**
```bash
# Check status
python -m pyagentvox status

# Verify voice injector subprocess is running
ps aux | grep injection  # Unix
tasklist | findstr injection  # Windows
```

**Solutions:**
```bash
# Focus Claude Code window briefly, then start PyAgentVox
# The injector captures the window handle on startup
python -m pyagentvox start --profile michelle

# After startup, you can switch to other windows freely!
# Voice input works in background without stealing focus
```

**Note:** The voice injector uses Windows messaging API to type into Claude Code without stealing focus. You can work in your browser, IDE, or any other window and still have your speech typed into Claude Code in the background!

### Runtime Control Not Working

**Symptoms:** Commands like `switch`, `tts`, `stt`, `modify` have no effect

**Checks:**
```bash
# Verify PyAgentVox is running
python -m pyagentvox status

# Check control file paths
python -m pyagentvox status  # Shows control file locations

# Verify files are being created
ls /tmp/agent_control_*.txt  # Unix
dir %TEMP%\agent_control_*.txt  # Windows
```

**Common causes:**
- PyAgentVox not running (start it first)
- Running command in wrong window (each window has its own instance)
- Control file permissions issues
- PyAgentVox hung or frozen (stop and restart)

**Solutions:**
```bash
# Restart PyAgentVox
python -m pyagentvox stop
python -m pyagentvox start --profile michelle --debug

# Try runtime commands again
python -m pyagentvox switch jenny
python -m pyagentvox tts on
```

### Multiple Instances Conflict

**Symptoms:** Multiple PyAgentVox processes, unexpected behavior

**Understanding:**
With per-window locking, multiple instances are **expected** if you're running PyAgentVox in multiple Claude Code windows. This is normal!

**Check which instances are running:**
```bash
# List all PyAgentVox instances
ps aux | grep pyagentvox  # Unix
tasklist | findstr python  # Windows

# Check status for current window
python -m pyagentvox status
```

**Stop specific instance:**
```bash
# Stop only the instance for current Claude Code window
python -m pyagentvox stop

# Stop all instances (be careful!)
pkill -f pyagentvox  # Unix
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *pyagentvox*"  # Windows
```

### Profile Switch Not Working

**Symptoms:** `python -m pyagentvox switch <profile>` doesn't change voice

**Checks:**
```bash
# Verify profile exists in config
python -m pyagentvox start --profile <profile>  # Test if profile loads

# Check for typos in profile name
cat pyagentvox.yaml | grep -A2 "profiles:"  # Unix
type pyagentvox.yaml | findstr "profiles:"  # Windows
```

**Solutions:**
```bash
# Wait for current TTS to finish
# Profile switch happens after current message completes

# Verify switch command succeeded
python -m pyagentvox switch michelle
# Should show: ✓ Switching to profile: michelle

# Test with TTS
echo "Test [cheerful] new profile!" > /tmp/agent_input_*.txt
```

### Microphone Too Sensitive

**Symptoms:** Background noise triggering speech recognition, false STT activations

**Solutions:**
```bash
# Increase energy threshold (higher = less sensitive)
python -m pyagentvox start --set "stt.energy_threshold=6000"

# Or modify at runtime
python -m pyagentvox modify stt.energy_threshold=6000

# Temporarily disable STT
python -m pyagentvox stt off

# Re-enable when ready
python -m pyagentvox stt on
```

### Audio Playback Issues

**Symptoms:** TTS generates audio but pygame can't play it

**Solutions:**
```bash
# Verify pygame can access audio device
python -c "import pygame; pygame.mixer.init(); print('OK')"

# Check for conflicting audio applications
# Close other apps using audio device

# Try different audio backend (Linux):
SDL_AUDIODRIVER=alsa python -m pyagentvox start

# Windows: Check audio device in system settings
```

### Config Not Loading

**Symptoms:** Voice settings not applied

**Debug:**
```bash
python -m pyagentvox start --debug

# Look for these messages:
# [Config] Loading: config.yaml
# [Config] Loading profile: michelle
# [Config] Applying overrides: {...}
```

**Common issues:**
- YAML syntax errors (use YAML validator)
- Profile name typo
- Config in wrong location
- Config file not readable

**Solutions:**
```bash
# Specify config explicitly
python -m pyagentvox start --config /path/to/pyagentvox.yaml

# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('pyagentvox.yaml'))"

# Check config search order
python -m pyagentvox start --debug  # Shows which config was loaded
```

### Getting Help

**Enable debug logging:**
```bash
python -m pyagentvox start --debug --log-file pyagentvox.log
```

**Check status:**
```bash
python -m pyagentvox status
```

**Examine control files:**
```bash
# Unix
ls -la /tmp/agent_*.txt
cat /tmp/agent_control_*.txt

# Windows
dir %TEMP%\agent_*.txt
type %TEMP%\agent_control_*.txt
```

**Clean restart:**
```bash
# Stop cleanly
python -m pyagentvox stop

# Start with debug
python -m pyagentvox start --debug --profile michelle
```

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

1. **Use subcommands** - Modern CLI: `python -m pyagentvox start`, `stop`, `status`, etc.
2. **Check status first** - Before troubleshooting: `python -m pyagentvox status`
3. **Start with a profile** - Easier than configuring voices manually
4. **Use --debug** - See exactly what's happening: `python -m pyagentvox start --debug`
5. **Test voices standalone first** - Verify PyAgentVox works before integrating with Claude
6. **Adjust energy_threshold** - Runtime: `python -m pyagentvox modify stt.energy_threshold=2000`
7. **Use TTS-only mode remotely** - Avoid picking up background audio: `python -m pyagentvox start --tts-only`
8. **Hot-swap profiles** - No restart needed: `python -m pyagentvox switch jenny`
9. **Runtime control** - Turn TTS/STT on/off without restarting
10. **Per-window instances** - Run PyAgentVox in multiple Claude Code windows simultaneously
11. **Check temp files** - When debugging, examine control files: `python -m pyagentvox status`
12. **Work without interruption** - Voice input types into Claude Code in the background while you stay focused on other windows!
13. **Clean shutdown** - Always stop gracefully: `python -m pyagentvox stop`

## 📝 Quick Command Reference

### Basic Commands

```bash
# Start PyAgentVox
python -m pyagentvox start
python -m pyagentvox start --profile michelle
python -m pyagentvox start --tts-only --profile jenny
python -m pyagentvox start --debug --background

# Stop PyAgentVox
python -m pyagentvox stop

# Check status
python -m pyagentvox status
```

### Runtime Control

```bash
# Switch voice profile
python -m pyagentvox switch <profile>

# Control TTS
python -m pyagentvox tts on
python -m pyagentvox tts off

# Control STT
python -m pyagentvox stt on
python -m pyagentvox stt off

# Modify voice settings
python -m pyagentvox modify pitch=+5
python -m pyagentvox modify speed=-10
python -m pyagentvox modify neutral.pitch=+3
python -m pyagentvox modify stt.energy_threshold=3000
```

### Configuration

```bash
# Use custom config
python -m pyagentvox start --config /path/to/config.yaml

# Override settings
python -m pyagentvox start --set "speed=15 pitch=5"

# Modify settings (relative)
python -m pyagentvox start --modify "speed=+5 pitch=-3"

# Save overrides to config
python -m pyagentvox start --set "speed=15" --save
```

### Available Profiles

```bash
michelle  # Balanced, professional (default)
jenny     # Energetic, upbeat
emma      # Warm, caring
sonia     # British, calm
libby     # British, friendly
```

### Emotion Tags (for Claude)

```markdown
[neutral]    # Default voice
[cheerful]   # Happy, upbeat
[excited]    # Very enthusiastic
[empathetic] # Caring, understanding
[warm]       # Gentle, kind
[calm]       # Professional, relaxed
[focused]    # Concentrated, steady
```

## 🎯 Next Steps

1. **Test standalone** - Run `python -m pyagentvox start --debug`
2. **Try profiles** - Find your favorite voice with `python -m pyagentvox start --profile <name>`
3. **Check status** - Use `python -m pyagentvox status` to verify it's running
4. **Experiment with runtime control** - Try switching profiles and modifying voice settings
5. **Integrate with Claude** - Use `/voice` skill or start manually
6. **Customize config** - Copy `pyagentvox.yaml` to project directory
7. **Read USAGE.md** - Learn advanced features and CLI options

Enjoy your voice-enabled AI conversations! 🎤✨
