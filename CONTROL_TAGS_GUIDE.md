# Avatar Control Tags - Complete Guide

## Overview

Control tags are specialty tags for interactive button states and special animations. They work alongside regular emotion tags but serve specific UI purposes.

## Control Tag Categories

**Naming Convention:** `control-<component>-<trigger>[-<state>]`

Tags describe **FUNCTION** (when/why they're shown), **NOT** content (what they look like).

### 1. Button Hover States
Show when user hovers over control buttons:

| Tag | Trigger | When Shown |
|-----|---------|------------|
| `control-tts-hover-on` | Hover TTS button (enabled state) | Mouse over 🔊 button |
| `control-tts-hover-off` | Hover TTS button (disabled state) | Mouse over 🔇 button |
| `control-stt-hover-on` | Hover STT button (enabled state) | Mouse over 🎤 button |
| `control-stt-hover-off` | Hover STT button (disabled state) | Mouse over 🔇 button |
| `control-close-hover` | Hover close button | Mouse over ❌ button |

### 2. Button Click Feedback
Brief confirmation animation after clicking:

| Tag | Trigger | Duration |
|-----|---------|----------|
| `control-tts-clicked` | TTS button clicked | 1 second |
| `control-stt-clicked` | STT button clicked | 1 second |

### 3. Special Animations
Used for specific UI events:

| Tag | Trigger | When Shown |
|-----|---------|------------|
| `control-close-animation` | Close animation triggered | After clicking ❌, before slide-down |

---

## Registration Examples

### Button Hover Images

```bash
# TTS button hover states (functional tags describe WHEN they're shown, not WHAT they show)
python -m pyagentvox.avatar_tags add controls/tts-hover-enabled.png \
  --tags control-tts-hover-on

python -m pyagentvox.avatar_tags add controls/tts-hover-disabled.png \
  --tags control-tts-hover-off

# STT button hover states
python -m pyagentvox.avatar_tags add controls/stt-hover-enabled.png \
  --tags control-stt-hover-on

python -m pyagentvox.avatar_tags add controls/stt-hover-disabled.png \
  --tags control-stt-hover-off

# Close button hover
python -m pyagentvox.avatar_tags add controls/close-hover.png \
  --tags control-close-hover
```

### Feedback Animations

```bash
# TTS clicked confirmation
python -m pyagentvox.avatar_tags add controls/tts-clicked.png \
  --tags control-tts-clicked

# STT clicked confirmation
python -m pyagentvox.avatar_tags add controls/stt-clicked.png \
  --tags control-stt-clicked
```

### Special Animations

```bash
# Close animation (before slide-down)
python -m pyagentvox.avatar_tags add controls/close-animation.png \
  --tags control-close-animation
```

---

## Tag Naming Convention

**Format:** `control-<component>-<trigger>[-<state>]`

**Key Principle:** Tags describe **FUNCTION** (when/why shown), not content (what image looks like)

**Examples:**
- `control-tts-hover-on` - Component (tts) + trigger (hover) + state (on)
- `control-stt-hover-off` - Component (stt) + trigger (hover) + state (off)
- `control-close-hover` - Component (close) + trigger (hover)
- `control-tts-clicked` - Component (tts) + trigger (clicked)
- `control-close-animation` - Component (close) + trigger (animation)

---

## Additional Tags (Optional)

Control images should ONLY have the functional control tag. Additional descriptive tags are **not recommended** since they describe content rather than function:

```bash
# ✅ GOOD - Functional only
--tags control-tts-hover-on

# ❌ BAD - Mixed functional + descriptive
--tags control-tts-hover-on,cheerful,thumbs-up

# ✅ GOOD - Multiple functional tags if image serves multiple purposes
--tags control-tts-hover-on,control-stt-hover-on
```

**Why?** The tag describes WHEN the image is shown (function), not WHAT it looks like (content).

---

## Backward Compatibility

The system supports legacy filenames for smooth migration:

| Legacy Filename | Functional Control Tag | Status |
|----------------|----------------------|--------|
| `tts-on.png` | `control-tts-hover-on` | ✅ Auto-mapped |
| `tts-off.png` | `control-tts-hover-off` | ✅ Auto-mapped |
| `stt-on.png` | `control-stt-hover-on` | ✅ Auto-mapped |
| `stt-off.png` | `control-stt-hover-off` | ✅ Auto-mapped |
| `pleading.png` | `control-close-hover` | ✅ Auto-mapped |
| `crying.png` | `control-close-animation` | ✅ Auto-mapped |
| `tts-toggled.png` | `control-tts-clicked` | ✅ Auto-mapped |
| `stt-toggled.png` | `control-stt-clicked` | ✅ Auto-mapped |

**If images are in `controls/` subdirectory and NOT registered in config**, the system will find them by filename automatically.

---

## Control Images vs Emotion Images

### Key Differences

| Aspect | Emotion Images | Control Images |
|--------|---------------|----------------|
| **Tags** | Emotion tags (cheerful, excited, etc.) | Control tags (control-*) |
| **Display** | Shown during normal TTS/conversations | Shown only during UI interactions |
| **Filtering** | Affected by include/exclude filters | Never filtered (always available) |
| **Cycling** | Cycle through variants automatically | Single image per control state |
| **Duration** | Shown until emotion changes | Shown for hover/click duration |

### Exclusion from Normal Display

Control images are **automatically excluded** from:
- Normal emotion display cycles
- Tag filtering (include/exclude)
- Variant cycling during TTS playback

This prevents control images from appearing during conversations.

---

## Complete Registration Workflow

### Step 1: Scan for Control Images

```bash
# Scan controls subdirectory
ls ~/.claude/luna/controls/

# Example output:
# tts-on.png
# tts-off.png
# stt-on.png
# stt-off.png
# pleading.png
# crying.png
# tts-toggled.png
# stt-toggled.png
```

### Step 2: Register All Control Images

```bash
#!/bin/bash
# register_controls.sh - Register all control images

CONTROLS_DIR="$HOME/.claude/luna/controls"

# TTS button hovers (functional tags only)
python -m pyagentvox.avatar_tags add "$CONTROLS_DIR/tts-hover-on.png" \
  --tags control-tts-hover-on

python -m pyagentvox.avatar_tags add "$CONTROLS_DIR/tts-hover-off.png" \
  --tags control-tts-hover-off

# STT button hovers
python -m pyagentvox.avatar_tags add "$CONTROLS_DIR/stt-hover-on.png" \
  --tags control-stt-hover-on

python -m pyagentvox.avatar_tags add "$CONTROLS_DIR/stt-hover-off.png" \
  --tags control-stt-hover-off

# Close button hover
python -m pyagentvox.avatar_tags add "$CONTROLS_DIR/close-hover.png" \
  --tags control-close-hover

# Click feedback animations
python -m pyagentvox.avatar_tags add "$CONTROLS_DIR/tts-clicked.png" \
  --tags control-tts-clicked

python -m pyagentvox.avatar_tags add "$CONTROLS_DIR/stt-clicked.png" \
  --tags control-stt-clicked

# Close animation
python -m pyagentvox.avatar_tags add "$CONTROLS_DIR/close-animation.png" \
  --tags control-close-animation

echo "✅ Registered all control images!"
```

### Step 3: Verify Registration

```bash
# List all control images
python -m pyagentvox.avatar_tags list | grep control-

# Example output:
# controls/tts-on.png
#   Tags: control-tts-on, cheerful, thumbs-up
# controls/tts-off.png
#   Tags: control-tts-off, neutral, finger-to-lips
# ...
```

---

## Testing Control Images

### Test Button Hovers

1. Start PyAgentVox with avatar:
   ```bash
   python -m pyagentvox --avatar
   ```

2. Move mouse over avatar → Control buttons appear

3. Hover over each button:
   - **🔊 (TTS enabled)** → Shows `control-tts-hover-on`
   - **🔇 (TTS disabled)** → Shows `control-tts-hover-off`
   - **🎤 (STT enabled)** → Shows `control-stt-hover-on`
   - **🔇 (STT disabled)** → Shows `control-stt-hover-off`
   - **❌ (Close)** → Shows `control-close-hover`

### Test Click Feedback

1. Click TTS button → Shows `control-tts-clicked` for 1 second
2. Click STT button → Shows `control-stt-clicked` for 1 second
3. Click Close button → Shows `control-close-animation`, then slides down

### Test Fallback

1. Remove a control image from registry
2. System should fall back to filename lookup in `controls/` subdirectory
3. Tries functional name first (`tts-hover-on.png`), then legacy names (`tts-on.png`)
4. Log message: `"Loaded control image by filename: tts-hover-on"` or `"tts-on"`

---

## Design Recommendations

**Remember:** Tags describe FUNCTION (when shown), not CONTENT (what it looks like)

### Button Hover Images (`control-*-hover-*`)
- **Clear visual feedback** - User should know what button does
- **State distinction** - Enabled vs disabled should be visually different
- **Avatar personality** - Can show any emotion/pose that fits the function
- **Consistent style** - Match rest of avatar collection

### Feedback Images (`control-*-clicked`)
- **Positive confirmation** - Any expression that says "got it!"
- **Brief but clear** - User sees it for 1 second
- **Different from hover** - Should feel like confirmation, not just hover repeat
- **Avatar personality** - Can be happy, thumbs up, wink, or any positive gesture

### Special Animations (`control-close-animation`)
- **Close animation**: Any expression/gesture appropriate for saying goodbye
- **Avatar personality** - Can be sad, waving, blowing kiss, etc.
- **Your choice** - The tag describes WHEN it's shown, not WHAT it shows

---

## Advanced: Creating Variants

You can create multiple variants for each control state:

```bash
# Multiple pleading variants
python -m pyagentvox.avatar_tags add controls/pleading-1.png \
  --tags control-pleading,empathetic,puppy-eyes,cream-dress

python -m pyagentvox.avatar_tags add controls/pleading-2.png \
  --tags control-pleading,empathetic,begging,daisy-dukes

# System will randomly choose one when showing pleading state
```

---

## Troubleshooting

### Control image not showing
**Check:**
1. Image is registered: `python -m pyagentvox.avatar_tags list | grep control-`
2. Tag format is correct: Must start with `control-`
3. Fallback directory exists: `~/.claude/luna/controls/`

### Wrong image showing
**Check:**
1. Tag matches exactly: `control-tts-on` not `tts-on`
2. Only one image per control tag (or system picks randomly)
3. Check logs: `[AVATAR] Loaded control image by tag: control-tts-on`

### Control image shows during conversation
**This should never happen!** Control images are excluded from emotion display.

**If it does:**
1. Check tags don't have emotion tags + control tags mixed incorrectly
2. Verify exclusion logic in code
3. Report bug with logs

---

## Summary

**Control tags provide:**
- ✅ Semantic button state images
- ✅ Special animation control
- ✅ Separation from emotion images
- ✅ Backward compatibility with filenames
- ✅ Optional variants per control state

**Best practices:**
- Always use `control-` prefix
- Register all control images explicitly
- Keep control images in `controls/` subdirectory
- Test all button interactions after registration

**Happy controlling! 🎮✨**
