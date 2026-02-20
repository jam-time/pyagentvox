# PyAgentVox Autonomous Setup

Zero-interaction setup instructions for AI agents. Follow these steps exactly to install and run PyAgentVox.

## Prerequisites

- Python 3.12+
- Windows OS (voice injection requires pywin32)
- Microphone and internet connection

## Setup Steps

### Step 1 (Optional): Install uv

Skip this step if `uv` is already installed.

```bash
# Check if uv is available
uv --version
```

If uv is not installed:

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

```bash
# Unix/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step 2: Initialize Project

If the target directory has no `pyproject.toml`:

```bash
uv init
```

### Step 3: Install PyAgentVox

```bash
uv add git+https://github.com/jam-time/pyagentvox.git
```

Or with pip:

```bash
pip install git+https://github.com/jam-time/pyagentvox.git
```

### Step 4: Run Autonomous Setup

```bash
python -m pyagentvox setup
```

This single command:

1. Generates `pyagentvox.yaml` in the current directory (Ava voice with all profiles)
2. Installs all 6 Claude Code skills to `~/.claude/skills/`
3. Patches skill scripts with the correct installation path
4. Validates dependencies and configuration

To overwrite existing files:

```bash
python -m pyagentvox setup --force
```

### Step 5: Start PyAgentVox

```bash
python -m pyagentvox start
```

With a specific voice profile:

```bash
python -m pyagentvox start --profile michelle
```

In background mode (no console window):

```bash
python -m pyagentvox start --background
```

TTS-only mode (no microphone required):

```bash
python -m pyagentvox start --tts-only
```

## Full Automated Script (Copy-Paste)

Run this entire block for a complete zero-interaction setup:

```bash
uv add git+https://github.com/jam-time/pyagentvox.git
python -m pyagentvox setup
python -m pyagentvox start
```

## What Gets Installed

### Config File: `pyagentvox.yaml`

Generated in the current working directory. Contains:

- Default voice: Ava (en-US-AvaNeural)
- 7 emotion mappings: neutral, cheerful, excited, empathetic, warm, calm, focused
- 7 voice profiles: default, michelle, jenny, emma, aria, ava, sonia, libby
- STT settings (microphone energy threshold)

### Claude Code Skills: `~/.claude/skills/`

| Skill | Slash Command | Description |
|-------|---------------|-------------|
| voice | `/voice [profile] [modes]` | Start PyAgentVox |
| voice-stop | `/voice-stop` | Stop PyAgentVox |
| voice-switch | `/voice-switch <profile>` | Switch voice at runtime |
| voice-modify | `/voice-modify <setting>` | Adjust pitch/speed at runtime |
| tts-control | `/tts-control on\|off` | Toggle text-to-speech |
| stt-control | `/stt-control on\|off` | Toggle speech recognition |

Shell scripts are automatically patched with the correct PyAgentVox installation path.

## Available Voice Profiles

| Profile | Description |
|---------|-------------|
| default | Fun, energetic, playful (Ava) |
| michelle | Sweet, empathetic, caring |
| jenny | Energetic and caring, happy medium |
| emma | Warm, nurturing, understanding |
| aria | Balanced, neutral voice |
| ava | Fun, energetic, playful |
| sonia | Formal British voice |
| libby | Friendly, casual British voice |

## Verification

```bash
# Validate setup
python -m pyagentvox setup

# Check running status
python -m pyagentvox status
```

## Troubleshooting

### Missing dependencies

```bash
pip install edge-tts pygame pyaudio speechrecognition psutil pywin32 pyyaml mutagen accelerate
```

### Skills not installed

```bash
python -m pyagentvox setup --force
```

### Already running

```bash
python -m pyagentvox stop
python -m pyagentvox start
```

## Post-Setup Commands

```bash
# Start with default voice
python -m pyagentvox start

# Start with profile
python -m pyagentvox start --profile michelle

# Start in background
python -m pyagentvox start --background

# Start TTS only (no mic)
python -m pyagentvox start --tts-only

# Stop
python -m pyagentvox stop

# Switch voice at runtime
python -m pyagentvox switch jenny

# Check status
python -m pyagentvox status
```
