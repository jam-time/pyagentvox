---
name: voice-stop
description: Stop PyAgentVox voice communication. Use when the user wants to stop voice output or microphone listening.
disable-model-invocation: true
---

# Voice Stop Skill

Stop the running PyAgentVox voice communication system.

## Usage

```bash
/voice-stop
```

## What This Does

1. Finds the running PyAgentVox process
2. Terminates it cleanly
3. Removes voice instructions from CLAUDE.md
4. Cleans up temp files and lock files

## Alternative

You can also say "stop listening" while PyAgentVox is running.
