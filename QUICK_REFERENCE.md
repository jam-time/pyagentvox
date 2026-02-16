# PyAgentVox Quick Reference

One-page cheat sheet for voice communication with Claude Code.

---

## 🚀 Quick Start

### Skills (Recommended)
```bash
/voice              # Start with default voice
/voice michelle     # Start with Michelle voice
/voice jenny debug  # Jenny voice + debug logging
/voice tts-only     # Voice output only (no mic)
/voice-stop         # Stop voice chat
```

### Direct CLI
```bash
python -m pyagentvox start              # Start with defaults
python -m pyagentvox start --debug      # With debug logging
python -m pyagentvox stop               # Stop running instance
python -m pyagentvox status             # Check status
```

---

## 📋 Subcommands

| Command | Description |
|---------|-------------|
| `start` | Start PyAgentVox with options |
| `stop` | Stop running instance |
| `switch <profile>` | Switch voice profile on-the-fly |
| `tts [on\|off]` | Enable/disable text-to-speech |
| `stt [on\|off]` | Enable/disable speech recognition |
| `modify <setting>` | Adjust pitch/speed at runtime |
| `status` | Show running status |

---

## 🎭 Skills Reference

### `/voice [profile] [modes...]`
Start voice communication. Combine profiles with modes:
- **Profiles:** `michelle`, `jenny`, `emma`, `aria`, `ava`, `sonia`, `libby`
- **Modes:** `debug`, `tts-only`, `custom`
- **Examples:**
  - `/voice michelle tts-only` - Michelle voice, no microphone
  - `/voice jenny debug` - Jenny voice with debug logs

### `/voice-stop`
Stop PyAgentVox and clean up. Or say "stop listening".

### `/voice-switch <profile>`
Hot-swap voice profiles without restarting:
- **Michelle** - Sweet, empathetic (debugging frustrations)
- **Jenny** - Energetic, playful (celebrations)
- **Emma** - Warm, nurturing (patient explanations)
- **Aria** - Professional, confident (presentations)
- **Ava** - Clear, precise (technical discussions)
- **Sonia** - Calm, professional (focused work)
- **Libby** - Friendly, approachable (collaboration)

### `/tts-control [on|off]`
Enable/disable text-to-speech output at runtime.

### `/stt-control [on|off]`
Enable/disable speech recognition at runtime.

### `/voice-modify <setting>`
Adjust voice settings on-the-fly:
- **Global:** `pitch=+5`, `speed=-10`
- **Per-emotion:** `neutral.pitch=+10`, `cheerful.speed=-5`
- **All emotions:** `all.pitch=+3`, `all.speed=-15`

---

## 🎭 Emotion Tags

Control voice dynamically in Claude responses:

| Tag | Voice Style |
|-----|-------------|
| `[neutral]` | Default, balanced |
| `[cheerful]` | Happy, upbeat |
| `[excited]` | Very enthusiastic |
| `[empathetic]` | Caring, understanding |
| `[warm]` | Gentle, kind |
| `[calm]` | Professional, relaxed |
| `[focused]` | Concentrated, steady |

**Usage:** `[excited] Bug fixed! [calm] Let me explain the solution...`

---

## ⚙️ Common CLI Patterns

### Start with Options
```bash
# Basic
python -m pyagentvox start --debug
python -m pyagentvox start --tts-only
python -m pyagentvox start --profile michelle

# Configuration
python -m pyagentvox start --config my_config.yaml
python -m pyagentvox start --set "neutral.speed=+10 neutral.pitch=+5"
python -m pyagentvox start --modify "speed=+5 pitch=-3"
python -m pyagentvox start --save  # Save changes

# Logging
python -m pyagentvox start --log-file vox.log
python -m pyagentvox start --background --log-file vox.log  # Windows only
```

