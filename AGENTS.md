# PyAgentVox Setup Guide for AI Agents

**For AI Assistants:** This guide explains how to set up PyAgentVox voice communication for your human user.

## 🎯 What is PyAgentVox?

PyAgentVox enables **two-way voice communication** between you (the AI) and your human:
- **Human speaks** → Text appears in conversation automatically
- **You respond** → Your text is spoken aloud with emotion-based voices
- **You control voice** → Use emotion tags like `[cheerful]` or `[calm]` to change voice dynamically

## 🚀 Quick Setup (For Your Human's Project)

### Prerequisites Check

Before starting, verify your human has:
- Python 3.12+ installed
- Windows OS (voice injector requires win32gui)
- Microphone connected
- Internet connection (for TTS and speech recognition)

### Step 1: Install PyAgentVox

Guide your human through installation:

```bash
# Clone or navigate to pyagentvox directory
cd /path/to/pyagentvox

# Install dependencies
uv pip install -e .
# OR
pip install -e .
```

### Step 2: Test PyAgentVox Standalone

Before integrating with your conversation system, test that it works:

```bash
# Run with debug to see what's happening
python -m pyagentvox --debug

# Your human should see:
#   ✓ Voice Injector started
#   ✓ TTS Monitor started
#   ✓ Voice recognition ready!

# Test by having them speak - text should appear in output file
# Test TTS by writing to input file:
echo "Hello! [cheerful] This is a test!" > /tmp/agent_input_*.txt
```

### Step 3: Create Voice Skills (Recommended)

If your conversation platform supports skills/commands, create voice control skills:

**File: `.claude/skills/voice/skill.md`** (example for Claude Code)
```markdown
# Voice Chat Skill

Start PyAgentVox for voice communication.

## Usage
/voice [profile]

## Profiles
michelle, jenny, emma, aria, ava, sonia, libby, maisie
```

**File: `.claude/skills/voice/voice.sh`**
```bash
#!/bin/bash
PROFILE="${1:-michelle}"
cd /path/to/pyagentvox
uv run python -m pyagentvox --profile "$PROFILE" > /tmp/pyagentvox.log 2>&1 &
echo "Voice chat started!"
```

Make executable:
```bash
chmod +x .claude/skills/voice/voice.sh
```

### Step 4: Inject Voice Instructions

PyAgentVox automatically injects voice usage instructions into your project's instruction file (e.g., CLAUDE.md):

```markdown
<!-- PYAGENTVOX_START -->
# Voice Output Active 🎤

Your responses are **spoken aloud**. Control voice with emotion tags:

**Available emotions:** [neutral] [cheerful] [excited] [empathetic] [warm] [calm] [focused]

**Usage:** [excited] I found it! [calm] Let me explain...
<!-- PYAGENTVOX_END -->
```

This happens automatically when PyAgentVox starts. The instructions are removed when it stops.

### Step 5: Start Voice Communication

From your conversation interface:

```bash
# Using skill (if created)
/voice michelle

# OR manually
cd /path/to/pyagentvox
python -m pyagentvox --profile michelle
```

That's it! Voice communication is now active.

## 🎭 Using Emotion Tags in Your Responses

As an AI agent, you can control voice dynamically using emotion tags:

### Basic Usage

```markdown
[neutral] I've analyzed the code.
[excited] Found the bug! It's in line 42.
[calm] Here's how to fix it...
```

### Tag Reference

| Tag | Voice Style | When to Use |
|-----|-------------|-------------|
| `[neutral]` | Balanced, default | General explanations, factual info |
| `[cheerful]` | Happy, upbeat | Positive news, greetings |
| `[excited]` | Very enthusiastic | Discoveries, breakthroughs, "aha!" moments |
| `[empathetic]` | Caring, understanding | Errors, debugging, user struggles |
| `[warm]` | Gentle, kind | Encouragement, support |
| `[calm]` | Professional, relaxed | Technical details, step-by-step instructions |
| `[focused]` | Concentrated, steady | Problem-solving, analysis |

### Best Practices

