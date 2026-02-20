---
name: stt-control
description: Toggle PyAgentVox speech-to-text (microphone) on or off without restarting. Use when user wants to stop or resume speaking to Claude via microphone.
argument-hint: "on|off"
---

# STT Control

Enable or disable speech recognition (speech-to-text) at runtime without restarting PyAgentVox.

## Usage

```bash
/stt-control [on|off]
```

## Examples

- `/stt-control on` - Enable speech recognition (default)
- `/stt-control off` - Disable speech recognition (keyboard input only)

## Notes

- PyAgentVox must be running (`/voice`)
- Changes take effect immediately
- When off, you can only type messages (no voice input)
- Use `/tts-control` to control text-to-speech separately
- Not applicable in TTS-only mode (`/voice tts-only`)
