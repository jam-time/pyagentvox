---
name: voice-context
description: "PyAgentVox voice is active: responses are spoken aloud via TTS with emotion-based voice switching. Control voice mid-response with emotion tags (removed before speaking): [neutral] balanced, [cheerful] upbeat, [excited] enthusiastic, [empathetic] caring, [warm] gentle, [calm] relaxed, [focused] steady. Example: \"[excited] Found it! [calm] Here's why...\" Use /voice to start, /voice-stop to stop, /voice-switch <profile> to change voice (michelle/jenny/emma/aria/ava/sonia/libby), /tts-control and /stt-control to toggle output/input, /voice-modify pitch=+10 to adjust. Avatar shows current emotion; use /avatar-tags to filter images."
user-invocable: false
---

Voice output is active via PyAgentVox. See skill description for quick reference.

## Emotion Tags

Place tags anywhere in your response to switch voice mid-message:

| Tag | Style | When to use |
|-----|-------|-------------|
| `[neutral]` | Balanced, default | General info, factual explanations |
| `[cheerful]` | Happy, upbeat | Good news, greetings |
| `[excited]` | Very enthusiastic | Discoveries, breakthroughs |
| `[empathetic]` | Caring, understanding | Errors, frustrations, debugging |
| `[warm]` | Gentle, kind | Encouragement, support |
| `[calm]` | Professional, relaxed | Technical details, step-by-step |
| `[focused]` | Concentrated, steady | Problem-solving, analysis |

Tags are stripped before TTS — they only control voice style.

## Quick Reference

- Switch profile: `/voice-switch michelle`
- Toggle TTS: `/tts-control off` / `/tts-control on`
- Toggle mic: `/stt-control off` / `/stt-control on`
- Adjust voice: `/voice-modify pitch=+10` or `neutral.speed=-15`
- Avatar filters: `/avatar-tags filter --include casual` or `--exclude formal`
- Stop everything: `/voice-stop`
