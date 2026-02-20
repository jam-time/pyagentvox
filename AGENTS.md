# PyAgentVox Setup Guide for AI Agents

**For AI Assistants:** This guide explains how to set up and use PyAgentVox voice communication for your human user. Follow this guide to implement full two-way voice in one session.

## 🎯 What is PyAgentVox?

PyAgentVox enables **two-way voice communication** between you (the AI) and your human:
- **Human speaks** → Text appears in conversation automatically
- **You respond** → Your text is spoken aloud with emotion-based voices
- **You control voice** → Use emotion tags like `[cheerful]` or `[calm]` to change voice dynamically
- **Runtime control** → Adjust TTS/STT, modify voice settings, switch profiles without restart

## 🚀 Quick Setup (For Your Human's Project)

### Step 0: Collect User Preferences First

**Ask your human these questions BEFORE running any commands.** You need this info to configure PyAgentVox correctly.

| # | Question | Options | Default |
|---|----------|---------|---------|
| 1 | **Which voice profile do you prefer?** | `michelle` (empathetic), `jenny` (energetic), `emma` (warm), `aria`/`ava` (professional), `sonia`/`libby` (British) | `michelle` |
| 2 | **Do you want to use speech-to-text?** (speak to Claude with your voice) | Yes = full mode, No = TTS-only (AI speaks, you type) | TTS-only |
| 3 | **How noisy is your environment?** *(only if using STT)* | Quiet → sensitivity 1000-3000, Normal → 4000, Noisy → 5000-8000 | 4000 |

**Once you have answers**, proceed with setup. Use the profile and mode in Step 4 below.

> **Example opener:** "I'm going to set up PyAgentVox voice for you. Quick question - which voice profile do you like? Options are: Michelle (sweet/empathetic), Jenny (energetic), Emma (warm), or a few British voices. And will you be speaking to me with your mic, or would you prefer I just speak to you while you type?"

### Prerequisites Check

Before starting, verify your human has:
- Python 3.10+ installed
- Windows OS (voice injector requires win32gui)
- Microphone connected (only needed for STT - can skip for TTS-only)
- Internet connection (for TTS and speech recognition)

### Step 1: Install PyAgentVox

Guide your human through installation:

```bash
# Clone or navigate to pyagentvox directory
cd /path/to/pyagentvox

# Install dependencies
pip install -e .
# OR
uv pip install -e .
```

### Step 2: Test PyAgentVox Standalone

Before integrating, test that it works:

```bash
# Start PyAgentVox with Michelle profile, TTS-only mode
python -m pyagentvox start --tts-only --profile michelle --debug

# Your human should see:
#   ✓ Voice Injector started
#   ✓ TTS Monitor started
#   ✓ TTS queue processor started

# Check status
python -m pyagentvox status

# Test TTS by writing to input file shown in status

# Stop when done testing
python -m pyagentvox stop
```

### Step 3: Create Voice Control Skills

PyAgentVox includes pre-built skills in `.claude/skills/`. Verify they exist:

```bash
ls .claude/skills/

# Should see:
#   voice/           - Start PyAgentVox
#   voice-stop/      - Stop PyAgentVox
#   voice-switch/    - Switch voice profiles
#   tts-control/     - Control TTS on/off
#   stt-control/     - Control STT on/off
#   voice-modify/    - Modify voice settings
```

All skills are ready to use immediately - no configuration needed!

### Step 4: Start Voice Communication

Use the profile and mode you collected in Step 0:

```bash
# TTS-only (no microphone) - recommended for most users
/voice michelle tts-only    # Replace "michelle" with chosen profile

# Full mode (microphone + TTS)
/voice jenny                # Replace "jenny" with chosen profile

# Stop voice when done
/voice-stop
```

That's it! Voice communication is now active. After starting, tell your human which emotion tags you'll use and invite them to speak (if in full mode).

## 📋 CLI Reference (Essential Commands)

PyAgentVox uses a subcommand architecture. All commands support per-window operation (multiple Claude Code instances can run PyAgentVox independently).

### Main Commands

```bash
# Start PyAgentVox
python -m pyagentvox start [--profile PROFILE] [--tts-only] [--debug] [--background]

# Stop running instance
python -m pyagentvox stop

# Check status
python -m pyagentvox status
```

### Runtime Control (NEW!)

```bash
# Control TTS output
python -m pyagentvox tts on      # Enable text-to-speech
python -m pyagentvox tts off     # Disable (silent mode)

# Control STT input
python -m pyagentvox stt on      # Enable speech recognition
python -m pyagentvox stt off     # Disable (keyboard only)

# Modify voice settings at runtime
python -m pyagentvox modify pitch=+10          # Increase pitch for all emotions
python -m pyagentvox modify neutral.speed=-15  # Slow down neutral voice
python -m pyagentvox modify all.pitch=+5       # Increase pitch for all emotions

# Switch voice profile
python -m pyagentvox switch jenny    # Switch to Jenny profile
```

