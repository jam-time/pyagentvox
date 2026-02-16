# PyAgentVox Usage Guide

**Two-way voice communication for AI agents** - Speak to your AI and hear it respond!

## 📋 Documentation Navigation

**New to PyAgentVox?** Read [SETUP.md](SETUP.md) first for:
- Architecture overview and how components work together
- Step-by-step setup instructions
- Prerequisites and installation
- Claude Code integration
- Troubleshooting guide

**Need quick answers?** Check [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for:
- Common CLI commands
- Emotion tags reference
- Voice profiles list
- Quick troubleshooting

**This guide covers:**
- Complete CLI reference with all subcommands
- Runtime control and IPC mechanisms
- Config file formats and profiles
- Available voices with descriptions
- Programmatic usage (Python API)
- Advanced features and tips

---

## CLI Overview

PyAgentVox uses a **subcommand-based CLI** for managing voice instances and runtime control.

### Basic Command Structure

```bash
python -m pyagentvox <subcommand> [options]
```

### Available Subcommands

| Subcommand | Description |
|------------|-------------|
| `start` | Start PyAgentVox (default if no subcommand given) |
| `stop` | Stop running instance for this window |
| `switch` | Switch voice profile at runtime |
| `tts` | Enable/disable TTS output |
| `stt` | Enable/disable speech recognition |
| `modify` | Modify voice settings at runtime |
| `status` | Show status and control file paths |

---

## Subcommands Reference

### `start` - Start PyAgentVox

Start a new PyAgentVox instance with specified configuration.

**Usage:**
```bash
python -m pyagentvox start [options]

# Backward compatibility: omitting 'start' defaults to start subcommand
python -m pyagentvox [options]
```

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--config PATH` | str | Path to config file (JSON or YAML) |
| `--profile NAME` | str | Load config profile by name |
| `--instructions-path PATH` | str | Path to CLAUDE.md for voice instruction injection |
| `--set "KEY=VALUE ..."` | str | Set config values (space-separated) |
| `--modify "KEY=MODIFIER ..."` | str | Modify config values (space-separated) |
| `--save` | flag | Save changes back to config file |
| `--debug` | flag | Enable debug logging |
| `--log-file PATH` | str | Write logs to file |
| `--background` | flag | Run in background (Windows only) |
| `--tts-only` | flag | TTS only mode (disable speech recognition) |

**Examples:**

```bash
# Run with default settings
python -m pyagentvox start

# Run with debug logging
python -m pyagentvox start --debug

# Use a specific config file
python -m pyagentvox start --config my_config.yaml

# Load a profile from config
python -m pyagentvox start --profile michelle

# TTS-only mode (disable speech recognition)
python -m pyagentvox start --tts-only

# Override specific config values
python -m pyagentvox start --set "warm.pitch=+20Hz"

# Override multiple values (space-separated)
python -m pyagentvox start --set "speed=15 pitch=-5"

# Save overrides back to config file
python -m pyagentvox start --set "warm.pitch=+20Hz" --save

# Run in background with logging (Windows only)
python -m pyagentvox start --background --log-file pyagentvox.log

# Combine profile with overrides
python -m pyagentvox start --profile male_voices --set "cheerful.speed=+25%"
```

**Background Mode (Windows Only):**

When using `--background`:
- Launches as detached process (no console window)
- Returns immediately with process ID
- All output redirected to log file
- **Must use `--log-file`** to capture output
- Stop with `python -m pyagentvox stop` or Task Manager

**Config Override Syntax:**

The `--set` flag accepts space-separated `key=value` pairs:

```bash
# Set multiple values at once
--set "neutral.voice=michelle speed=10 pitch=-5"

# Shorthands apply to all emotions
--set "speed=15"   # Sets speed=+15% for all emotions
--set "voice=jenny"  # Sets voice to Jenny for all emotions

# Voice name shortcuts (auto-resolved):
# Female: michelle, jenny, emma, aria, ava, sonia, libby, maisie
# Male: guy, davis, tony, jason, ryan, thomas
```

**Config Modification Syntax:**

The `--modify` flag **adds to existing values** instead of replacing:

```bash
# Add +5 to current speed, -3 to current pitch
--modify "speed=5 pitch=-3"

# Combine --set (replace) and --modify (add)
--set "voice=jenny" --modify "speed=10"
```

---

### `stop` - Stop Running Instance

Stop the PyAgentVox instance for the current Claude Code window.

**Usage:**
```bash
python -m pyagentvox stop
```

**Behavior:**
- Terminates PyAgentVox process for this window (per-window locking)
- Cleans up PID file and temporary files
- Waits up to 5 seconds for graceful shutdown
- Force kills if process doesn't respond
- Removes injected voice instructions from CLAUDE.md

**Requirements:**
- `psutil` package (installed by default)

**Examples:**

```bash
# Stop running instance
python -m pyagentvox stop

# Stop will clean up stale PID files if process is not running
```

---

### `switch` - Switch Voice Profile

Switch voice profile at runtime without restarting PyAgentVox.

**Usage:**
```bash
python -m pyagentvox switch <profile>
```

**Arguments:**
- `<profile>` - Profile name from config file (e.g., `michelle`, `male_voices`)

**Behavior:**
- Writes profile name to control file
- Profile switch queued (processes in order)
- Changes take effect after current TTS finishes
- Re-injects voice instructions with new profile info
- Preserves runtime modifications (TTS/STT state, voice modifications)

**Examples:**

```bash
# Switch to 'michelle' profile
python -m pyagentvox switch michelle

# Switch to custom profile
python -m pyagentvox switch male_voices

# Multiple switches are queued and processed in order
python -m pyagentvox switch jenny
python -m pyagentvox switch michelle
```

**Note:** Profile must be defined in config file under `profiles` key.

---

### `tts` - Control TTS Output

Enable or disable text-to-speech output at runtime.

**Usage:**
```bash
python -m pyagentvox tts <on|off>
```

**Arguments:**
- `on` - Enable TTS (speak responses)
- `off` - Disable TTS (silent mode)

**Behavior:**
- Writes command to control file: `tts:on` or `tts:off`
- Takes effect immediately for next message
- Does not affect queued messages already being processed
- Preserves speech recognition (STT) state

**Examples:**

```bash
# Disable TTS (silent mode)
python -m pyagentvox tts off

# Re-enable TTS
python -m pyagentvox tts on
```

---

### `stt` - Control Speech Recognition

Enable or disable speech recognition at runtime.

**Usage:**
```bash
python -m pyagentvox stt <on|off>
```

**Arguments:**
- `on` - Enable speech recognition
- `off` - Disable speech recognition (listen-only mode)

**Behavior:**
- Writes command to control file: `stt:on` or `stt:off`
- Takes effect immediately
- Microphone stops listening when disabled
- Does not affect TTS output

**Examples:**

```bash
# Disable speech recognition (listen-only mode)
python -m pyagentvox stt off

# Re-enable speech recognition
python -m pyagentvox stt on
```

---

### `modify` - Modify Voice Settings

Modify voice settings (pitch, speed, voice) at runtime.

**Usage:**
```bash
python -m pyagentvox modify <setting>
```

**Arguments:**
- `<setting>` - Modification string in format: `key=value`

**Supported Modifications:**

| Format | Description | Example |
|--------|-------------|---------|
| `pitch=±N` | Adjust pitch (all emotions) | `pitch=+5` → add +5Hz to all |
| `speed=±N` | Adjust speed (all emotions) | `speed=-10` → subtract 10% from all |
| `<emotion>.pitch=±N` | Adjust emotion-specific pitch | `neutral.pitch=+10` |
| `<emotion>.speed=±N` | Adjust emotion-specific speed | `cheerful.speed=-5` |
| `<emotion>.voice=NAME` | Change emotion voice | `neutral.voice=en-US-GuyNeural` |
| `all.pitch=±N` | Explicitly modify all emotions | `all.pitch=+3` |

**Behavior:**
- Writes modification to control file
- Changes take effect for **next** TTS message
- Modifications are **cumulative** (add to existing values)
- For voice changes, value is replaced (not cumulative)

**Examples:**

```bash
# Increase pitch for all emotions
python -m pyagentvox modify "pitch=+5"

# Decrease speed for neutral emotion
python -m pyagentvox modify "neutral.speed=-10"

# Change neutral voice to Guy (male)
python -m pyagentvox modify "neutral.voice=en-US-GuyNeural"

# Modify multiple emotions
python -m pyagentvox modify "all.pitch=+3"
python -m pyagentvox modify "cheerful.speed=+5"
```

**Value Adjustment:**

Modifications are **additive** for pitch and speed:
- Current: `+20Hz`, Modifier: `+5` → Result: `+25Hz`
- Current: `+10%`, Modifier: `-5` → Result: `+5%`
- Current: `+5%`, Modifier: `-10` → Result: `-5%`

---

### `status` - Show Status

Display status and control file paths for the current window.

**Usage:**
```bash
python -m pyagentvox status
```

**Output:**
- Lock ID (unique per Claude Code window)
- Running status (PID, memory, CPU usage)
- Control file paths for manual IPC

**Examples:**

```bash
# Check if PyAgentVox is running
python -m pyagentvox status

# Example output:
# PyAgentVox Status
# ==================================================
# Lock ID: a3f8b2c1
# Status: ✓ Running
# PID: 12345
# Memory: 145.2 MB
# CPU: 2.3%
#
# Control files:
#   Profile: C:\Users\...\Temp\agent_profile_12345.txt
#   Control: C:\Users\...\Temp\agent_control_12345.txt
#   Modify: C:\Users\...\Temp\agent_modify_12345.txt
```

**Requirements:**
- `psutil` package (installed by default)

---

## Per-Window Locking

PyAgentVox uses **per-window locking** to allow multiple instances for different Claude Code windows.

### How It Works

1. **Conversation File Detection** - Finds active Claude Code conversation JSONL file:
   - Checks `CLAUDE_CONVERSATION_FILE` environment variable
   - Searches `~/.claude/projects/` for most recent `.jsonl` file
   - Excludes subagent files

2. **Lock ID Generation** - Creates 8-character hash from conversation file path:
   ```
   /path/to/.claude/projects/abc123/conversation.jsonl
   → MD5 hash → a3f8b2c1
   ```

3. **PID File** - Creates unique PID file per window:
   ```
   Windows: %TEMP%\pyagentvox_a3f8b2c1.pid
   Unix:    /tmp/pyagentvox_a3f8b2c1.pid
   ```

4. **Stale Lock Cleanup** - Automatically removes stale locks:
   - Checks if PID exists and is a PyAgentVox process
   - Removes lock if process is dead or not PyAgentVox
   - Retries up to 3 times with 500ms delay

### Benefits

- **Multi-Window Support** - Run separate instances for different Claude Code windows
- **No Conflicts** - Each window has independent voice configuration
- **Smart Fallback** - Falls back to global lock if conversation file not found
- **Auto Cleanup** - Stale locks are automatically cleaned up

### Manual Lock Management

```bash
# Check which window you're in
python -m pyagentvox status
# Shows Lock ID: a3f8b2c1

# Stop instance for this window only
python -m pyagentvox stop

# Remove stale lock manually (if needed)
# Windows:
del %TEMP%\pyagentvox_a3f8b2c1.pid

# Unix:
rm /tmp/pyagentvox_a3f8b2c1.pid
```

---

## Control File IPC

PyAgentVox uses **file-based IPC** for runtime control. Control files are located in:
- **Windows:** `%TEMP%\agent_*_{pid}.txt`
- **Unix:** `/tmp/agent_*_{pid}.txt`

### Control File Types

| File Name | Purpose | Format | Watched By |
|-----------|---------|--------|------------|
| `agent_profile_{pid}.txt` | Profile switching | Profile name | `_watch_profile_control()` |
| `agent_control_{pid}.txt` | TTS/STT on/off | `tts:on\|off`, `stt:on\|off` | `_watch_control_file()` |
| `agent_modify_{pid}.txt` | Voice modifications | `key=value` | `_watch_modify_file()` |
| `agent_input_{pid}.txt` | TTS input (from monitor) | Text to speak | `_watch_input_file()` |
| `agent_output_{pid}.txt` | STT output (from recognizer) | Recognized text | Voice injector |

### Manual Control

You can write to control files manually instead of using CLI subcommands:

```bash
# Get PID from status command
python -m pyagentvox status
# PID: 12345

# Switch profile (Windows)
echo michelle > %TEMP%\agent_profile_12345.txt

# Switch profile (Unix)
echo michelle > /tmp/agent_profile_12345.txt

# Disable TTS (Windows)
echo tts:off > %TEMP%\agent_control_12345.txt

# Disable TTS (Unix)
echo tts:off > /tmp/agent_control_12345.txt

# Modify pitch (Windows)
echo pitch=+5 > %TEMP%\agent_modify_12345.txt

# Modify pitch (Unix)
echo pitch=+5 > /tmp/agent_modify_12345.txt
```

### File Watching Behavior

- **Polling Interval:** 500ms for control files, 400ms for input file
- **File Deletion:** Control files are deleted after processing
- **Modification Time:** Uses `st_mtime` to detect changes
- **Write Delay:** Waits 100ms after detecting change to ensure write completion
- **Queue Processing:** Profile switches and voice modifications are queued and processed in order

### IPC Message Flow

```
┌─────────────────────────────────────────────────────┐
│                  PyAgentVox Process                 │
│                                                     │
│  ┌──────────────┐      ┌──────────────┐           │
│  │ TTS Monitor  │─────▶│ Input File   │           │
│  │ (subprocess) │ write│ (agent_input)│           │
│  └──────────────┘      └──────┬───────┘           │
│                                │                    │
│                                ▼                    │
│                         ┌──────────────┐           │
│                         │ TTS Queue    │           │
│                         │ (async)      │           │
│                         └──────┬───────┘           │
│                                │                    │
│                                ▼                    │
│                         ┌──────────────┐           │
│                         │ Speech Gen   │           │
│                         └──────────────┘           │
│                                                     │
│  ┌──────────────┐      ┌──────────────┐           │
│  │ STT Thread   │─────▶│ Output File  │           │
│  │ (threaded)   │ write│ (agent_output)│          │
│  └──────────────┘      └──────┬───────┘           │
│                                │                    │
│                                ▼                    │
│                         ┌──────────────┐           │
│                         │Voice Injector│           │
│                         │ (subprocess) │           │
│                         └──────────────┘           │
│                                                     │
│  ┌──────────────┐      ┌──────────────┐           │
│  │ CLI Commands │─────▶│Control Files │           │
│  │ (switch/    │ write│ (profile/    │           │
│  │  tts/stt/   │      │  control/    │           │
│  │  modify)    │      │  modify)     │           │
│  └──────────────┘      └──────┬───────┘           │
│                                │                    │
│                                ▼                    │
│                         ┌──────────────┐           │
│                         │File Watchers │           │
│                         │ (async)      │           │
│                         └──────────────┘           │
└─────────────────────────────────────────────────────┘
```

---

## Configuration

### Config File Discovery

PyAgentVox looks for config files in this order:

1. File specified with `--config path/to/config.yaml`
2. `pyagentvox.json` in current directory
3. `pyagentvox.yaml` in current directory
4. `config.yaml` in package directory (fallback)

### Config File Format

Supports both **YAML** and **JSON** formats.

#### Example config.yaml

```yaml
# Speech Recognition Settings
stt:
  energy_threshold: 4000  # Microphone sensitivity (lower = more sensitive)
                          # Typical range: 300-4000
                          # Adjust if mic is too sensitive or not picking up speech

# Emotion-specific voice settings (no nesting!)
neutral:
  voice: "en-US-MichelleNeural"
  speed: "+10%"
  pitch: "+10Hz"

cheerful:
  voice: "en-US-JennyNeural"
  speed: "+15%"
  pitch: "+8Hz"

excited:
  voice: "en-US-JennyNeural"
  speed: "+20%"
  pitch: "+15Hz"

empathetic:
  voice: "en-US-EmmaNeural"
  speed: "+8%"
  pitch: "+12Hz"

warm:
  voice: "en-US-EmmaNeural"
  speed: "+8%"
  pitch: "+18Hz"

calm:
  voice: "en-GB-SoniaNeural"
  speed: "+0%"
  pitch: "-2Hz"

focused:
  voice: "en-US-AvaNeural"
  speed: "+5%"
  pitch: "+5Hz"

# Optional: Define profiles for different configs
profiles:
  male_voices:
    neutral:
      voice: "en-US-GuyNeural"
    cheerful:
      voice: "en-US-JasonNeural"
    calm:
      voice: "en-GB-RyanNeural"

  debug:
    neutral:
      speed: "-10%"  # Slower for testing
```

#### Example pyagentvox.json

```json
{
  "stt": {
    "energy_threshold": 4000
  },
  "neutral": {
    "voice": "en-US-MichelleNeural",
    "speed": "+10%",
    "pitch": "+10Hz"
  },
  "cheerful": {
    "voice": "en-US-JennyNeural",
    "speed": "+15%",
    "pitch": "+8Hz"
  },
  "profiles": {
    "male_voices": {
      "neutral": {
        "voice": "en-US-GuyNeural"
      }
    }
  }
}
```

### Profiles

Profiles let you store multiple config variations in a single file.

#### Defining Profiles

In your `config.yaml`:

```yaml
# Base config
neutral:
  voice: "en-US-MichelleNeural"
  speed: "+10%"
  pitch: "+10Hz"

# Profiles (alternative configurations)
profiles:
  # Profile: male_voices
  male_voices:
    neutral:
      voice: "en-US-GuyNeural"
      pitch: "+0Hz"
    cheerful:
      voice: "en-US-JasonNeural"

  # Profile: high_energy
  high_energy:
    neutral:
      speed: "+20%"
      pitch: "+15Hz"
    cheerful:
      speed: "+30%"
      pitch: "+20Hz"

  # Profile: debug (slower for testing)
  debug:
    neutral:
      speed: "-10%"
```

#### Using Profiles

```bash
# Load the "male_voices" profile
python -m pyagentvox start --profile male_voices

# Load profile and override specific values
python -m pyagentvox start --profile male_voices --set "calm.voice=en-GB-RyanNeural"
```

**How profiles work:**
1. Base config is loaded
2. Profile overrides are applied (recursively merged)
3. CLI overrides are applied last

---

## Available Voices

### Female Voices

| Voice | Description |
|-------|-------------|
| `en-US-MichelleNeural` | Balanced, default |
| `en-US-JennyNeural` | Energetic, upbeat |
| `en-US-EmmaNeural` | Warm, caring |
| `en-US-AriaNeural` | Friendly, bright |
| `en-US-AvaNeural` | Professional |
| `en-GB-SoniaNeural` | British, calm |
| `en-GB-LibbyNeural` | British, friendly |
| `en-GB-MaisieNeural` | British, young |

### Male Voices

| Voice | Description |
|-------|-------------|
| `en-US-GuyNeural` | Casual, conversational |
| `en-US-DavisNeural` | Professional, authoritative |
| `en-US-TonyNeural` | News anchor style |
| `en-US-JasonNeural` | Energetic, enthusiastic |
| `en-GB-RyanNeural` | British, professional |
| `en-GB-ThomasNeural` | British, formal |

---

## Programmatic Usage

### Basic Usage

```python
from pyagentvox import run

# Run with default config
run()

# Run with debug logging
run(debug=True)

# Run with custom config
run(config_path='my_config.yaml')

# Run with profile
run(config_path='config.yaml', profile='male_voices')

# TTS-only mode
run(tts_only=True)
```

### With Config Dictionary

```python
from pyagentvox import run

config = {
    'neutral': {
        'voice': 'en-US-GuyNeural',
        'speed': '+10%',
        'pitch': '+5Hz'
    },
    'cheerful': {
        'voice': 'en-US-JasonNeural',
        'speed': '+15%',
        'pitch': '+10Hz'
    }
}

run(config_dict=config)
```

### With Config Overrides

```python
from pyagentvox import run

# Load config and apply overrides
overrides = {
    'warm': {
        'pitch': '+25Hz'
    }
}

run(
    config_path='config.yaml',
    config_overrides=overrides,
    debug=True
)
```

### Using the PyAgentVox Class

```python
import asyncio
from pyagentvox import PyAgentVox

# Create instance with config
config = {
    'neutral': {'voice': 'en-US-GuyNeural'}
}

agent = PyAgentVox(config_dict=config)

# Run the agent
asyncio.run(agent.run())
```

---

## Auto-Injection of Voice Instructions

PyAgentVox automatically injects voice usage instructions into your CLAUDE.md file when started.

### How It Works

1. When PyAgentVox starts, it searches for CLAUDE.md in:
   - Current directory
   - Parent directory
   - Claude Code project directory (via `~/.claude/projects/*/sessions-index.json`)

2. Injects voice instructions wrapped in HTML comment markers:
   ```markdown
   <!-- PYAGENTVOX_START -->
   # Voice Output Active 🎤
   [... voice instructions ...]
   <!-- PYAGENTVOX_END -->
   ```

3. When PyAgentVox stops, it cleanly removes the injected section

### Benefits

- **Zero Configuration**: The AI automatically knows how to use emotion tags
- **Clean Integration**: Uses HTML comments for non-intrusive injection
- **Auto Cleanup**: Instructions are removed when PyAgentVox stops
- **Smart Discovery**: Finds your CLAUDE.md even in complex project structures

### Manual Management

If you want to manually manage the instructions:

```python
from pyagentvox import instruction

# Inject instructions
instruction.inject_voice_instructions()

# Remove instructions
instruction.remove_voice_instructions()

# Use custom CLAUDE.md path
from pathlib import Path
instruction.inject_voice_instructions(Path("/path/to/CLAUDE.md"))
```

---

## Emotion Tags

Use emotion tags in your AI's responses to change voice personality:

```
[neutral] This is the default voice.
[cheerful] This sounds happy and upbeat!
[excited] This is very enthusiastic!
[empathetic] This sounds caring and understanding.
[warm] This is gentle and kind.
[calm] This is professional and relaxed.
[focused] This is concentrated and steady.
```

**For AI Agents:** See [AI_INSTRUCTIONS.md](AI_INSTRUCTIONS.md) for comprehensive guidelines on when and how to use emotion tags effectively. Also check [SYSTEM_PROMPT.txt](SYSTEM_PROMPT.txt) for a quick prompt to add to your AI's system instructions.

---

## Advanced Features

### Runtime Control Examples

```bash
# Start PyAgentVox
python -m pyagentvox start --profile michelle --debug

# Switch to different profile (hot-swap)
python -m pyagentvox switch male_voices

# Disable TTS temporarily
python -m pyagentvox tts off

# Make voice modifications
python -m pyagentvox modify "pitch=+5"
python -m pyagentvox modify "neutral.speed=-10"

# Re-enable TTS
python -m pyagentvox tts on

# Check status
python -m pyagentvox status

# Stop when done
python -m pyagentvox stop
```

### Custom Config Locations

```bash
# Use config in project directory
cd my-project
echo '{"neutral": {"voice": "en-US-GuyNeural"}}' > pyagentvox.json
python -m pyagentvox start  # Auto-detects pyagentvox.json

# Or specify path
python -m pyagentvox start --config /path/to/my-config.yaml
```

### Persistent Overrides

Save CLI overrides back to config:
```bash
# Test a change
python -m pyagentvox start --set "warm.pitch=+25Hz"

# Like it? Save it permanently
python -m pyagentvox start --set "warm.pitch=+25Hz" --save
```

### Multiple Profiles

Create workflow-specific profiles:

```yaml
profiles:
  development:
    neutral:
      speed: "-10%"  # Slower for clarity

  presentation:
    neutral:
      speed: "+15%"  # Faster and energetic
      pitch: "+10Hz"

  late_night:
    neutral:
      voice: "en-GB-SoniaNeural"  # Calm British voice
      speed: "+0%"
      pitch: "-5Hz"
```

Then switch between them:
```bash
python -m pyagentvox start --profile development
python -m pyagentvox switch presentation
python -m pyagentvox switch late_night
```

---

## Tips & Best Practices

1. **Start with profiles** - Easier than maintaining multiple config files
2. **Use `--debug`** - See what config is actually being loaded
3. **Test voices first** - Run `test_voices_fixed.py` to find your favorites
4. **Adjust pitch and speed** - Each voice sounds better at different settings
5. **Save good configs** - Use `--save` to persist your favorite tweaks
6. **Use `status` command** - Check control file paths for manual IPC
7. **Runtime control** - Use `switch`/`tts`/`stt`/`modify` to adjust without restarting
8. **Per-window instances** - Run separate instances for different Claude Code windows

---

## Troubleshooting

### Voice injector not working

Make sure:
1. PyAgentVox is running first (creates temp files)
2. Claude Code window is in focus when voice injector starts
3. Python dependencies are installed (pynput for keyboard automation)

### TTS not working

Check:
1. PyAgentVox is running with correct config
2. TTS monitor is running and watching the right file
3. Edge TTS can access the internet (requires connection)

### Config not loading

Debug with:
```bash
python -m pyagentvox start --debug
```

Look for config loading messages:
- `[Config] Loading: config.yaml`
- `[Config] Loading profile: male_voices`
- `[Config] Applying overrides: {...}`

### Instance already running

If you get "already running" error:
```bash
# Check status
python -m pyagentvox status

# Stop existing instance
python -m pyagentvox stop

# If stale lock, remove manually:
# Windows: del %TEMP%\pyagentvox_*.pid
# Unix: rm /tmp/pyagentvox_*.pid
```

### Testing voices

Use the test script to hear all available voices:
```bash
cd /path/to/pyagentvox
uv run python test_voices_fixed.py
```

---

## Examples

### Example 1: Quick voice change

```bash
# Try Guy (male) voice temporarily
python -m pyagentvox start --set "neutral.voice=en-US-GuyNeural"

# Like it? Save it
python -m pyagentvox start --set "neutral.voice=en-US-GuyNeural" --save
```

### Example 2: Create a new profile

Edit `config.yaml`:
```yaml
profiles:
  my_profile:
    neutral:
      voice: "en-US-GuyNeural"
      speed: "+5%"
      pitch: "+0Hz"
    cheerful:
      voice: "en-US-JasonNeural"
      speed: "+15%"
      pitch: "+8Hz"
```

Then use it:
```bash
python -m pyagentvox start --profile my_profile
```

### Example 3: Programmatic usage with overrides

```python
from pyagentvox import run

# Load base config, apply profile, override one value
run(
    config_path='config.yaml',
    profile='male_voices',
    config_overrides={
        'calm': {
            'pitch': '-10Hz'  # Make calm voice deeper
        }
    },
    debug=True
)
```

### Example 4: Background mode with monitoring

```bash
# Start in background with logging
python -m pyagentvox start --background --log-file pyagentvox.log

# Monitor logs in another terminal
tail -f pyagentvox.log

# Control while running in background
python -m pyagentvox switch male_voices
python -m pyagentvox tts off

# Stop when done
python -m pyagentvox stop
```

---

## Getting Help

- Run `python -m pyagentvox --help` for CLI options
- Check `config.yaml` for voice reference and examples
- Use `--debug` to see what's happening
- Test voices with `test_voices_fixed.py`
- Use `status` command to inspect control files

Enjoy your voice-enabled AI conversations! 🎤✨
