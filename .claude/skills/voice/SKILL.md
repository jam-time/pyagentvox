---
name: voice
description: Start PyAgentVox voice communication for this session. Use when enabling voice output (TTS) or full two-way voice interaction (TTS + speech recognition). Arguments: optional profile name (michelle, jenny, emma, aria, ava, sonia, libby) and/or modes (tts-only, debug, custom).
disable-model-invocation: true
argument-hint: "[profile] [tts-only|debug|custom]"
---

# Voice Chat Skill

Start PyAgentVox voice communication system for two-way voice interaction with Claude.

## What This Does

Launches PyAgentVox which:
- **Listens** to your microphone continuously
- **Types** recognized speech into Claude Code automatically
- **Speaks** Claude's responses aloud with emotion-based voices
- **Monitors** Claude Code conversation files for responses

## Usage

```bash
/voice [profile] [modes...]
```

You can now **combine** profiles with modes!

## Options

### Voice Profiles
```bash
/voice                    # Default (Ava voice)
/voice michelle           # Michelle voice (sweet, empathetic)
/voice jenny              # Jenny voice (energetic, playful)
/voice emma               # Emma voice (warm, nurturing)
/voice aria               # Aria voice (professional, confident)
/voice ava                # Ava voice (clear, precise)
/voice sonia              # Sonia voice (British, calm)
/voice libby              # Libby voice (British, friendly)
```

### Special Modes
```bash
/voice tts-only           # Voice output only (no speech recognition)
/voice debug              # Run with debug logging
/voice custom             # Use pyagentvox.yaml from current directory
```

### Combined Usage (NEW!)
```bash
/voice michelle tts-only  # Michelle voice, no microphone
/voice jenny debug        # Jenny voice with debug logging
/voice emma tts-only debug # Emma voice, no mic, with debug logs
/voice tts-only debug     # Default voice, no mic, debug mode
```

## What Happens When You Run This

1. **PyAgentVox starts** in background with selected profile
2. **Voice injector launches** automatically (types speech into Claude Code, unless tts-only)
3. **TTS monitor starts** automatically (watches for Claude's responses)
4. **You can start talking** immediately! (unless tts-only mode)

## Examples

```bash
# Working from home - full voice interaction with Michelle
/voice michelle

# In a coffee shop - can't use mic, just want to hear responses
/voice jenny tts-only

# Debugging issues with Emma voice
/voice emma debug

# Testing custom config with no microphone
/voice custom tts-only

# Maximum logging for troubleshooting
/voice debug tts-only
```

## Stopping Voice Chat

```bash
/voice-stop
```

Or say: **"stop listening"**

## Emotion Tags

Claude can use these tags to change voice dynamically:

- `[neutral]` - Default, balanced
- `[cheerful]` - Happy, upbeat
- `[excited]` - Very enthusiastic
- `[empathetic]` - Caring, understanding
- `[warm]` - Gentle, kind
- `[calm]` - Professional, relaxed
- `[focused]` - Concentrated, steady

Example: `[excited] I found it! [calm] Let me explain...`

## Troubleshooting

**Already running error:**
```bash
/voice-stop
# Wait 2 seconds, then:
/voice michelle
```

**No audio output:**
- Check internet connection (Edge TTS requires online)
- Verify microphone permissions

**Speech not recognized:**
- Check microphone is working
- Adjust volume/positioning
- Try `/voice debug` to see what's happening

## Requirements

- Python 3.10+
- Windows (voice injector uses keyboard automation)
- Internet connection (for TTS and speech recognition)
- Microphone
