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
- Command-line options and configuration
- Config file formats and profiles
- Available voices with descriptions
- Programmatic usage (Python API)
- Advanced features and tips

## Quick Reference

### Basic Usage

```bash
# Run with default settings
pyagentvox

# Run with debug logging
pyagentvox --debug

# Use a specific config file
pyagentvox --config my_config.yaml

# Use a config profile
pyagentvox --profile michelle

# TTS-only mode (disable speech recognition)
pyagentvox --tts-only
```

### Voice Commands

While PyAgentVox is running:

- **"stop listening"** - Stops PyAgentVox without sending message to AI

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

warm:
  voice: "en-US-EmmaNeural"
  speed: "+8%"
  pitch: "+18Hz"

calm:
  voice: "en-GB-SoniaNeural"
  speed: "+0%"
  pitch: "-2Hz"

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
    emotions:
      neutral:
        speed: "-10%"  # Slower for testing
```

#### Example pyagentvox.json

```json
{
  "stt": {
    "energy_threshold": 4000
  },
  "emotions": {
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
  },
  "profiles": {
    "male_voices": {
      "emotions": {
        "neutral": {
          "voice": "en-US-GuyNeural"
        }
      }
    }
  }
}
```

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

## Command-Line Options

### Basic Options

```bash
# Show help
pyagentvox --help

# Enable debug logging
pyagentvox --debug

# Write logs to file
pyagentvox --log-file pyagentvox.log
```

### Config Options

```bash
# Use specific config file
pyagentvox --config /path/to/config.yaml

# Load a profile from config
pyagentvox --profile male_voices

# Override specific config values
pyagentvox --set warm.pitch=+20Hz

# Override multiple values
pyagentvox --set warm.pitch=+20Hz --set cheerful.speed=+25%

# Save overrides back to config file
pyagentvox --set warm.pitch=+20Hz --save
```

### Background Mode

**NEW in v0.2.0!** Run PyAgentVox as a background process (Windows only):

```bash
# Run in background with default config
pyagentvox --background

# Run in background with profile and logging
pyagentvox --background --profile male_voices --log-file pyagentvox.log

# Run in background with debug mode
pyagentvox --background --debug --log-file debug.log
```

**How It Works:**
- Launches PyAgentVox as a detached process
- No console window appears
- Returns immediately with process ID
- All output redirected to log file (use `--log-file`)

**Stopping Background Process:**
```bash
# Use Task Manager, or:
taskkill /PID 12345  # Replace with actual PID
```

**Important Notes:**
- Only supported on Windows (requires `CREATE_NO_WINDOW` flag)
- Use `--log-file` to capture output when running in background
- Process ID is displayed when launched
- Use `--debug --log-file debug.log` for troubleshooting background processes

### Config Override Syntax

**New in v0.3.0:** Space-separated key=value pairs!

```bash
# Set multiple values at once (space-separated)
pyagentvox --set "neutral.voice=michelle speed=10 pitch=-5"

# Shorthands apply to all emotions
pyagentvox --set "speed=15"  # Sets speed=+15% for all emotions
pyagentvox --set "voice=jenny"  # Sets voice to Jenny for all emotions

# Modify existing values (adds to current)
pyagentvox --modify "speed=5 pitch=-3"  # Adds +5 to speed, -3 to pitch

# Combine --set and --modify
pyagentvox --set "voice=jenny" --modify "speed=10"
```

**Shorthands:**
- `speed=10` → Applies to all emotions
- `pitch=+5Hz` → Applies to all emotions
- `voice=jenny` → Applies to all emotions (resolved to full voice ID)

**Voice name shortcuts:**
- michelle, jenny, emma, aria, ava, sonia, libby, maisie (female)
- guy, davis, tony, jason, ryan, thomas (male)

Values are auto-normalized:
- Numbers → `10` becomes `+10%` or `+10Hz`
- Voice names → `jenny` becomes `en-US-JennyNeural`

## Profiles

Profiles let you store multiple config variations in a single file.

### Defining Profiles

In your `config.yaml`:

```yaml
# Base config
emotions:
  neutral:
    voice: "en-US-MichelleNeural"
    speed: "+10%"
    pitch: "+10Hz"

# Profiles (alternative configurations)
profiles:
  # Profile: male_voices
  male_voices:
    emotions:
      neutral:
        voice: "en-US-GuyNeural"
        pitch: "+0Hz"
      cheerful:
        voice: "en-US-JasonNeural"

  # Profile: high_energy
  high_energy:
    emotions:
      neutral:
        speed: "+20%"
        pitch: "+15Hz"
      cheerful:
        speed: "+30%"
        pitch: "+20Hz"

  # Profile: debug (slower for testing)
  debug:
    emotions:
      neutral:
        speed: "-10%"