### CLI Options

```bash
--profile PROFILE          # Voice profile (michelle, jenny, emma, aria, ava, sonia, libby)
--tts-only                 # TTS only (no speech recognition)
--debug                    # Enable debug logging
--background               # Run in background (Windows only)
--config CONFIG            # Custom config file path
--log-file FILE            # Log to file
```

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

## 🔄 Runtime Control Features (NEW!)

### TTS Control (On/Off)

Control text-to-speech without restarting:

```bash
# Via CLI
python -m pyagentvox tts off     # Mute responses
python -m pyagentvox tts on      # Unmute

# Via skill
/tts-control off
/tts-control on
```

**Use cases:**
- Noisy environment (disable TTS)
- Presentation mode (enable TTS)
- Late night coding (disable TTS)

### STT Control (On/Off)

Control speech recognition without restarting:

```bash
# Via CLI
python -m pyagentvox stt off     # Stop listening
python -m pyagentvox stt on      # Start listening

# Via skill
/stt-control off
/stt-control on
```

**Use cases:**
- Conference call (disable microphone)
- Hands-free needed (enable microphone)

### Voice Modification (Runtime)

Adjust voice settings on the fly:

```bash
# Global adjustments (all emotions)
python -m pyagentvox modify pitch=+10     # Higher pitch
python -m pyagentvox modify speed=-15     # Slower speech

# Emotion-specific
python -m pyagentvox modify neutral.pitch=+5        # Adjust neutral only
python -m pyagentvox modify cheerful.speed=-10      # Slow cheerful voice

# Apply to all emotions explicitly
python -m pyagentvox modify all.pitch=+3

# Via skill
/voice-modify pitch=+10
/voice-modify neutral.speed=-15
```

**Use cases:**
- User finds voice too high/low
- User prefers slower/faster speech
- Fine-tune specific emotions

### Profile Switching

Switch voice profiles during conversation:

```bash
# Via CLI
python -m pyagentvox switch jenny

# Via skill
/voice-switch jenny
```

**Use cases:**
- User frustrated → Switch to empathetic Michelle
- Bug fixed → Switch to energetic Jenny
- Technical explanation → Switch to professional Sonia

### Status Checking

Check if PyAgentVox is running and view control files:

```bash
python -m pyagentvox status

# Output:
# PyAgentVox Status
# ==================================================
# Lock ID: 6560708d
# Status: ✓ Running
# PID: 54380
# Memory: 53.1 MB
# CPU: 0.0%
#
# Control files:
#   Profile: /tmp/agent_profile_54380.txt
#   Control: /tmp/agent_control_54380.txt
#   Modify: /tmp/agent_modify_54380.txt
```

## 🎪 Voice Profile Guide

### Available Profiles & Their Vibes

| Profile | Description | Best For |
|---------|-------------|----------|
| `michelle` | Sweet, empathetic, caring | Debugging frustrations, difficult moments |
| `jenny` | Energetic, playful, upbeat | Celebrations, successful builds |
| `emma` | Warm, nurturing, understanding | Patient explanations, learning |
| `aria` | Professional, confident, bright | Presentations, demos |
| `ava` | Clear, precise, versatile | Technical discussions, coding |
| `sonia` | British, calm, professional | Focused work, architecture |
| `libby` | British, friendly, approachable | Collaborative problem-solving |

### When to Switch Profiles

**🔧 Debugging & Problem Solving**
```bash
# User is stuck on a tricky bug
/voice-switch michelle
```
Then in your response:
```markdown
[empathetic] I know this is frustrating. Let's work through it together.
```

**🎉 Celebrations & Success**
```bash
# Tests just passed!
/voice-switch jenny
```
Then:
```markdown
[excited] YES! All tests passing! [cheerful] You crushed it!
```

**📚 Teaching & Learning**
```bash
# User learning new concepts
/voice-switch emma
```
Then:
```markdown
[warm] Let me walk you through this step by step...
```

## 🛠️ Skills Reference

All skills are in `.claude/skills/` and work immediately:

### `/voice` - Start PyAgentVox

```bash
/voice                      # Default voice
/voice michelle             # Michelle voice
/voice jenny tts-only       # Jenny voice, no microphone
/voice emma debug           # Emma voice with debug logs
/voice tts-only debug       # Default voice, no mic, debug mode
```

**Arguments:**
- `[profile]` - Voice profile (michelle, jenny, emma, aria, ava, sonia, libby)
- `tts-only` - TTS only (no speech recognition)
- `debug` - Enable debug logging
- `custom` - Use pyagentvox.yaml from current directory

