# PyAgentVox Quick Reference

## 🚀 Getting Started

### Using Skills (Recommended)
```bash
/voice              # Start with default voice
/voice michelle     # Start with Michelle voice
/voice jenny        # Start with Jenny voice
/voice-stop         # Stop voice chat
```

### Direct Commands
```bash
# Test standalone
python -m pyagentvox --debug

# Try voice profiles
python -m pyagentvox --profile michelle
python -m pyagentvox --profile jenny

# TTS-only mode
python -m pyagentvox --tts-only
```

## 🎤 Voice Commands & Behavior

| Command/Feature | Action |
|---------|--------|
| "stop listening" | Stops PyAgentVox |
| Auto-pause (10 min) | STT pauses after 10 minutes idle |
| Auto-resume (on TTS) | STT resumes when AI responds |

## ⚙️ CLI Options

### Basic
```bash
python -m pyagentvox                    # Run with defaults
python -m pyagentvox --debug            # Debug logging
python -m pyagentvox --tts-only         # TTS only (no microphone)
python -m pyagentvox --log-file vox.log # Write logs to file
```

### Configuration
```bash
python -m pyagentvox --config my_config.yaml       # Use specific config
python -m pyagentvox --profile michelle            # Load profile
python -m pyagentvox --set "speed=15 pitch=5"      # Override values
python -m pyagentvox --modify "speed=+5 pitch=-3"  # Modify values
python -m pyagentvox --save                        # Save overrides
```

### Background Mode (Windows)
```bash
python -m pyagentvox --background --log-file vox.log
taskkill /PID <pid>  # Stop
```

## 🎭 Emotion Tags

| Tag | Voice Style |
|-----|-------------|
| `[neutral]` | Default, balanced |
| `[cheerful]` | Happy, upbeat |
| `[excited]` | Very enthusiastic |
| `[empathetic]` | Caring, understanding |
| `[warm]` | Gentle, kind |
| `[calm]` | Professional, relaxed |
| `[focused]` | Concentrated, steady |

**Usage in Claude responses:**
```
[excited] I found the bug! [calm] Let me explain the fix...
```

## 🔊 Available Voice Profiles

### Female Voices
- `michelle` - Balanced, versatile
- `jenny` - Energetic, upbeat
- `emma` - Warm, caring
- `aria` - Professional, bright
- `ava` - Clear, precise

### British Voices
- `sonia` - Calm, professional
- `libby` - Friendly
- `maisie` - Young, bright

## 📁 Temp Files

PyAgentVox creates temp files for communication:

| File | Purpose |
|------|---------|
| `/tmp/agent_output_*.txt` | STT output (your speech) |
| `/tmp/agent_input_*.txt` | TTS input (text to speak) |
| `/tmp/pyagentvox_v2.pid` | Single-instance lock |

## 🐛 Quick Troubleshooting

### Already running error
```bash
kill $(cat /tmp/pyagentvox_v2.pid)
rm /tmp/pyagentvox_v2.pid
```

### No audio output
1. Check internet connection
2. Verify temp file exists: `ls /tmp/agent_input_*.txt`
3. Test manual write: `echo "Test" > /tmp/agent_input_*.txt`

### Speech not recognized
1. Check microphone permissions
2. Verify temp file exists: `ls /tmp/agent_output_*.txt`
3. Try lower energy threshold in config

### Multiple instances
```bash
pkill -f pyagentvox
```

## ⚙️ Config File Quick Example

```yaml
# Simple config (pyagentvox.yaml)
neutral:
  voice: "en-US-MichelleNeural"
  speed: "+10%"
  pitch: "+10Hz"

cheerful:
  voice: "en-US-JennyNeural"
  speed: "+15%"
  pitch: "+8Hz"

# Profiles
profiles:
  my_profile:
    neutral:
      voice: "en-US-GuyNeural"
      speed: "+5%"
      pitch: "+0Hz"
```

## 📖 Full Documentation

**For Users:**
- **[SETUP.md](SETUP.md)** - Complete setup guide with architecture
- **[USAGE.md](USAGE.md)** - Detailed CLI options and configuration
- **[README.md](README.md)** - Overview and quick start

**For AI Agents:**
- **[AGENTS.md](AGENTS.md)** - Guide for AI assistants setting up voice for their humans

## 💡 Pro Tips

1. Start with `--debug` to see what's happening
2. Use `--profile` instead of manual voice config
3. Test standalone before integrating with Claude
4. Use `--tts-only` when working remotely
5. Check `/tmp/agent_*.txt` files when debugging
