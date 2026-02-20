---
name: voice-switch
description: Switch PyAgentVox voice profile without restarting. Use when changing voice personality - e.g. switch to Michelle for empathetic tone, Jenny for energetic, Sonia for professional. Available profiles: michelle, jenny, emma, aria, ava, sonia, libby.
argument-hint: "<profile>"
---

# Voice Profile Switch Skill

Switch PyAgentVox voice profiles on the fly without restarting. Perfect for adapting voice tone to match conversation context!

## What This Does

Hot-swaps the active voice profile in a running PyAgentVox instance:
- **No interruption** - Waits for current TTS to finish before switching
- **Seamless** - Takes only 1-2 seconds
- **Safe** - Falls back to current profile on errors
- **Automatic** - Updates CLAUDE.md with new profile description

## Usage

```bash
/voice-switch <profile>
```

## Available Profiles

### US Voices
- **`michelle`** - Sweet, empathetic, and caring (perfect for debugging frustrations)
- **`jenny`** - Energetic, playful, and upbeat (great for celebrations)
- **`emma`** - Warm, nurturing, and understanding (ideal for patient explanations)
- **`aria`** - Professional, confident, and bright (excellent for presentations)
- **`ava`** - Clear, precise, and versatile (great for technical discussions)

### British Voices
- **`sonia`** - Calm and professional (perfect for focused work)
- **`libby`** - Friendly and approachable (lovely for collaborative problem-solving)

### Default
- **`default`** - Clear, precise, and versatile

## Examples

```bash
# User seems frustrated debugging
/voice-switch michelle

# Successfully fixed the bug!
/voice-switch jenny

# Explaining complex architecture
/voice-switch emma

# Presenting to stakeholders
/voice-switch aria
```

## When to Use Profile Switching

### 🔧 **Debugging & Problem Solving**
- **Michelle** or **Emma** - When user is frustrated or stuck
- **Sonia** - For calm, focused debugging sessions

### 🎉 **Celebrations & Success**
- **Jenny** - Tests passing, builds succeeding, bugs fixed!

### 📚 **Learning & Teaching**
- **Emma** - Patient explanations of new concepts
- **Libby** - Friendly collaborative learning

### 💼 **Professional Contexts**
- **Aria** - Presentations, demos, stakeholder communication
- **Sonia** - Architecture discussions, technical planning

### 💻 **General Coding**
- **Ava** (default) - Clear technical discussions
- **Sonia** - Focused coding sessions

## Requirements

- PyAgentVox must be running (start with `/voice`)
- Profile switch happens after current speech finishes

## Troubleshooting

**PyAgentVox not running:**
```bash
/voice [profile]
```

**Profile not switching:**
- Check PyAgentVox logs for errors
- Verify profile name is correct (case-sensitive)
- Restart PyAgentVox if needed: `/voice-stop` then `/voice`

## Behind the Scenes

This skill calls: `python -m pyagentvox --switch <profile>`

The switch process:
1. Finds running PyAgentVox PID
2. Writes profile name to control file
3. PyAgentVox detects change and waits for TTS queue to drain
4. Reloads config with new profile
5. Reinitializes TTS engine with new voices
6. Updates CLAUDE.md instructions with new profile description