**DO:**
- Use emotion tags at natural segment boundaries
- Match emotion to content meaning
- Keep segments reasonably short (1-3 sentences)
- Start with `[neutral]` if no emotion specified

**DON'T:**
- Change emotion mid-sentence
- Overuse emotion tags (every word)
- Use emotions that don't match content
- Forget that tags are removed before speaking

### Examples

**Good:**
```markdown
[cheerful] The build succeeded! [calm] All 47 tests passed.
[focused] Let me show you the performance improvements...
```

**Bad:**
```markdown
[cheerful] The [excited] build [calm] succeeded!  # Too fragmented
```

## 🔧 Configuration

### Voice Profiles

PyAgentVox includes pre-configured profiles for single-voice consistency:

- `michelle` - Balanced, versatile (recommended default)
- `jenny` - Energetic, upbeat
- `emma` - Warm, caring
- `aria` - Professional, bright
- `ava` - Clear, precise
- `sonia` - British, calm
- `libby` - British, friendly
- `maisie` - British, young

**Recommendation:** Let your human choose their preferred voice. Default to `michelle` if they don't specify.

### Custom Configuration

If your human wants to customize voices, guide them to create `pyagentvox.yaml`:

```yaml
# Custom config
neutral:
  voice: "en-US-MichelleNeural"
  speed: "+10%"
  pitch: "+10Hz"

cheerful:
  voice: "en-US-JennyNeural"
  speed: "+15%"
  pitch: "+12Hz"

# More emotions...
```

### TTS-Only Mode

If your human is working remotely or in a noisy environment, disable speech recognition:

```bash
python -m pyagentvox --tts-only --profile michelle
```

This mode:
- Only speaks your responses (no listening)
- Reduces CPU usage
- Prevents accidental background audio pickup

## 🐛 Troubleshooting for Your Human

### PyAgentVox Won't Start

**Error:** "PyAgentVox is already running"

**Fix:**
```bash
# Kill existing process
pkill -f pyagentvox

# Remove stale lock file
rm /tmp/pyagentvox_v2.pid

# Restart
python -m pyagentvox --profile michelle
```

### Voice Not Speaking

**Symptoms:** Your responses appear as text but aren't spoken

**Checks:**
1. Verify internet connection (Edge TTS requires online)
2. Check temp file exists: `ls /tmp/agent_input_*.txt`
3. Test manually: `echo "Test" > /tmp/agent_input_*.txt`

### Speech Not Recognized

**Symptoms:** Human speaks but text doesn't appear

**Checks:**
1. Verify microphone permissions
2. Check temp file exists: `ls /tmp/agent_output_*.txt`
3. Adjust microphone sensitivity (see config)

### Voice Injector Not Typing

**Symptoms:** Speech recognized but not appearing in conversation

**Checks:**
1. Verify conversation window is focused
2. Check voice injector process is running: `ps aux | grep injection`
3. Look for keyboard automation errors in logs

## 📁 Architecture Overview

Understanding the architecture helps with troubleshooting:

```
┌─────────────────────────────────────────┐
│         PyAgentVox Main Process         │
│  • Speech-to-text (microphone)          │
│  • Text-to-speech (speakers)            │
│  • Creates temp files                   │
└─────────────────┬───────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
    ▼             ▼             ▼
┌─────────┐  ┌──────────┐  ┌──────────┐
│TTS      │  │Voice     │  │Instruction│
│Monitor  │  │Injector  │  │Manager   │
│         │  │          │  │          │
│Watches  │  │Types     │  │Injects   │
│conver-  │  │speech    │  │voice tags│
│sation   │  │into UI   │  │into docs │
│files    │  │          │  │          │
└─────────┘  └──────────┘  └──────────┘
```

