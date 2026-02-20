# Luna Avatar Generator - Automated Colab Pipeline

Generates **4,870** Luna avatar variations using **Flux.1 Kontext Dev** on Google Colab's free T4 GPU.

## Quick Start (Fully Automated)

```bash
python colab/launch.py
```

That's it. The launcher handles everything:
1. Installs dependencies (selenium, google-api-python-client, etc.)
2. Authenticates with Google (opens browser once for OAuth consent)
3. Uploads BASE_IMAGES + prompt_manifest.py + notebook to Google Drive
4. Opens notebook in Colab via Firefox
5. Sets T4 GPU and clicks Run All
6. Injects keep-alive JavaScript
7. Monitors progress via Drive API
8. Downloads results when complete

### First-Time Setup

You need Google OAuth credentials (one-time):

1. Go to [Google Cloud Console > Credentials](https://console.cloud.google.com/apis/credentials)
2. Create OAuth 2.0 Client ID (Desktop app)
3. Download JSON, save as `~/.colab_runner/credentials.json`
4. Enable [Google Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com)

Then run `python colab/launch.py` -- it opens your browser for OAuth consent.

### Other Modes

```bash
python colab/launch.py --upload-only     # Just upload files to Drive
python colab/launch.py --monitor-only    # Monitor + download (notebook already running)
python colab/launch.py --download-only   # Download finished results
python colab/launch.py --status          # Quick status check
python colab/launch.py --skip-upload     # Skip upload (files already on Drive)
python colab/launch.py --skip-browser    # Skip browser (already running in Colab)
```

## Architecture

```
colab/
  launch.py                      # Full automated launcher (use this)
  luna_avatar_generator.ipynb    # Colab notebook (runs on GPU)
  prompt_manifest.py             # 4,870 image manifest (23 bases x prompts x hairstyles)
  colab_runner.py                # Legacy runner (individual methods)
  README.md                      # This file
```

## How It Works

1. **Flux.1 Kontext Dev** - Image-to-image editing model that preserves character identity
2. **FP8 quantization** (optimum-quanto) - Fits on free T4 GPU (15 GB VRAM)
3. **23 base images** - 9 regular outfits + 14 costumes
4. **170 prompts** - 117 regular (x4 hairstyle variants) + 53 costume-specific
5. **Priority ordering** - Preview round (160 images, ~1.1h) first for quick variety check

### Generation Priority

| Phase | Images | Time | Description |
|-------|--------|------|-------------|
| 1. Preview Regular | 90 | ~0.6h | 10 distinctive poses per regular outfit |
| 2. Preview Costume | 70 | ~0.5h | 5 thematic poses per costume |
| 3. Dress Complete | 386 | ~2.7h | All remaining dress.jpg images |
| 4. Regular Complete | 3,044 | ~21h | Everything else for regular outfits |
| 5. Costume Complete | 1,280 | ~9h | Everything else for costumes |

### Parallel Mode

Split across multiple Colab instances (1 GPU per Google account):

In the notebook, set `CHUNK_INDEX` (0-based) and `TOTAL_CHUNKS` before running.
Each instance gets a balanced slice grouped by base image.

## Post-Generation Pipeline

```bash
# 1. Download results (if not auto-downloaded)
python colab/launch.py --download-only

# 2. Remove backgrounds (uses birefnet-general model, ~973 MB)
python remove_backgrounds.py

# 3. Images are ready in ~/.claude/luna/{outfit}/
# 4. Merge _generated_config.yaml into pyagentvox.yaml
```

## Costs

- **Colab T4 GPU**: Free tier (limited daily hours, ~12h sessions)
- **Google Drive**: Free (15 GB)
- **Flux.1 Kontext Dev**: Free (open-weight model)
- **Total**: $0

## Troubleshooting

- **"No GPU detected"**: Runtime > Change runtime type > T4 GPU
- **Session disconnects**: Keep-alive JS auto-reconnects; re-run notebook (resume-safe)
- **OAuth "unverified app"**: Click Advanced > Go to app (normal for personal OAuth)
- **Firefox not found**: Install Firefox or set path in launch.py
- **~25s per image**: Normal for Flux Kontext on T4 with FP8 quantization
