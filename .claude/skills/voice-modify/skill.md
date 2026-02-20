# Voice Modify

Modify voice settings (pitch, speed) at runtime without restarting PyAgentVox.

## Usage

```bash
/voice-modify <setting>
```

## Setting Formats

- `pitch=<value>` - Adjust pitch for all emotions
- `speed=<value>` - Adjust speed for all emotions
- `<emotion>.pitch=<value>` - Adjust pitch for specific emotion
- `<emotion>.speed=<value>` - Adjust speed for specific emotion
- `all.pitch=<value>` - Adjust pitch for all emotions (explicit)

## Examples

### Global Adjustments
- `/voice-modify pitch=+5` - Increase pitch by 5Hz for all emotions
- `/voice-modify speed=-10` - Decrease speed by 10% for all emotions

### Emotion-Specific Adjustments
- `/voice-modify neutral.pitch=+10` - Increase neutral pitch by 10Hz
- `/voice-modify cheerful.speed=-5` - Decrease cheerful speed by 5%
- `/voice-modify excited.pitch=-3` - Decrease excited pitch by 3Hz

### Apply to All Emotions
- `/voice-modify all.pitch=+3` - Increase pitch by 3Hz for all emotions
- `/voice-modify all.speed=-15` - Decrease speed by 15% for all emotions

## Available Emotions

- `neutral` - Default voice
- `cheerful` - Happy, upbeat
- `excited` - Very enthusiastic
- `empathetic` - Caring, understanding
- `warm` - Friendly, comforting
- `calm` - Relaxed, professional
- `focused` - Concentrated, serious

## Notes

- PyAgentVox must be running (`/voice`)
- Changes take effect immediately for next TTS output
- Values are relative (use + or - to adjust from current)
- Pitch values in Hz, speed values in %
- Changes are temporary (lost on restart)
