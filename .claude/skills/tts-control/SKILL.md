---
name: tts-control
description: Toggle PyAgentVox text-to-speech output on or off without restarting. Use when user mentions noise, wants silence, or wants to re-enable voice output.
argument-hint: "on|off"
---

# TTS Control

Enable or disable text-to-speech output at runtime without restarting PyAgentVox.

## Usage

```bash
/tts-control [on|off]
```

## Examples

- `/tts-control on` - Enable text-to-speech (default)
- `/tts-control off` - Disable text-to-speech (silent mode, text only)

## Notes

- PyAgentVox must be running (`/voice`)
- Changes take effect immediately
- Text is still queued even when TTS is off
- Use `/stt-control` to control speech recognition separately
