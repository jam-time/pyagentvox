# .claude Directory

Configuration and utilities for Claude Code workspace.

## Voice Chat System 🎤

**Quick Start:**
```bash
/voice              # Start with default voice profile
/voice michelle     # Start with Michelle voice
/voice debug        # Start with debug logging
/voice-stop         # Stop voice chat
```

**Skills:**
- `/voice [profile|debug|tts-only]` - Start PyAgentVox with options
- `/voice-switch <profile>` - Switch voice profiles on the fly (NEW!)
- `/voice-stop` - Stop PyAgentVox cleanly

**Available Profiles:** michelle, jenny, emma, aria, ava

**Hot-Swap Profiles (Runtime):**
```bash
# Switch profile without restarting
python -m pyagentvox --switch michelle
python -m pyagentvox --switch jenny

# Or use manual control file method
echo jenny > %TEMP%\agent_profile_<pid>.txt
```
Profile switches after current TTS finishes - no interruption to active speech!

## How Voice Chat Works

```
You speak → PyAgentVox (STT) → Types into Claude Code
                                    ↓
                        Luna responds with text
                                    ↓
                    TTS Monitor captures response
                                    ↓
                                PyAgentVox (TTS)
                                    ↓
                            You hear Luna! 🔊
```

## Emotion Tags

When voice chat is active, Luna can use emotion tags to switch voices mid-response:

- `[neutral]` - Default, balanced
- `[cheerful]` - Happy, upbeat
- `[excited]` - Very enthusiastic
- `[empathetic]` - Caring, understanding
- `[warm]` - Gentle, kind
- `[calm]` - Professional, relaxed
- `[focused]` - Concentrated, steady

## Directory Structure

```
.claude/
├── README.md                   # This file
├── settings.local.json         # Local Claude Code settings
├── docs/                       # Project documentation
│   ├── style-guide.md          # Python style standards
│   ├── patterns.md             # Async, error handling patterns
│   └── testing.md              # Testing best practices
├── hooks/                      # Event hooks
│   └── hooks.json              # Hook configuration
└── skills/                     # Custom skills
    ├── voice/                  # /voice skill
    │   ├── skill.md
    │   └── voice.sh
    └── voice-stop/             # /voice-stop skill
        ├── skill.md
        └── voice-stop.sh
```

## Hooks

Hooks are configured in `hooks/hooks.json` and run automatically on events.

## Documentation

- **[CLAUDE.md](../CLAUDE.md)** - Main project instructions for Claude
- **[Style Guide](docs/style-guide.md)** - Core Python coding standards
- **[Patterns](docs/patterns.md)** - Advanced patterns (async, error handling)
- **[Testing](docs/testing.md)** - Testing patterns and best practices

---

Need help? Check the docs or ask Luna! 🌙✨