### Runtime Control
```bash
# Switch profiles
python -m pyagentvox switch michelle

# Toggle features
python -m pyagentvox tts off
python -m pyagentvox stt on

# Adjust voice
python -m pyagentvox modify pitch=+5
python -m pyagentvox modify neutral.speed=-10

# Check status
python -m pyagentvox status

# Stop
python -m pyagentvox stop
```

---

## 📁 Temp Files

PyAgentVox uses temp files for IPC:

| File | Purpose |
|------|---------|
| `%TEMP%\agent_output_*.txt` | STT output (your speech) |
| `%TEMP%\agent_input_*.txt` | TTS input (text to speak) |
| `%TEMP%\agent_profile_*.txt` | Profile switch control |
| `%TEMP%\agent_tts_*.txt` | TTS enable/disable |
| `%TEMP%\agent_stt_*.txt` | STT enable/disable |
| `%TEMP%\agent_modify_*.txt` | Runtime voice adjustments |
| `%TEMP%\pyagentvox_v2.pid` | Single-instance lock |

**Monitor:** `dir %TEMP%\agent_*.txt` (Windows) or `ls /tmp/agent_*.txt` (Unix)

---

## 🐛 Quick Troubleshooting

### Already Running
```bash
python -m pyagentvox stop
# OR manually:
kill $(cat /tmp/pyagentvox_v2.pid)  # Unix
taskkill /PID <pid>                 # Windows
```

### No Audio Output
1. Check internet connection (Edge TTS requires online)
2. Verify temp file: `dir %TEMP%\agent_input_*.txt`
3. Test manual write: `echo Test > %TEMP%\agent_input_*.txt`
4. Try: `python -m pyagentvox tts on`

### Speech Not Recognized
1. Check microphone permissions
2. Verify temp file: `dir %TEMP%\agent_output_*.txt`
3. Lower energy threshold in config: `stt.energy_threshold: 2000`
4. Try: `python -m pyagentvox stt on`

### Profile Not Switching
```bash
python -m pyagentvox status  # Check current profile
python -m pyagentvox switch michelle --debug
# OR restart:
python -m pyagentvox stop && python -m pyagentvox start --profile michelle
```

### Multiple Instances
```bash
# Windows
tasklist | findstr python
taskkill /F /PID <pid>

# Unix
pkill -f pyagentvox
```

---

## ⚙️ Config File Quick Example

```yaml
# pyagentvox.yaml
neutral:
  voice: "en-US-MichelleNeural"
  speed: "+10%"
  pitch: "+10Hz"

cheerful:
  voice: "en-US-JennyNeural"
  speed: "+15%"
  pitch: "+8Hz"

stt:
  energy_threshold: 4000  # Lower = more sensitive

profiles:
  my_profile:
    neutral:
      voice: "en-US-GuyNeural"
      speed: "+5%"
      pitch: "+0Hz"
```

---

## 💡 Pro Tips

1. **Debug mode is your friend:** `python -m pyagentvox start --debug` shows everything
2. **Hot-swap profiles:** Use `/voice-switch` to match conversation mood
3. **Test standalone first:** `python -m pyagentvox start --debug` before integrating
4. **Remote work:** Use `--tts-only` when you can't use a microphone
5. **Monitor temp files:** Check `%TEMP%\agent_*.txt` when debugging
6. **Adjust sensitivity:** Lower `stt.energy_threshold` for quieter environments
7. **Combine modes:** `/voice michelle tts-only debug` for maximum control
8. **Save your tweaks:** Use `--save` after `--set` or `--modify` to persist changes

---

## 📖 More Documentation

- **[README.md](README.md)** - Project overview and quick start
- **[SETUP.md](SETUP.md)** - Complete setup guide with architecture
- **[USAGE.md](USAGE.md)** - Detailed CLI options and configuration
- **[AGENTS.md](AGENTS.md)** - Guide for AI assistants
- **[CLAUDE.md](CLAUDE.md)** - Project instructions and code style