```

### Using Profiles

```bash
# Load the "male_voices" profile
pyagentvox --profile male_voices

# Load profile and override specific values
pyagentvox --profile male_voices --set calm.voice=en-GB-RyanNeural
```

**How profiles work:**
1. Base config is loaded
2. Profile overrides are applied (recursively merged)
3. CLI overrides are applied last

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
```

### With Config Dictionary

```python
from pyagentvox import run

config = {
    'emotions': {
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
}

run(config=config)
```

### With Config Overrides

```python
from pyagentvox import run

# Load config and apply overrides
overrides = {
    'emotions': {
        'warm': {
            'pitch': '+25Hz'
        }
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
    'emotions': {
        'neutral': {'voice': 'en-US-GuyNeural'}
    }
}

agent = PyAgentVox(config=config)

# Run the agent
asyncio.run(agent.run())
```

## Auto-Injection of Voice Instructions

**NEW in v0.2.0!** PyAgentVox now automatically injects voice usage instructions into your CLAUDE.md file when started.

### How It Works

1. When PyAgentVox starts, it searches for CLAUDE.md in:
   - Current directory
   - Parent directory
   - Claude Code project directory (via `~/.claude/projects/*/sessions-index.json`)

2. Injects voice instructions wrapped in HTML comment markers:
   ```markdown
   <!-- PYAGENTVOX_START -->
   # Voice System (PyAgentVox Active)
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
from pyagentvox import claude_md_manager

# Inject instructions
claude_md_manager.inject_voice_instructions()

# Remove instructions
claude_md_manager.remove_voice_instructions()

# Use custom CLAUDE.md path
from pathlib import Path
claude_md_manager.inject_voice_instructions(Path("/path/to/CLAUDE.md"))
```

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
pyagentvox --debug
```

Look for config loading messages:
- `[Config] Loading: config.yaml`
- `[Config] Loading profile: male_voices`
- `[Config] Applying overrides: {...}`

### Testing voices

Use the test script to hear all available voices:
```bash
cd /path/to/pyagentvox
uv run python test_voices_fixed.py
```

## Advanced Features

### Custom Config Locations

```bash
# Use config in project directory
cd my-project
echo '{"emotions": {"neutral": {"voice": "en-US-GuyNeural"}}}' > pyagentvox.json
pyagentvox  # Auto-detects pyagentvox.json

# Or specify path
pyagentvox --config /path/to/my-config.yaml
```

### Persistent Overrides

Save CLI overrides back to config:
```bash
# Test a change
pyagentvox --set warm.pitch=+25Hz

# Like it? Save it permanently
pyagentvox --set warm.pitch=+25Hz --save
```

### Multiple Profiles

Create workflow-specific profiles:

```yaml
profiles:
  development:
    emotions:
      neutral:
        speed: "-10%"  # Slower for clarity

  presentation:
    emotions:
      neutral:
        speed: "+15%"  # Faster and energetic
        pitch: "+10Hz"

  late_night:
    emotions:
      neutral:
        voice: "en-GB-SoniaNeural"  # Calm British voice
        speed: "+0%"
        pitch: "-5Hz"
```

Then switch between them:
```bash
pyagentvox --profile development
pyagentvox --profile presentation
pyagentvox --profile late_night
```

## Tips & Best Practices

1. **Start with profiles** - Easier than maintaining multiple config files
2. **Use --debug** - See what config is actually being loaded
3. **Test voices first** - Run `test_voices_fixed.py` to find your favorites
4. **Adjust pitch and speed** - Each voice sounds better at different settings
5. **Save good configs** - Use `--save` to persist your favorite tweaks

## Examples

### Example 1: Quick voice change

```bash
# Try Guy (male) voice temporarily
pyagentvox --set neutral.voice=en-US-GuyNeural

# Like it? Save it
pyagentvox --set neutral.voice=en-US-GuyNeural --save
```

### Example 2: Create a new profile

Edit `config.yaml`:
```yaml
profiles:
  my_profile:
    emotions:
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
pyagentvox --profile my_profile
```

### Example 3: Programmatic usage with overrides

```python
from pyagentvox import run

# Load base config, apply profile, override one value
run(
    config_path='config.yaml',
    profile='male_voices',
    config_overrides={
        'emotions': {
            'calm': {
                'pitch': '-10Hz'  # Make calm voice deeper
            }
        }
    },
    debug=True
)
```

## Getting Help

- Run `pyagentvox --help` for CLI options
- Check `config.yaml` for voice reference and examples
- Use `--debug` to see what's happening
- Test voices with `test_voices_fixed.py`

Enjoy your voice-enabled AI conversations! 🎤✨