### `/voice-stop` - Stop PyAgentVox

```bash
/voice-stop
```

Cleanly stops PyAgentVox and all subprocesses.

### `/voice-switch` - Switch Profile

```bash
/voice-switch jenny
```

**Available profiles:** michelle, jenny, emma, aria, ava, sonia, libby, default

### `/tts-control` - Control TTS (NEW!)

```bash
/tts-control on
/tts-control off
```

Enable/disable text-to-speech output at runtime.

### `/stt-control` - Control STT (NEW!)

```bash
/stt-control on
/stt-control off
```

Enable/disable speech recognition at runtime.

### `/voice-modify` - Modify Voice (NEW!)

```bash
/voice-modify pitch=+5
/voice-modify speed=-10
/voice-modify neutral.pitch=+10
/voice-modify cheerful.speed=-5
/voice-modify all.pitch=+3
```

Adjust voice settings at runtime.

**Supported settings:**
- `pitch` - Voice pitch (Hz)
- `speed` - Speech speed (%)

**Scopes:**
- Global: `pitch=+5` (applies to all)
- Emotion-specific: `neutral.pitch=+10`
- Explicit all: `all.pitch=+3`

## 🏗️ Architecture Overview

Understanding the architecture helps with troubleshooting:

```
┌─────────────────────────────────────────┐
│         PyAgentVox Main Process         │
│  • Speech-to-text (microphone)          │
│  • Text-to-speech (speakers)            │
│  • Runtime control watchers (NEW!)      │
│  • Profile hot-swap queue               │
│  • Per-window PID locking (NEW!)        │
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

### Key Components

**Main Process:**
- Manages async event loop
- Runs 5 concurrent watchers:
  - Input file watcher (TTS requests)
  - Profile control watcher (hot-swap)
  - TTS/STT control watcher (on/off commands)
  - Voice modify watcher (runtime settings)
  - TTS queue processor (parallel generation + sequential playback)

**TTS Monitor:**
- Watches conversation JSONL files
- Sends Claude responses to main process
- Smart path filtering (excludes subagent files)

**Voice Injector:**
- Types recognized speech into Claude Code
- Windows PostMessage API (no focus stealing)
- Background operation

**Instruction Manager:**
- Auto-injects voice tag documentation
- Updates CLAUDE.md dynamically
- Removes instructions on shutdown

### IPC (Inter-Process Communication)

**Control Files:**
- `agent_profile_{pid}.txt` - Profile hot-swap requests
- `agent_control_{pid}.txt` - TTS/STT on/off commands
- `agent_modify_{pid}.txt` - Voice modification commands
- `agent_input_{pid}.txt` - TTS requests (from monitor)
- `agent_output_{pid}.txt` - STT output (to injector)

**PID Files (Per-Window Locking):**
- `pyagentvox_{lock_id}.pid` - Per-window lock
- Lock ID = MD5 hash of conversation file path
- Allows multiple PyAgentVox instances in different Claude Code windows

## 🐛 Troubleshooting for Your Human

### PyAgentVox Won't Start

**Error:** "PyAgentVox is already running"

**Fix:**
```bash
# Check status first
python -m pyagentvox status

# If running, stop it
python -m pyagentvox stop

# If stale lock:
rm /tmp/pyagentvox_*.pid