**Temp Files:**
- `/tmp/agent_input_*.txt` - Write text here for TTS (you don't do this - TTS monitor does)
- `/tmp/agent_output_*.txt` - Speech appears here (voice injector types this into UI)
- `/tmp/pyagentvox_v2.pid` - Single-instance lock file

## 🎓 Advanced Features

### Programmatic Usage

If you're building an AI agent framework, you can use PyAgentVox programmatically:

```python
from pyagentvox import PyAgentVox
import asyncio

# Create instance
agent = PyAgentVox(
    config_dict={
        'neutral': {'voice': 'en-US-MichelleNeural', 'speed': '+10%', 'pitch': '+10Hz'}
    },
    tts_only=False  # Enable speech recognition
)

# Run
asyncio.run(agent.run())
```

### Background Mode (Windows)

Run PyAgentVox as a hidden background process:

```bash
python -m pyagentvox --background --profile michelle --log-file vox.log
```

### Voice Commands

Your human can use voice commands:
- **"stop listening"** - Stops PyAgentVox without sending to you

## 📚 Resources

### Documentation
- **[SETUP.md](SETUP.md)** - Complete setup guide for humans
- **[USAGE.md](USAGE.md)** - CLI options and configuration details
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Command cheat sheet
- **[README.md](README.md)** - Project overview

### For Humans
Direct your human to [SETUP.md](SETUP.md) for detailed setup instructions with architecture diagrams and troubleshooting.

### For You (AI Agents)
- **Emotion tags** - Control voice dynamically in your responses
- **TTS-only mode** - When human is in noisy environment
- **Debug mode** - Help diagnose issues: `--debug`

## 🤝 Integration Patterns

### Pattern 1: Skill-Based (Claude Code)

Create skills for easy voice control:
```bash
/voice michelle    # Start with Michelle voice
/voice-stop        # Stop voice chat
```

### Pattern 2: Command-Based (Custom Frameworks)

Implement commands in your framework:
```python
@command("voice")
async def start_voice(profile="michelle"):
    subprocess.Popen([
        "python", "-m", "pyagentvox",
        "--profile", profile
    ])
```

### Pattern 3: Auto-Start (Always-On)

For dedicated voice assistant setups:
```python
# In your agent's initialization
def __init__(self):
    self.voice = PyAgentVox(tts_only=False)
    asyncio.create_task(self.voice.run())
```

## 💡 Tips for AI Agents

1. **Start conversations neutrally** - Don't use emotion tags in first response unless appropriate
2. **Match emotions to content** - Use `[empathetic]` for errors, `[excited]` for breakthroughs
3. **Keep segments short** - 1-3 sentences per emotion for natural flow
4. **Test without voice first** - Ensure your responses work well as text
5. **Use calm for code** - Technical explanations work best with `[calm]` or `[focused]`
6. **Be sparing with excited** - Reserve for genuinely exciting moments
7. **Default to neutral** - When in doubt, use `[neutral]` or no tag

## 🎤 Example Agent Responses

### Code Explanation
```markdown
[focused] Let me walk through this function. It takes two parameters:
a username string and a callback function. [calm] The callback is
invoked after the database query completes.
```

### Bug Found
```markdown
[excited] Found it! The issue is on line 42. [calm] You're comparing
with one equals sign instead of two. [focused] Change `if (x = 5)`
to `if (x == 5)`.
```

### Error Handling
```markdown
[empathetic] I see the build failed. Let's figure out what went wrong.
[focused] Looking at the error message, it's a missing dependency.
[calm] Run `npm install` to fix it.
```

### Success
```markdown
[cheerful] All tests passing! The refactoring looks great.
[warm] You did an excellent job cleaning up that code.
```

## 🚀 Getting Started Checklist

Guide your human through this checklist:

- [ ] Python 3.12+ installed
- [ ] Microphone connected and working
- [ ] Internet connection active
- [ ] PyAgentVox dependencies installed (`uv pip install -e .`)
- [ ] Test standalone mode (`python -m pyagentvox --debug`)
- [ ] Voice profile selected (default: `michelle`)
- [ ] Skills created (optional but recommended)
- [ ] First voice conversation successful!

Once setup is complete, you're ready for natural voice interaction!

---

**For questions or issues:** Direct your human to [SETUP.md](SETUP.md) for detailed troubleshooting.