# Restart
python -m pyagentvox start --profile michelle
```

### Voice Not Speaking

**Symptoms:** Your responses appear as text but aren't spoken

**Checks:**
1. Verify TTS is enabled: `python -m pyagentvox status`
2. If disabled, enable: `python -m pyagentvox tts on`
3. Check internet connection (Edge TTS requires online)
4. Test manually: `echo "Test" > /tmp/agent_input_*.txt`

### Speech Not Recognized

**Symptoms:** Human speaks but text doesn't appear

**Checks:**
1. Verify STT is enabled: `python -m pyagentvox status`
2. If disabled, enable: `python -m pyagentvox stt on`
3. Check microphone permissions
4. Verify not in TTS-only mode

### Skills Not Working

**Symptoms:** `/voice` or other skills fail

**Checks:**
1. Verify skill scripts are executable: `chmod +x .claude/skills/*/*.sh`
2. Check PyAgentVox root path in skill scripts
3. Run skill script directly to see errors: `bash .claude/skills/voice/voice.sh`

### Runtime Controls Not Responding

**Symptoms:** `tts off` or `modify` commands don't work

**Checks:**
1. Verify PyAgentVox is running: `python -m pyagentvox status`
2. Check control file was created: `ls /tmp/agent_control_*.txt`
3. Check PyAgentVox logs for watcher errors
4. Restart PyAgentVox if watchers crashed

## 💡 Tips for AI Agents

### General Usage

1. **Start conversations neutrally** - Don't use emotion tags in first response unless appropriate
2. **Match emotions to content** - Use `[empathetic]` for errors, `[excited]` for breakthroughs
3. **Keep segments short** - 1-3 sentences per emotion for natural flow
4. **Test without voice first** - Ensure your responses work well as text
5. **Use calm for code** - Technical explanations work best with `[calm]` or `[focused]`
6. **Be sparing with excited** - Reserve for genuinely exciting moments
7. **Default to neutral** - When in doubt, use `[neutral]` or no tag

### Runtime Control Recommendations

1. **Monitor user context** - Suggest TTS off if they mention noise/distraction
2. **Proactive profile switching** - Switch to Michelle when user is frustrated
3. **Voice fine-tuning** - If user mentions voice issues, suggest `/voice-modify`
4. **Status awareness** - Periodically check if PyAgentVox is still running
5. **Graceful degradation** - If PyAgentVox stops, suggest restart

### Skill Usage Patterns

```markdown
# Starting voice for first time
Let's enable voice communication! I'll use the Michelle voice profile.

(Execute: /voice michelle tts-only)

# User seems frustrated debugging
I can hear the frustration. Let me switch to a more empathetic voice.

(Execute: /voice-switch michelle)

[empathetic] I know this is tough. Let's work through it together.

# Bug fixed!
(Execute: /voice-switch jenny)

[excited] YES! We found it! [cheerful] Great debugging work!

# Late night coding
It's getting late - want me to disable voice output so I don't wake anyone?

(Offer: /tts-control off)

# User wants faster speech
(Execute: /voice-modify speed=+20)

I've increased the speech speed. Let me know if this is better!
```

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

### Error Handling with Profile Switch
```bash
/voice-switch michelle
```
```markdown
[empathetic] I see the build failed. Let's figure out what went wrong.
[focused] Looking at the error message, it's a missing dependency.
[calm] Run `npm install` to fix it.
```

### Success with Profile Switch
```bash
/voice-switch jenny
```
```markdown
[cheerful] All tests passing! The refactoring looks great.
[warm] You did an excellent job cleaning up that code.
```

## 🚀 Implementation Checklist

When setting up PyAgentVox for your human, use this checklist:

### Installation
- [ ] Python 3.10+ verified
- [ ] PyAgentVox installed (`pip install -e .`)
- [ ] Dependencies working (no import errors)

### Testing
- [ ] Standalone mode tested (`python -m pyagentvox start --debug --tts-only`)
- [ ] Status command works (`python -m pyagentvox status`)
- [ ] Stop command works (`python -m pyagentvox stop`)

### Skills
- [ ] Skills directory exists (`.claude/skills/`)
- [ ] All 6 skills present (voice, voice-stop, voice-switch, tts-control, stt-control, voice-modify)
- [ ] Scripts are executable (`chmod +x`)
- [ ] Test basic skill: `/voice michelle tts-only`

### Runtime Controls
- [ ] TTS control tested (`python -m pyagentvox tts off/on`)
- [ ] Voice modify tested (`python -m pyagentvox modify pitch=+5`)
- [ ] Profile switch tested (`python -m pyagentvox switch jenny`)

### Integration
- [ ] Voice instructions appear in CLAUDE.md when active
- [ ] Emotion tags working in responses
- [ ] Profile switching updates instructions
- [ ] Clean shutdown removes instructions

### User Experience
- [ ] Voice profile selected (let user choose or default to michelle)
- [ ] TTS/STT mode chosen (tts-only for remote/noisy)
- [ ] First conversation successful
- [ ] User knows how to stop (`/voice-stop`)

Once complete, you're ready for full two-way voice interaction! 🎉

## 📚 Additional Resources

### Documentation
- **[README.md](README.md)** - Project overview
- **[SETUP.md](SETUP.md)** - Detailed setup guide for humans
- **[USAGE.md](USAGE.md)** - Full CLI reference and configuration
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Command cheat sheet

### Skills Documentation
Each skill has a `skill.md` file with detailed usage:
- `.claude/skills/voice/skill.md`
- `.claude/skills/voice-switch/skill.md`
- `.claude/skills/tts-control/skill.md`
- (etc.)

### For Advanced Integration
- **Programmatic API** - Use `from pyagentvox import PyAgentVox`
- **Custom configs** - Create `pyagentvox.yaml` for voice customization
- **Background mode** - Run with `--background` flag (Windows)
- **Multiple windows** - Per-window locking allows concurrent instances

---

**For questions or issues:** Direct your human to [SETUP.md](SETUP.md) or check `python -m pyagentvox --help` for CLI reference.

**Version:** PyAgentVox with CLI subcommands, per-window locking, and runtime controls.
