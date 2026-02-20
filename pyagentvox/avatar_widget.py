"""Floating avatar widget for PyAgentVox mood visualization.

This module provides a Tkinter-based always-on-top floating window that displays
Luna's mood-based avatar images. It monitors a temp file written by the TTS
playback system to update the displayed avatar based on the currently-playing
emotion, cycling through multiple image variants per emotion.

Features:
    - Always-on-top transparent floating window
    - Mood-based avatar switching linked to TTS audio playback
    - Multiple image variants per emotion with automatic cycling (3-5s)
    - "Waiting" idle state with its own image variants
    - Full-size image support with aspect ratio preservation
    - Bottom-of-screen anchoring (looks like standing on taskbar)
    - Click-through window (doesn't steal focus or block clicks)
    - Right-click to close
    - Position persistence across restarts
    - Smooth fade transitions between emotions
    - PNG alpha channel transparency support

Usage:
    # Standalone
    python -m pyagentvox.avatar_widget

    # With PyAgentVox (auto-launched)
    python -m pyagentvox start --avatar

Author:
    Jake Meador <jameador13@gmail.com>
"""

import contextlib
import json
import logging
import math
import os
import random
import sys
import tempfile
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox
from typing import Any

try:
    from PIL import Image, ImageEnhance, ImageFilter, ImageTk
except ImportError:
    print('ERROR: Pillow is required for the avatar widget.', file=sys.stderr)
    print('Install with: pip install Pillow', file=sys.stderr)
    raise SystemExit(1)

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

try:
    import win32gui
    import win32con
except ImportError:
    win32gui = None  # type: ignore[assignment]
    win32con = None  # type: ignore[assignment]

__author__ = 'Jake Meador <jameador13@gmail.com>'
__all__ = ['AvatarWidget', 'ImageEntry', 'TagEditorDialog', 'main']

logger = logging.getLogger('pyagentvox.avatar')

# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class ImageEntry:
    """Represents a registered avatar image with tags.

    Attributes:
        path: Path to the image file (relative to avatar directory or absolute).
        tags: List of tags (must include at least one emotion tag).
    """
    path: Path
    tags: list[str]

    def __post_init__(self) -> None:
        """Convert path string to Path object if needed."""
        if isinstance(self.path, str):
            self.path = Path(self.path)

    @property
    def tag_set(self) -> set[str]:
        """Return tags as a set for efficient lookups."""
        return {tag.lower() for tag in self.tags}


# ============================================================================
# Config Loading
# ============================================================================

def load_avatar_config() -> dict[str, Any]:
    """Load avatar configuration from pyagentvox.yaml files.

    Loads the package default config first, then merges any CWD config on top.
    This ensures TTS/avatar base settings from the package are always present,
    while CWD-specific settings (like image registry) override them.

    Returns:
        Avatar config dict with keys: directory, idle_states, emotion_hierarchy, etc.
        Returns default config if file not found or yaml not installed.
    """
    default_config: dict[str, Any] = {
        'enabled': True,
        'directory': str(Path.home() / '.claude' / 'luna'),
        'default_size': 300,
        'cycle_interval': 4000,
        'idle_states': {'waiting': 0, 'bored': 60, 'sleeping': 120},
        'emotion_hierarchy': {},
        'filters': {
            'include_tags': [],
            'exclude_tags': [],
            'require_all_include': False,
        },
        'animation': {
            'shimmer_threshold': 0.5,
            'shimmer_duration': 400,
            'shimmer_steps': 8,
        },
        'images': [],
    }

    if yaml is None:
        logger.warning('[AVATAR] PyYAML not installed, using default avatar config')
        return default_config

    result = default_config.copy()

    # 1. Load package config first (base settings: directory, size, cycle_interval, etc.)
    package_config_path = Path(__file__).parent / 'pyagentvox.yaml'
    try:
        if package_config_path.exists():
            logger.debug(f'[AVATAR] Loading package config: {package_config_path}')
            with open(package_config_path, encoding='utf-8') as f:
                full_config = yaml.safe_load(f)
                avatar_config = full_config.get('avatar', {})

                for key, value in avatar_config.items():
                    if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                        result[key].update(value)
                    else:
                        result[key] = value
                logger.debug(f'[AVATAR] Package config loaded ({len(avatar_config)} avatar keys)')
        else:
            logger.debug(f'[AVATAR] Package config not found: {package_config_path}')
    except Exception as e:
        logger.warning(f'[AVATAR] Failed to load package config: {e}')

    # 2. Merge CWD config on top (overrides like image registry)
    cwd_config_path = Path.cwd() / 'pyagentvox.yaml'
    if cwd_config_path.exists() and cwd_config_path.resolve() != package_config_path.resolve():
        try:
            logger.debug(f'[AVATAR] Loading CWD config overlay: {cwd_config_path}')
            with open(cwd_config_path, encoding='utf-8') as f:
                cwd_full_config = yaml.safe_load(f)
                cwd_avatar_config = cwd_full_config.get('avatar', {})

                for key, value in cwd_avatar_config.items():
                    if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                        result[key].update(value)
                    else:
                        result[key] = value
                logger.debug(
                    f'[AVATAR] CWD config merged ({len(cwd_avatar_config)} avatar keys, '
                    f'{len(cwd_avatar_config.get("images", []))} images)'
                )
        except Exception as e:
            logger.warning(f'[AVATAR] Failed to load CWD config: {e}')

    # Also check for pyagentvox.json in CWD
    cwd_json_path = Path.cwd() / 'pyagentvox.json'
    if cwd_json_path.exists():
        try:
            logger.debug(f'[AVATAR] Loading CWD JSON config overlay: {cwd_json_path}')
            cwd_json_config = json.loads(cwd_json_path.read_text(encoding='utf-8'))
            cwd_avatar_config = cwd_json_config.get('avatar', {})

            for key, value in cwd_avatar_config.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key].update(value)
                else:
                    result[key] = value
            logger.debug(f'[AVATAR] CWD JSON config merged ({len(cwd_avatar_config)} avatar keys)')
        except Exception as e:
            logger.warning(f'[AVATAR] Failed to load CWD JSON config: {e}')

    # Expand ~ in directory path
    if 'directory' in result:
        result['directory'] = str(Path(result['directory']).expanduser())

    logger.debug(
        f'[AVATAR] Final config: dir={result["directory"]}, size={result["default_size"]}, '
        f'cycle={result["cycle_interval"]}ms, images={len(result["images"])}'
    )
    return result


# ============================================================================
# Constants
# ============================================================================

_CONFIG = load_avatar_config()
AVATAR_DIR = Path(_CONFIG['directory'])
DEFAULT_SIZE = _CONFIG['default_size']
VARIANT_CYCLE_INTERVAL_MS = _CONFIG['cycle_interval']
IDLE_STATES = _CONFIG['idle_states']
EMOTION_HIERARCHY = _CONFIG['emotion_hierarchy']
FILTER_CONFIG = _CONFIG['filters']
ANIMATION_CONFIG = _CONFIG['animation']
IMAGE_REGISTRY = _CONFIG['images']

POSITION_FILE = Path(tempfile.gettempdir()) / 'pyagentvox_avatar_position.json'
FADE_STEPS = 10
FADE_INTERVAL_MS = 30
EMOTION_POLL_INTERVAL_MS = 200
SHIMMER_PEAK_BRIGHTNESS = 2.5  # Peak brightness multiplier for shimmer effect
IDLE_CHECK_INTERVAL_MS = 5000  # Check idle state every 5 seconds
FILTER_POLL_INTERVAL_MS = 500  # Check filter control file every 500ms

# Emotion tag -> avatar filename mapping
EMOTION_AVATAR_MAP: dict[str, str] = {
    'excited': 'excited',
    'thinking': 'thinking',
    'curious': 'curious',
    'warm': 'warm',
    'empathetic': 'warm',
    'determined': 'determined',
    'focused': 'focused',
    'cheerful': 'cheerful',
    'calm': 'calm',
    'apologetic': 'apologetic',
    'neutral': 'cheerful',
    'playful': 'playful',
    'surprised': 'surprised',
}

DEFAULT_AVATAR = 'cheerful'
DETECTIVE_AVATAR = 'detective'
WAITING_STATE = 'waiting'

# Button hover avatar tags -- maps button state to image tag for tag-based lookup.
# These tags are matched against the image registry to find contextual avatars
# that visually communicate the button's function.
BUTTON_HOVER_TAGS: dict[str, str] = {
    'tts_on': 'headphones',    # Headphones image -- "I output voice"
    'tts_off': 'shh',          # Shh gesture -- "voice is muted"
    'stt_on': 'listening',     # Listening pose -- "I hear you"
    'stt_off': 'shh',          # Shh gesture -- "mic is off"
    # Note: 'close' and 'tags' buttons have no hover images
    # - crying.png shows AFTER close button is pressed (in animation)
    # - tags button shows current image (for editing that image's tags)
}

# Button styling colors
BTN_COLOR_ACTIVE = '#2d6b3f'         # Muted green - feature enabled
BTN_COLOR_INACTIVE = '#8b2d2d'       # Muted red - feature disabled
BTN_COLOR_NEUTRAL = '#2a2a2a'        # Dark gray - non-toggle buttons (close, tags)
BTN_COLOR_HOVER_ACTIVE = '#3a8a52'   # Brighter green on hover
BTN_COLOR_HOVER_INACTIVE = '#a83a3a' # Brighter red on hover
BTN_COLOR_HOVER_NEUTRAL = '#555555'  # Lighter gray on hover
BTN_SHADOW_COLOR = '#111111'         # Shadow fill
BTN_SHADOW_OFFSET = 2                # Shadow offset in pixels
BTN_CORNER_RADIUS = 8               # Rounded corner radius

# Avatar image shadow (contoured drop shadow behind Luna)
AVATAR_SHADOW_OFFSET_X = 4          # Shadow horizontal offset
AVATAR_SHADOW_OFFSET_Y = 6          # Shadow vertical offset (light from above)
AVATAR_SHADOW_BLUR_RADIUS = 8       # Gaussian blur radius for soft edges
AVATAR_SHADOW_OPACITY = 100         # Shadow alpha (0-255), 100 = ~39% opacity


# ============================================================================
# Emotion Resolution
# ============================================================================

_emotion_hierarchy_cache: dict[tuple[str, str], str] = {}


def resolve_emotion_hierarchy(emotion: str, avatar_dir: Path) -> str:
    """Resolve an emotion through the hierarchy to find available images.

    Results are cached to avoid repeated filesystem scans (called every 200ms
    by the emotion poll). Cache is keyed on (emotion, avatar_dir_str).

    Resolution order:
    1. Check if emotion has images directly
    2. Check EMOTION_AVATAR_MAP for standard emotion mappings
    3. Check EMOTION_HIERARCHY for specific -> generic fallback
    4. Fall back to 'waiting' state

    Args:
        emotion: Emotion name from TTS (e.g., 'excited', 'celebrating').
        avatar_dir: Directory to check for images.

    Returns:
        Resolved emotion name that has images available.
    """
    cache_key = (emotion, str(avatar_dir))
    if cache_key in _emotion_hierarchy_cache:
        return _emotion_hierarchy_cache[cache_key]

    result = _resolve_emotion_hierarchy_uncached(emotion, avatar_dir)
    _emotion_hierarchy_cache[cache_key] = result
    return result


def _resolve_emotion_hierarchy_uncached(emotion: str, avatar_dir: Path) -> str:
    """Uncached implementation of emotion hierarchy resolution."""
    # 1. Check if emotion has images directly
    if discover_variants(avatar_dir, emotion):
        return emotion

    # 2. Try standard emotion mapping (for the 7 TTS emotions)
    mapped_emotion = EMOTION_AVATAR_MAP.get(emotion)
    if mapped_emotion and discover_variants(avatar_dir, mapped_emotion):
        logger.debug(f'Emotion {emotion} -> {mapped_emotion} (standard mapping)')
        return mapped_emotion

    # 3. Try hierarchy fallback (for specific -> generic mappings)
    generic_emotion = EMOTION_HIERARCHY.get(emotion)
    if generic_emotion:
        # Recursively resolve the generic emotion
        resolved = resolve_emotion_hierarchy(generic_emotion, avatar_dir)
        if resolved != WAITING_STATE:
            logger.debug(f'Emotion {emotion} -> {resolved} (hierarchy fallback)')
            return resolved

    # 4. Last resort: waiting state
    logger.debug(f'Emotion {emotion} -> waiting (no images found)')
    return WAITING_STATE


# ============================================================================
# Tag Filtering System
# ============================================================================

def calculate_tag_similarity(tags1: set[str], tags2: set[str]) -> float:
    """Calculate Jaccard similarity between two tag sets.

    Args:
        tags1: First set of tags.
        tags2: Second set of tags.

    Returns:
        Float between 0.0 (no overlap) and 1.0 (identical).
    """
    if not tags1 and not tags2:
        return 1.0

    intersection = len(tags1 & tags2)
    union = len(tags1 | tags2)

    return intersection / union if union > 0 else 0.0


def filter_images_by_tags(
    images: list[ImageEntry],
    include_tags: list[str],
    exclude_tags: list[str],
    require_all_include: bool
) -> list[ImageEntry]:
    """Filter images based on tag inclusion/exclusion rules.

    Args:
        images: All registered images.
        include_tags: If non-empty, only images with these tags pass.
        exclude_tags: Images with any of these tags are excluded.
        require_all_include: If True, image must have ALL include tags;
                            If False, image must have ANY include tag.

    Returns:
        Filtered list of images.
    """
    filtered = []

    # Normalize tags to lowercase for case-insensitive matching
    include_set = {tag.lower() for tag in include_tags}
    exclude_set = {tag.lower() for tag in exclude_tags}

    for img in images:
        img_tags = img.tag_set

        # Exclude filter (highest priority)
        if exclude_set and any(tag in img_tags for tag in exclude_set):
            continue

        # Include filter
        if include_set:
            if require_all_include:
                # Must have ALL include tags
                if not include_set.issubset(img_tags):
                    continue
            else:
                # Must have ANY include tag
                if not any(tag in img_tags for tag in include_set):
                    continue

        filtered.append(img)

    return filtered


def load_image_registry(avatar_dir: Path, registry_config: list[dict]) -> list[ImageEntry]:
    """Load image registry from config, resolving relative paths.

    Args:
        avatar_dir: Base directory for relative paths.
        registry_config: List of image dicts from config (path, tags).

    Returns:
        List of ImageEntry objects with resolved paths.
    """
    entries = []
    skipped = 0
    missing = 0

    logger.debug(f'[AVATAR] Loading image registry: {len(registry_config)} entries from config')
    logger.debug(f'[AVATAR] Base directory for relative paths: {avatar_dir}')

    for item in registry_config:
        if not isinstance(item, dict) or 'path' not in item or 'tags' not in item:
            logger.warning(f'[AVATAR] Invalid image registry entry (missing path/tags): {item}')
            skipped += 1
            continue

        path = Path(item['path'])
        tags = item['tags']

        # Resolve relative paths
        if not path.is_absolute():
            path = avatar_dir / path

        # Check if file exists
        if not path.exists():
            logger.debug(f'[AVATAR] Image file missing: {path}')
            missing += 1

        # Validate at least one emotion or control tag
        valid_emotions = {
            'cheerful', 'excited', 'calm', 'focused', 'warm', 'empathetic', 'neutral',
            'thinking', 'curious', 'determined', 'apologetic', 'playful', 'surprised',
            'waiting', 'bored', 'sleeping'
        }
        valid_control_tags = {
            'control-tts-hover-on', 'control-tts-hover-off',
            'control-stt-hover-on', 'control-stt-hover-off',
            'control-close-hover',
            'control-tts-clicked', 'control-stt-clicked',
            'control-close-animation',
        }
        tag_set_lower = {tag.lower() for tag in tags}
        has_valid_tag = any(tag in valid_emotions or tag in valid_control_tags
                           for tag in tag_set_lower)

        if not has_valid_tag:
            logger.warning(f'[AVATAR] Image {path.name} has no emotion or control tag, skipping')
            skipped += 1
            continue

        entries.append(ImageEntry(path=path, tags=tags))

    logger.info(
        f'[AVATAR] Image registry loaded: {len(entries)} valid, '
        f'{skipped} skipped, {missing} missing files'
    )
    return entries


# ============================================================================
# Emotion File IPC
# ============================================================================

def get_emotion_file_path(pid: int) -> Path:
    """Get the path to the emotion IPC temp file for a given PID.

    Args:
        pid: Process ID of the PyAgentVox main process.

    Returns:
        Path to the emotion state file.
    """
    return Path(tempfile.gettempdir()) / f'pyagentvox_avatar_emotion_{pid}.txt'


def write_emotion_state(pid: int, emotion: str) -> None:
    """Write the current emotion state to the IPC temp file.

    Called by the TTS playback system when audio starts/stops.

    Args:
        pid: Process ID of the PyAgentVox main process.
        emotion: Emotion name (e.g., 'excited', 'waiting').
    """
    emotion_file = get_emotion_file_path(pid)
    with contextlib.suppress(OSError):
        emotion_file.write_text(emotion, encoding='utf-8')
        logger.debug(f'Wrote emotion state: {emotion}')


def read_emotion_state(pid: int) -> str | None:
    """Read the current emotion state from the IPC temp file.

    Args:
        pid: Process ID of the PyAgentVox main process.

    Returns:
        Emotion name string, or None if file doesn't exist or is unreadable.
    """
    emotion_file = get_emotion_file_path(pid)
    try:
        if emotion_file.exists():
            return emotion_file.read_text(encoding='utf-8').strip()
    except OSError:
        pass
    return None


def cleanup_emotion_file(pid: int) -> None:
    """Remove the emotion IPC temp file.

    Args:
        pid: Process ID of the PyAgentVox main process.
    """
    emotion_file = get_emotion_file_path(pid)
    with contextlib.suppress(OSError):
        if emotion_file.exists():
            emotion_file.unlink()


def get_filter_control_file_path(pid: int) -> Path:
    """Get the path to the filter control IPC temp file for a given PID.

    Args:
        pid: Process ID of the PyAgentVox main process.

    Returns:
        Path to the filter control file.
    """
    return Path(tempfile.gettempdir()) / f'agent_avatar_filter_{pid}.txt'


def write_filter_command(pid: int, command: str) -> None:
    """Write a filter command to the IPC temp file.

    Args:
        pid: Process ID of the PyAgentVox main process.
        command: Filter command (e.g., 'include:casual,summer', 'reset').
    """
    filter_file = get_filter_control_file_path(pid)
    with contextlib.suppress(OSError):
        filter_file.write_text(command, encoding='utf-8')
        logger.debug(f'Wrote filter command: {command}')


# ============================================================================
# Image Variant Discovery
# ============================================================================

def discover_variants(avatar_dir: Path, emotion: str) -> list[Path]:
    """Discover all image variants for a given emotion.

    Looks for images in the emotion subdirectory, supporting multiple formats
    (.png, .jpg, .jpeg, .webp). Falls back to root directory if subdirectory is
    missing or empty.

    Args:
        avatar_dir: Directory containing avatar images (or emotion subdirectories).
        emotion: Base emotion name (e.g., 'excited', 'waiting').

    Returns:
        Sorted list of image paths. Empty if no images found.
    """
    variants: list[Path] = []
    supported_formats = ['*.png', '*.jpg', '*.jpeg', '*.webp']

    if not avatar_dir.exists():
        logger.warning(f'[AVATAR] Avatar directory does not exist: {avatar_dir}')
        return variants

    # Check for emotion subdirectory first (e.g., ~/.claude/luna/excited/)
    emotion_subdir = avatar_dir / emotion
    if emotion_subdir.is_dir():
        for pattern in supported_formats:
            variants.extend(sorted(emotion_subdir.glob(pattern)))
        if variants:
            logger.debug(f'[AVATAR] discover_variants("{emotion}"): {len(variants)} from subdirectory')
            return variants
        # Empty subdirectory - fall through to root directory check
        logger.debug(f'[AVATAR] discover_variants("{emotion}"): subdirectory empty, checking root')

    # Fall back to root directory with emotion prefix (e.g., excited.png, excited-1.png)
    for pattern in supported_formats:
        # Base image (e.g., excited.png)
        ext = pattern[1:]  # Remove leading *
        base_path = avatar_dir / f'{emotion}{ext}'
        if base_path.exists():
            variants.append(base_path)

        # Numbered variants (e.g., excited-1.png, excited-2.png)
        for variant_path in sorted(avatar_dir.glob(f'{emotion}-[0-9]*{ext}')):
            stem = variant_path.stem
            suffix = stem[len(emotion) + 1:]  # After "emotion-"
            if suffix.isdigit():
                variants.append(variant_path)

    result = list(dict.fromkeys(variants))  # Remove duplicates while preserving order
    logger.debug(f'[AVATAR] discover_variants("{emotion}"): {len(result)} from root directory')
    return result


# ============================================================================
# Position Persistence
# ============================================================================

def _load_position() -> tuple[int, int] | None:
    """Load saved window position from temp file.

    Returns:
        Tuple of (x, y) coordinates, or None if no saved position.
    """
    logger.debug(f'[AVATAR] Looking for saved position: {POSITION_FILE}')
    try:
        if POSITION_FILE.exists():
            data = json.loads(POSITION_FILE.read_text(encoding='utf-8'))
            return (int(data['x']), int(data['y']))
    except (json.JSONDecodeError, KeyError, ValueError, OSError):
        pass
    return None


def _save_position(x: int, y: int) -> None:
    """Save window position to temp file.

    Args:
        x: Window X coordinate.
        y: Window Y coordinate.
    """
    with contextlib.suppress(OSError):
        POSITION_FILE.write_text(
            json.dumps({'x': x, 'y': y}),
            encoding='utf-8'
        )


# ============================================================================
# Valid Tag Constants (imported from avatar_tags if available, else inline)
# ============================================================================

try:
    from pyagentvox.avatar_tags import VALID_CONTROL_TAGS, VALID_EMOTIONS
except ImportError:
    VALID_EMOTIONS = {
        'cheerful', 'excited', 'calm', 'focused', 'warm', 'empathetic', 'neutral',
        'thinking', 'curious', 'determined', 'apologetic', 'playful', 'surprised',
        'waiting', 'bored', 'sleeping',
    }
    VALID_CONTROL_TAGS = {
        'control-tts-hover-on', 'control-tts-hover-off',
        'control-stt-hover-on', 'control-stt-hover-off',
        'control-close-hover',
        'control-tts-clicked', 'control-stt-clicked',
        'control-close-animation',
    }


# ============================================================================
# Tag Editor Dialog
# ============================================================================

class TagEditorDialog:
    """Modal dialog for editing image tags with a checklist UI.

    Displays all known tags in the system organized by category (emotions,
    control tags, custom tags) with checkboxes. The user can check/uncheck
    tags and save changes back to the config file.

    Args:
        parent: Parent tkinter window.
        image_entry: The ImageEntry being edited.
        all_tags: Set of all tags across the entire image registry.
        on_save_callback: Called with the new tag list when the user clicks Apply.
    """

    def __init__(
        self,
        parent: tk.Tk | tk.Toplevel,
        image_entry: 'ImageEntry',
        all_tags: set[str],
        on_save_callback: 'callable',
    ) -> None:
        self.image_entry = image_entry
        self.on_save = on_save_callback
        self.tag_vars: dict[str, tk.BooleanVar] = {}

        # Build sorted tag lists by category
        self._emotion_tags = sorted(tag for tag in all_tags if tag.lower() in VALID_EMOTIONS)
        self._control_tags = sorted(tag for tag in all_tags if tag.lower() in VALID_CONTROL_TAGS)
        self._other_tags = sorted(
            tag for tag in all_tags
            if tag.lower() not in VALID_EMOTIONS and tag.lower() not in VALID_CONTROL_TAGS
        )

        # Create modal dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f'Edit Tags - {image_entry.path.name}')
        self.dialog.geometry('420x520')
        self.dialog.resizable(False, True)

        # transient + grab_set can fail on overrideredirect parent windows
        with contextlib.suppress(tk.TclError):
            self.dialog.transient(parent)
        with contextlib.suppress(tk.TclError):
            self.dialog.grab_set()

        self._create_widgets()

        # Center on parent
        self.dialog.update_idletasks()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_w = parent.winfo_width()
        dlg_w = self.dialog.winfo_width()
        x = parent_x + (parent_w - dlg_w) // 2
        self.dialog.geometry(f'+{x}+{parent_y}')

    def _create_widgets(self) -> None:
        """Build the dialog layout: header, tag checklist, and action buttons."""
        current_tags = self.image_entry.tag_set

        # --- Header ---
        header_frame = tk.Frame(self.dialog, padx=10, pady=8)
        header_frame.pack(fill='x')

        tk.Label(
            header_frame,
            text=f'Image: {self.image_entry.path.name}',
            font=('Segoe UI', 10, 'bold'),
            anchor='w',
        ).pack(fill='x')

        # --- Tags Section Label ---
        tk.Label(
            self.dialog,
            text='Tags (check/uncheck):',
            font=('Segoe UI', 9, 'bold'),
            padx=10,
            pady=(4, 2),
            anchor='w',
        ).pack(fill='x')

        # --- Scrollable Checklist ---
        scroll_frame = tk.Frame(self.dialog)
        scroll_frame.pack(fill='both', expand=True, padx=10, pady=4)

        canvas = tk.Canvas(scroll_frame, highlightthickness=0)
        scrollbar = tk.Scrollbar(scroll_frame, orient='vertical', command=canvas.yview)
        inner_frame = tk.Frame(canvas)

        inner_frame.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )
        canvas.create_window((0, 0), window=inner_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        # Enable mouse wheel scrolling
        def _on_mousewheel(event: tk.Event) -> None:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

        canvas.bind_all('<MouseWheel>', _on_mousewheel)
        self.dialog.protocol('WM_DELETE_WINDOW', lambda: self._on_close(canvas, _on_mousewheel))

        row = 0

        # --- Emotion Tags ---
        if self._emotion_tags:
            tk.Label(
                inner_frame,
                text='Emotions:',
                font=('Segoe UI', 8, 'bold'),
            ).grid(row=row, column=0, columnspan=2, sticky='w', pady=(6, 2))
            row += 1

            for i, tag in enumerate(self._emotion_tags):
                var = tk.BooleanVar(value=tag.lower() in current_tags)
                self.tag_vars[tag] = var

                cb = tk.Checkbutton(inner_frame, text=tag, variable=var, anchor='w')
                col = i % 2
                cb.grid(row=row + i // 2, column=col, sticky='w', padx=(12, 4))

            row += (len(self._emotion_tags) + 1) // 2

        # --- Control Tags ---
        if self._control_tags:
            tk.Label(
                inner_frame,
                text='Control Tags:',
                font=('Segoe UI', 8, 'bold'),
            ).grid(row=row, column=0, columnspan=2, sticky='w', pady=(10, 2))
            row += 1

            for i, tag in enumerate(self._control_tags):
                var = tk.BooleanVar(value=tag.lower() in current_tags)
                self.tag_vars[tag] = var

                cb = tk.Checkbutton(inner_frame, text=tag, variable=var, anchor='w')
                col = i % 2
                cb.grid(row=row + i // 2, column=col, sticky='w', padx=(12, 4))

            row += (len(self._control_tags) + 1) // 2

        # --- Other / Custom Tags ---
        if self._other_tags:
            tk.Label(
                inner_frame,
                text='Custom Tags:',
                font=('Segoe UI', 8, 'bold'),
            ).grid(row=row, column=0, columnspan=2, sticky='w', pady=(10, 2))
            row += 1

            for i, tag in enumerate(self._other_tags):
                var = tk.BooleanVar(value=tag.lower() in current_tags)
                self.tag_vars[tag] = var

                cb = tk.Checkbutton(inner_frame, text=tag, variable=var, anchor='w')
                col = i % 2
                cb.grid(row=row + i // 2, column=col, sticky='w', padx=(12, 4))

        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Store canvas ref for cleanup
        self._canvas = canvas
        self._mousewheel_handler = _on_mousewheel

        # --- Action Buttons ---
        btn_frame = tk.Frame(self.dialog, padx=10, pady=10)
        btn_frame.pack(fill='x')

        tk.Button(
            btn_frame,
            text='Cancel',
            command=lambda: self._on_close(canvas, _on_mousewheel),
            width=12,
        ).pack(side='left', padx=4)

        tk.Button(
            btn_frame,
            text='Apply & Save',
            command=self._save_tags,
            width=14,
            bg='#4CAF50',
            fg='white',
        ).pack(side='right', padx=4)

    def _save_tags(self) -> None:
        """Validate and save the updated tags via the callback."""
        new_tags = [tag for tag, var in self.tag_vars.items() if var.get()]

        # Validation: must have at least one emotion or control tag
        has_emotion = any(tag.lower() in VALID_EMOTIONS for tag in new_tags)
        has_control = any(tag.lower() in VALID_CONTROL_TAGS for tag in new_tags)

        if not has_emotion and not has_control:
            messagebox.showerror(
                'Invalid Tags',
                'Image must have at least one emotion tag or control tag.',
                parent=self.dialog,
            )
            return

        # Call save callback and close
        self.on_save(new_tags)
        self._cleanup_bindings()
        self.dialog.destroy()

    def _on_close(self, canvas: tk.Canvas, handler: 'callable') -> None:
        """Clean up bindings and close dialog without saving."""
        self._cleanup_bindings()
        self.dialog.destroy()

    def _cleanup_bindings(self) -> None:
        """Unbind global mousewheel handler to prevent leaks."""
        with contextlib.suppress(tk.TclError):
            self.dialog.unbind_all('<MouseWheel>')


# ============================================================================
# Avatar Widget
# ============================================================================

class AvatarWidget:
    """Floating avatar widget that displays mood-based images.

    Creates a transparent, always-on-top Tkinter window that monitors
    the TTS emotion state file and displays the corresponding avatar
    image, cycling through variants when multiple exist.

    Args:
        avatar_dir: Path to directory containing avatar images.
        size: Widget size in pixels (width; height adjusts to aspect ratio).
        monitor_pid: PID of the PyAgentVox main process to monitor for emotion
            changes. If None, the widget shows the waiting/default state.
    """

    def __init__(
        self,
        avatar_dir: Path | None = None,
        size: int = DEFAULT_SIZE,
        monitor_pid: int | None = None,
    ) -> None:
        self.avatar_dir = avatar_dir or AVATAR_DIR
        self.size = size
        self.monitor_pid = monitor_pid
        self.current_emotion: str = ''  # Empty so _switch_emotion() doesn't skip initial display
        self.current_avatar_path: Path | None = None
        self._running = True
        self._fade_alpha = 1.0
        self._fade_after_id: str | None = None  # Track fade animation callback for cancellation

        # Idle timer state (for bored/sleeping transitions)
        self._idle_start_time: float | None = None
        self._idle_check_after_id: str | None = None
        self._is_speaking = False  # Track whether TTS is currently playing

        # Variant cycling state
        self._variant_cache: dict[str, list[Path]] = {}
        self._current_variant_index: int = 0
        self._cycle_after_id: str | None = None

        # Tag filtering state
        self._image_registry: list[ImageEntry] = []
        self._include_tags: list[str] = FILTER_CONFIG['include_tags'].copy()
        self._exclude_tags: list[str] = FILTER_CONFIG['exclude_tags'].copy()
        self._require_all_include: bool = FILTER_CONFIG['require_all_include']
        self._filter_poll_after_id: str | None = None

        # Animation settings
        self._shimmer_threshold: float = ANIMATION_CONFIG['shimmer_threshold']
        self._shimmer_duration: int = ANIMATION_CONFIG['shimmer_duration']
        self._shimmer_steps: int = ANIMATION_CONFIG['shimmer_steps']
        self._shimmer_after_id: str | None = None  # Track shimmer animation callback for cancellation

        # Speaking indicator state
        self._speaking_indicator_id: int | None = None  # Canvas item ID for speech bubble
        self._speaking_dot_ids: list[int] = []  # Canvas item IDs for animated dots
        self._speaking_anim_after_id: str | None = None  # After ID for dot animation
        self._speaking_anim_frame: int = 0  # Current animation frame

        # Hover glow state
        self._glow_item_id: int | None = None  # Canvas item ID for glow effect

        # Load image registry from config
        self._image_registry = load_image_registry(self.avatar_dir, IMAGE_REGISTRY)

        # Interactive controls state
        self._buttons_visible = False
        self._preview_active = False
        self._preview_emotion: str | None = None
        self._tts_enabled = True
        self._stt_enabled = True
        self._tag_editor_open = False

        # Canvas-based control button IDs (bg rect + text for each)
        self._ctrl_btn_ids: dict[str, tuple[int, int]] = {}  # name -> (bg_id, text_id)

        # Hover lock state (pauses variant cycling while mouse is over avatar)
        self._hover_locked = False
        self._was_cycling = False

        logger.info(f'[AVATAR] Avatar dir: {self.avatar_dir}')
        logger.debug(f'[AVATAR] Avatar dir exists: {self.avatar_dir.exists()}')
        if monitor_pid:
            logger.info(f'[AVATAR] Monitoring PID: {monitor_pid}')
        logger.debug(f'[AVATAR] Image registry: {len(self._image_registry)} entries')
        logger.debug(f'[AVATAR] Widget size: {self.size}px')

        # Image cache: file_path_str -> PhotoImage
        self._image_cache: dict[str, ImageTk.PhotoImage] = {}

        # Build window
        logger.debug('[AVATAR] Creating tkinter root window')
        self._root = tk.Tk()
        self._root.title('Luna Avatar')

        logger.debug('[AVATAR] Setting overrideredirect(True)')
        self._root.overrideredirect(True)

        logger.debug('[AVATAR] Setting window attributes: topmost=True')
        self._root.attributes('-topmost', True)

        # Transparent background - use a distinctive color that won't appear in real images.
        # Previously #010101 (near-black) which caused thousands of dark image pixels to
        # become transparent holes, potentially making the avatar invisible.
        self._transparent_color = '#F0F0F1'
        self._transparent_rgb = (240, 240, 241)  # Must match _transparent_color
        logger.debug(f'[AVATAR] Setting transparent color: {self._transparent_color}')
        self._root.attributes('-transparentcolor', self._transparent_color)
        self._root.configure(bg=self._transparent_color)

        # Canvas for image display
        self._canvas = tk.Canvas(
            self._root,
            width=self.size,
            height=self.size,
            bg=self._transparent_color,
            highlightthickness=0,
            bd=0,
        )
        self._canvas.pack(fill=tk.BOTH, expand=True)
        logger.debug(f'[AVATAR] Canvas created: {self.size}x{self.size}')

        # Image item on canvas (anchored to bottom-center)
        self._image_item = self._canvas.create_image(
            self.size // 2, self.size,
            anchor=tk.S,
        )

        # Log screen dimensions for positioning diagnostics
        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()
        logger.debug(f'[AVATAR] Screen dimensions: {screen_w}x{screen_h}')

        # Position window
        saved_pos = _load_position()
        if saved_pos:
            # Validate saved position is still on-screen
            pos_x, pos_y = saved_pos
            if 0 <= pos_x < screen_w and 0 <= pos_y < screen_h:
                self._root.geometry(f'{self.size}x{self.size}+{pos_x}+{pos_y}')
                logger.debug(f'[AVATAR] Restored saved position: x={pos_x}, y={pos_y}')
            else:
                logger.warning(
                    f'[AVATAR] Saved position off-screen: x={pos_x}, y={pos_y} '
                    f'(screen: {screen_w}x{screen_h}), using default'
                )
                self._position_bottom_right()
        else:
            logger.debug('[AVATAR] No saved position, using bottom-right default')
            self._position_bottom_right()

        # Ensure window is visible after setup
        self._root.deiconify()
        self._root.lift()
        logger.debug('[AVATAR] Called deiconify() and lift() to ensure visibility')

        # Log final window geometry
        self._root.update_idletasks()
        final_geometry = self._root.geometry()
        logger.debug(f'[AVATAR] Final window geometry: {final_geometry}')

        # Bind events
        self._canvas.bind('<Button-3>', self._on_right_click)
        self._canvas.bind('<ButtonPress-1>', self._on_drag_start)
        self._canvas.bind('<B1-Motion>', self._on_drag_motion)
        self._canvas.bind('<ButtonRelease-1>', self._on_drag_release)
        self._canvas.bind('<Enter>', self._on_mouse_enter)
        self._canvas.bind('<Leave>', self._on_mouse_leave)
        self._root.protocol('WM_DELETE_WINDOW', self.stop)

        # Drag state
        self._drag_x = 0
        self._drag_y = 0
        self._drag_prev_hwnd = None  # Store foreground window before drag

        # Make click-through on Windows (pass clicks to windows behind)
        if sys.platform == 'win32':
            self._setup_click_through()

        # Load initial avatar (waiting state)
        logger.debug('[AVATAR] Loading initial avatar (waiting state)')
        self._switch_emotion(WAITING_STATE)

        logger.info(f'[AVATAR] Widget initialized ({self.size}x{self.size}), geometry: {final_geometry}')

    def _position_bottom_right(self) -> None:
        """Position window in the bottom-right corner, anchored to bottom."""
        margin = 20
        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()
        x = screen_w - self.size - margin
        # Anchor to very bottom of screen (above taskbar ~40px)
        y = screen_h - self.size - 40
        geometry = f'{self.size}x{self.size}+{x}+{y}'
        self._root.geometry(geometry)
        logger.debug(f'[AVATAR] Positioned bottom-right: x={x}, y={y} (screen: {screen_w}x{screen_h})')

    def _setup_click_through(self) -> None:
        """Make the window click-through on Windows using win32 API.

        The transparent background already lets clicks pass through empty areas.
        We keep drag and right-click events on the actual image pixels.
        """
        # Note: We do NOT set WS_EX_TRANSPARENT because we want drag + right-click.
        # The transparent background already lets clicks pass through empty areas.
        pass

    def _get_variants(self, emotion: str) -> list[Path]:
        """Get all image variants for an emotion, with caching.

        Uses tag-based lookup if image registry is populated, otherwise falls
        back to directory-based discovery for backward compatibility.

        Args:
            emotion: Emotion name (e.g., 'excited', 'waiting').

        Returns:
            List of image paths. Falls back to cheerful.png for empty results
            on 'waiting' emotion.
        """
        if emotion not in self._variant_cache:
            variants: list[Path] = []
            logger.debug(f'[AVATAR] Resolving variants for emotion: {emotion}')

            # Tag-based lookup (if registry is populated)
            if self._image_registry:
                # Map emotion to avatar base name for consistency
                avatar_name = EMOTION_AVATAR_MAP.get(emotion, emotion)
                logger.debug(f'[AVATAR] Tag lookup: emotion={emotion} -> avatar_name={avatar_name}')

                # Get all images with this emotion tag (exclude all control tags)
                emotion_images = [
                    img for img in self._image_registry
                    if (avatar_name.lower() in img.tag_set and
                        not any(tag.startswith('control') for tag in img.tag_set))
                ]
                logger.debug(f'[AVATAR] Found {len(emotion_images)} images with tag "{avatar_name}"')

                # Apply tag filters
                if emotion_images:
                    filtered = filter_images_by_tags(
                        emotion_images,
                        self._include_tags,
                        self._exclude_tags,
                        self._require_all_include
                    )
                    variants = [img.path for img in filtered]
                    logger.debug(f'[AVATAR] After filtering: {len(variants)} variants')

                # Fallback: if filters excluded everything, ignore filters for this emotion
                if not variants and emotion_images:
                    variants = [img.path for img in emotion_images]
                    logger.warning(
                        f'[AVATAR] Tag filters excluded all {emotion} images, ignoring filters'
                    )
            else:
                logger.debug('[AVATAR] No image registry, using directory-based discovery')

            # Directory-based discovery (backward compatibility)
            if not variants:
                avatar_name = EMOTION_AVATAR_MAP.get(emotion, emotion)
                variants = discover_variants(self.avatar_dir, avatar_name)
                logger.debug(
                    f'[AVATAR] Directory discovery for "{avatar_name}": {len(variants)} variants'
                )

            # For waiting state, try 'waiting' first, then fall back to cheerful
            if not variants and emotion == WAITING_STATE:
                cheerful_path = self.avatar_dir / f'{DEFAULT_AVATAR}.png'
                if cheerful_path.exists():
                    variants = [cheerful_path]
                    logger.debug(f'[AVATAR] Waiting fallback to cheerful: {cheerful_path}')
                else:
                    logger.warning(f'[AVATAR] No waiting images AND no {DEFAULT_AVATAR}.png found!')

            # For any emotion with no variants, fall back to default avatar
            if not variants and emotion != WAITING_STATE:
                default_path = self.avatar_dir / f'{DEFAULT_AVATAR}.png'
                if default_path.exists():
                    variants = [default_path]
                    logger.warning(f'[AVATAR] No variants for {emotion}, falling back to {DEFAULT_AVATAR}')
                else:
                    logger.error(f'[AVATAR] No variants for {emotion} and no fallback image exists!')

            self._variant_cache[emotion] = variants
            logger.debug(
                f'[AVATAR] Cached {len(variants)} variant(s) for "{emotion}"'
                + (f': {[p.name for p in variants[:3]]}...' if len(variants) > 3 else
                   f': {[p.name for p in variants]}' if variants else '')
            )

        return self._variant_cache[emotion]

    def _load_image_from_path(self, image_path: Path) -> ImageTk.PhotoImage | None:
        """Load and cache an image at the current widget size.

        Preserves aspect ratio and composites onto a transparent background
        anchored to the bottom of the canvas.

        Args:
            image_path: Path to the PNG image file.

        Returns:
            Tkinter-compatible PhotoImage, or None if loading failed.
        """
        cache_key = f'{image_path}_{self.size}'
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]

        if not image_path.exists():
            logger.error(f'[AVATAR] Image file does not exist: {image_path}')
            return None

        try:
            logger.debug(f'[AVATAR] Loading image: {image_path.name} ({image_path.stat().st_size} bytes)')
            img = Image.open(image_path)
            img = img.convert('RGBA')
            logger.debug(f'[AVATAR] Image dimensions: {img.width}x{img.height}, mode={img.mode}')

            # Maintain aspect ratio, fit within size (leave room for shadow offset)
            shadow_pad = max(AVATAR_SHADOW_OFFSET_X, AVATAR_SHADOW_OFFSET_Y) + AVATAR_SHADOW_BLUR_RADIUS
            effective_size = self.size - shadow_pad
            img.thumbnail((effective_size, effective_size), Image.Resampling.LANCZOS)

            # Create background matching window transparent color
            r, g, b = self._transparent_rgb
            bg = Image.new('RGBA', (self.size, self.size), (r, g, b, 0))
            offset_x = (self.size - img.width) // 2
            offset_y = self.size - img.height  # Anchor to bottom

            # Generate contoured drop shadow from image alpha channel
            alpha = img.split()[3]  # Extract alpha channel
            # Clamp alpha to shadow opacity (fast vectorized via point())
            clamped_alpha = alpha.point(lambda a: min(a, AVATAR_SHADOW_OPACITY))
            # Create solid black shadow with clamped alpha shape
            shadow = Image.new('RGBA', img.size, (0, 0, 0, 0))
            shadow.putalpha(clamped_alpha)
            # Blur the shadow for soft edges
            shadow = shadow.filter(ImageFilter.GaussianBlur(radius=AVATAR_SHADOW_BLUR_RADIUS))

            # Paste shadow first (offset), then image on top
            shadow_x = offset_x + AVATAR_SHADOW_OFFSET_X
            shadow_y = offset_y + AVATAR_SHADOW_OFFSET_Y
            bg.paste(shadow, (shadow_x, shadow_y), shadow)
            bg.paste(img, (offset_x, offset_y), img)

            photo = ImageTk.PhotoImage(bg)
            self._image_cache[cache_key] = photo
            logger.debug(f'[AVATAR] Image cached: {image_path.name} (scaled to {img.width}x{img.height})')
            return photo
        except Exception as e:
            logger.error(f'[AVATAR] Failed to load image {image_path}: {e}', exc_info=True)
            return None

    def _display_variant(self, image_path: Path) -> None:
        """Display a specific image variant on the canvas.

        Args:
            image_path: Path to the image to display.
        """
        photo = self._load_image_from_path(image_path)
        if photo:
            self._canvas.itemconfig(self._image_item, image=photo)
            # Keep reference to prevent garbage collection
            self._canvas._current_photo = photo  # type: ignore[attr-defined]
            self.current_avatar_path = image_path
            logger.debug(f'[AVATAR] Displaying: {image_path.name}')
        else:
            logger.warning(f'[AVATAR] Failed to display variant: {image_path}')

    def _switch_emotion(self, emotion: str, force_shimmer: bool = False) -> None:
        """Switch to a new emotion, resetting variant cycling.

        Decides between immediate switch and shimmer animation based on tag similarity.

        Args:
            emotion: New emotion name to display.
            force_shimmer: Force shimmer animation regardless of tag similarity.
        """
        # Allow initial load even when emotion matches (no image displayed yet)
        if emotion == self.current_emotion and self.current_avatar_path is not None:
            return

        old_emotion = self.current_emotion
        logger.debug(f'[AVATAR] Switching emotion: {old_emotion} -> {emotion}')
        variants = self._get_variants(emotion)

        if not variants:
            logger.warning(f'No variants found for emotion: {emotion}')
            return

        # Choose a random variant for visual variety
        new_variant_index = random.randint(0, len(variants) - 1)
        new_image_path = variants[new_variant_index]

        # Determine if we should use shimmer animation based on tag similarity
        use_shimmer = force_shimmer
        if not use_shimmer and self._image_registry and self.current_avatar_path:
            # Get tags for current and new images
            current_tags = set()
            new_tags = set()

            for img in self._image_registry:
                if img.path == self.current_avatar_path:
                    current_tags = img.tag_set
                if img.path == new_image_path:
                    new_tags = img.tag_set

            # Calculate similarity and decide animation type
            if current_tags and new_tags:
                similarity = calculate_tag_similarity(current_tags, new_tags)
                use_shimmer = similarity < self._shimmer_threshold
                logger.debug(f'Tag similarity: {similarity:.2f}, shimmer={use_shimmer}')

        # Execute appropriate transition
        if use_shimmer:
            self._shimmer_transition(emotion, new_image_path)
        else:
            # Use immediate switch (no fade for now to keep it simple)
            self.current_emotion = emotion
            self._current_variant_index = new_variant_index

            # Cancel any existing cycle timer
            if self._cycle_after_id is not None:
                with contextlib.suppress(tk.TclError):
                    self._root.after_cancel(self._cycle_after_id)
                self._cycle_after_id = None

            self._display_variant(new_image_path)

            # Start cycling if multiple variants exist
            if len(variants) > 1:
                self._cycle_after_id = self._root.after(
                    VARIANT_CYCLE_INTERVAL_MS, self._cycle_variant
                )

            logger.info(f'Emotion: {old_emotion} -> {emotion} ({len(variants)} variant(s))')

    def _cycle_variant(self) -> None:
        """Cycle to the next variant image for the current emotion.

        Respects hover lock -- if the mouse is hovering over the avatar,
        cycling is paused until the mouse leaves.
        """
        if not self._running:
            return

        # Don't cycle while hover-locked (user is inspecting)
        if self._hover_locked:
            self._cycle_after_id = None
            return

        variants = self._get_variants(self.current_emotion)
        if len(variants) <= 1:
            return

        # Advance to next variant
        self._current_variant_index = (self._current_variant_index + 1) % len(variants)
        self._display_variant(variants[self._current_variant_index])

        # Schedule next cycle
        self._cycle_after_id = self._root.after(
            VARIANT_CYCLE_INTERVAL_MS, self._cycle_variant
        )

    def _fade_transition(self, new_emotion: str) -> None:
        """Perform a smooth fade transition to a new emotion.

        Fades out the current avatar, swaps the emotion, then fades back in.

        Args:
            new_emotion: Emotion name to transition to.
        """
        if new_emotion == self.current_emotion:
            return

        # Cancel any in-progress fade to prevent overlapping animations
        if self._fade_after_id is not None:
            with contextlib.suppress(tk.TclError):
                self._root.after_cancel(self._fade_after_id)
            self._fade_after_id = None

        self._fade_step = 0
        self._pending_emotion = new_emotion
        self._fade_out()

    def _fade_out(self) -> None:
        """Animate fade-out step."""
        if not self._running:
            return

        self._fade_step += 1
        alpha = max(0.0, 1.0 - (self._fade_step / FADE_STEPS))

        if sys.platform == 'win32':
            with contextlib.suppress(tk.TclError):
                self._root.attributes('-alpha', alpha)

        if self._fade_step >= FADE_STEPS:
            # Swap emotion at full transparency
            self._switch_emotion(self._pending_emotion)
            self._fade_step = 0
            self._fade_after_id = self._root.after(FADE_INTERVAL_MS, self._fade_in)
        else:
            self._fade_after_id = self._root.after(FADE_INTERVAL_MS, self._fade_out)

    def _fade_in(self) -> None:
        """Animate fade-in step."""
        if not self._running:
            return

        self._fade_step += 1
        alpha = min(1.0, self._fade_step / FADE_STEPS)

        if sys.platform == 'win32':
            with contextlib.suppress(tk.TclError):
                self._root.attributes('-alpha', alpha)

        if self._fade_step < FADE_STEPS:
            self._fade_after_id = self._root.after(FADE_INTERVAL_MS, self._fade_in)
        else:
            self._fade_after_id = None

    def _shimmer_transition(self, new_emotion: str, new_image_path: Path) -> None:
        """Animate a shimmer/sparkle brightness pulse during emotion transitions.

        Animation sequence:
        1. Current image brightens to peak (shimmer out)
        2. At peak brightness, swap to new image
        3. New image dims from peak back to normal (shimmer in)

        The effect creates a brief magical glow without distorting the image.

        Args:
            new_emotion: Emotion to transition to.
            new_image_path: Path to the new image to display.
        """
        if not self._running:
            return

        # Cancel any in-progress shimmer to prevent overlapping animations
        if self._shimmer_after_id is not None:
            with contextlib.suppress(tk.TclError):
                self._root.after_cancel(self._shimmer_after_id)
            self._shimmer_after_id = None

        steps = self._shimmer_steps
        delay_ms = max(16, int(self._shimmer_duration / (steps * 2)))
        peak = SHIMMER_PEAK_BRIGHTNESS

        # Pre-load source images for shimmer frames
        shimmer_out_source = self._load_shimmer_source(self.current_avatar_path)
        shimmer_in_source = self._load_shimmer_source(new_image_path)

        def ease_out_quad(t: float) -> float:
            """Quadratic ease-out: fast start, slow end."""
            return t * (2.0 - t)

        def ease_in_quad(t: float) -> float:
            """Quadratic ease-in: slow start, fast end."""
            return t * t

        # Phase 1: Brighten current image to peak
        def shimmer_out(step: int = 0) -> None:
            if not self._running or step >= steps:
                # Swap to new image at peak brightness
                old_emotion = self.current_emotion
                self.current_emotion = new_emotion
                self._current_variant_index = 0
                self.current_avatar_path = new_image_path
                logger.info(f'Emotion: {old_emotion} -> {new_emotion} (shimmer animation)')

                # Start shimmer-in with the new image
                self._shimmer_after_id = self._root.after(delay_ms, lambda: shimmer_in(0))
                return

            t = ease_out_quad(step / steps)
            brightness = 1.0 + (peak - 1.0) * t
            self._render_shimmer_frame(shimmer_out_source, brightness)
            self._shimmer_after_id = self._root.after(delay_ms, lambda s=step: shimmer_out(s + 1))

        # Phase 2: Dim new image from peak back to normal
        def shimmer_in(step: int = 0) -> None:
            if not self._running or step >= steps:
                # Restore normal display and clean up
                self._display_variant(new_image_path)
                self._shimmer_after_id = None
                # Resume variant cycling if multiple variants exist
                variants = self._get_variants(self.current_emotion)
                if len(variants) > 1 and self._cycle_after_id is None:
                    self._cycle_after_id = self._root.after(
                        VARIANT_CYCLE_INTERVAL_MS, self._cycle_variant
                    )
                return

            t = ease_in_quad(step / steps)
            brightness = peak - (peak - 1.0) * t
            self._render_shimmer_frame(shimmer_in_source, brightness)
            self._shimmer_after_id = self._root.after(delay_ms, lambda s=step: shimmer_in(s + 1))

        # Cancel any existing cycle timer
        if self._cycle_after_id is not None:
            with contextlib.suppress(tk.TclError):
                self._root.after_cancel(self._cycle_after_id)
            self._cycle_after_id = None

        # Start shimmer-out animation
        shimmer_out(0)

    def _load_shimmer_source(self, image_path: Path | None) -> Image.Image | None:
        """Load and composite an image for shimmer animation frames.

        Returns the image fitted to widget size with aspect ratio preserved
        and bottom-anchored on transparent background, matching the normal
        display pipeline exactly.

        Args:
            image_path: Path to the image file.

        Returns:
            Composited RGBA Image at (self.size x self.size), or None.
        """
        if not image_path or not image_path.exists():
            return None
        try:
            img = Image.open(image_path).convert('RGBA')
            img.thumbnail((self.size, self.size), Image.Resampling.LANCZOS)

            # Composite onto transparent background, bottom-anchored
            r, g, b = self._transparent_rgb
            bg = Image.new('RGBA', (self.size, self.size), (r, g, b, 0))
            offset_x = (self.size - img.width) // 2
            offset_y = self.size - img.height
            bg.paste(img, (offset_x, offset_y), img)
            return bg
        except Exception as e:
            logger.error(f'[AVATAR] Failed to load shimmer source {image_path}: {e}')
            return None

    def _render_shimmer_frame(self, source: Image.Image | None, brightness: float) -> None:
        """Render a single frame of the shimmer animation.

        Applies a brightness enhancement to the source image while preserving
        the alpha channel (transparent pixels stay transparent).

        Args:
            source: Pre-composited RGBA image at (self.size x self.size).
            brightness: Brightness multiplier (1.0 = normal, >1.0 = brighter).
        """
        if source is None:
            return
        try:
            # Split alpha channel before brightness adjustment
            r_chan, g_chan, b_chan, a_chan = source.split()

            # Apply brightness to RGB channels only
            rgb_img = Image.merge('RGB', (r_chan, g_chan, b_chan))
            enhancer = ImageEnhance.Brightness(rgb_img)
            brightened = enhancer.enhance(brightness)

            # Recombine with original alpha channel
            result = brightened.convert('RGBA')
            result.putalpha(a_chan)

            photo = ImageTk.PhotoImage(result)
            self._canvas.itemconfig(self._image_item, image=photo)
            self._canvas._current_photo = photo  # type: ignore[attr-defined]
        except Exception as e:
            logger.error(f'[AVATAR] Failed to render shimmer frame: {e}')

    # ========================================================================
    # Idle Timer Management
    # ========================================================================

    def _start_idle_timer(self) -> None:
        """Start tracking idle time for bored/sleeping transitions."""
        if self._idle_start_time is None:
            self._idle_start_time = time.time()
            logger.debug('Idle timer started')

        # Schedule idle state check
        if self._idle_check_after_id is None and self._running:
            self._idle_check_after_id = self._root.after(
                IDLE_CHECK_INTERVAL_MS, self._check_idle_state
            )

    def _reset_idle_timer(self) -> None:
        """Reset idle timer (called when TTS/STT activity resumes).

        Cancels any pending idle check and clears the start time so the
        next _start_idle_timer call begins fresh.
        """
        self._idle_start_time = None
        if self._idle_check_after_id is not None:
            with contextlib.suppress(tk.TclError):
                self._root.after_cancel(self._idle_check_after_id)
            self._idle_check_after_id = None
        logger.debug('Idle timer reset')

    def _check_idle_state(self) -> None:
        """Check idle duration and transition to bored/sleeping if needed."""
        if not self._running or self._is_speaking:
            # Don't check idle state while speaking
            self._idle_check_after_id = None
            return

        if self._idle_start_time is None:
            # Start timer if not running
            self._start_idle_timer()

        idle_duration = time.time() - (self._idle_start_time or time.time())

        # Determine idle state based on duration
        target_emotion = WAITING_STATE
        if idle_duration >= IDLE_STATES['sleeping']:
            target_emotion = 'sleeping'
        elif idle_duration >= IDLE_STATES['bored']:
            target_emotion = 'bored'

        # Transition if state changed
        if target_emotion != self.current_emotion:
            logger.info(f'Idle transition: {self.current_emotion} -> {target_emotion} (idle: {idle_duration:.0f}s)')
            self._fade_transition(target_emotion)

        # Schedule next check
        if self._running:
            self._idle_check_after_id = self._root.after(
                IDLE_CHECK_INTERVAL_MS, self._check_idle_state
            )

    # ========================================================================
    # Speaking Indicator
    # ========================================================================

    def _show_speaking_indicator(self) -> None:
        """Show a speech bubble with animated dots when TTS is speaking."""
        if self._speaking_indicator_id is not None:
            return
        cx = 45
        cy = 25
        bw, bh = 50, 28
        self._speaking_indicator_id = self._canvas.create_oval(
            cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2,
            fill='white', outline='#cccccc', width=1,
        )
        dot_radius = 3
        dot_spacing = 12
        self._speaking_dot_ids = []
        for i in range(3):
            dot_x = cx - dot_spacing + (i * dot_spacing)
            dot_id = self._canvas.create_oval(
                dot_x - dot_radius, cy - dot_radius, dot_x + dot_radius, cy + dot_radius,
                fill='#aaaaaa', outline='',
            )
            self._speaking_dot_ids.append(dot_id)
        tri_x = cx + bw // 2 - 8
        tri_y = cy + bh // 2
        self._speaking_tri_id = self._canvas.create_polygon(
            tri_x, tri_y - 2, tri_x + 6, tri_y + 8, tri_x - 6, tri_y - 2,
            fill='white', outline='#cccccc', width=1,
        )
        self._speaking_anim_frame = 0
        self._animate_speaking_dots()
        logger.debug('[AVATAR] Speaking indicator shown')

    def _hide_speaking_indicator(self) -> None:
        """Remove the speech bubble indicator from the canvas."""
        if self._speaking_indicator_id is not None:
            self._canvas.delete(self._speaking_indicator_id)
            self._speaking_indicator_id = None
        for dot_id in self._speaking_dot_ids:
            self._canvas.delete(dot_id)
        self._speaking_dot_ids = []
        if hasattr(self, '_speaking_tri_id') and self._speaking_tri_id is not None:
            self._canvas.delete(self._speaking_tri_id)
            self._speaking_tri_id = None
        if self._speaking_anim_after_id is not None:
            with contextlib.suppress(tk.TclError):
                self._root.after_cancel(self._speaking_anim_after_id)
            self._speaking_anim_after_id = None
        logger.debug('[AVATAR] Speaking indicator hidden')

    def _animate_speaking_dots(self) -> None:
        """Animate the speech bubble dots in a wave pattern."""
        if not self._running or not self._speaking_dot_ids:
            return
        active_dot = self._speaking_anim_frame % 3
        for i, dot_id in enumerate(self._speaking_dot_ids):
            fill = '#555555' if i == active_dot else '#cccccc'
            self._canvas.itemconfig(dot_id, fill=fill)
        self._speaking_anim_frame += 1
        self._speaking_anim_after_id = self._root.after(400, self._animate_speaking_dots)

    # ========================================================================
    # Hover Glow Effect
    # ========================================================================

    def _show_hover_glow(self) -> None:
        """Show a soft golden aura behind the avatar on mouse hover.

        Creates multiple concentric ovals with golden colors and decreasing
        stipple density to simulate a partially transparent ethereal glow.
        """
        if self._glow_item_id is not None:
            return

        # Build layered golden aura (outer = faintest, inner = brightest)
        glow_layers = [
            (5, '#c8962d', 'gray12'),    # Outer: faint warm gold
            (15, '#d4a843', 'gray25'),    # Mid: soft amber
            (25, '#e8c362', 'gray25'),    # Inner: brighter gold
        ]

        self._glow_layer_ids: list[int] = []
        for margin, color, stipple in glow_layers:
            layer_id = self._canvas.create_oval(
                margin, margin, self.size - margin, self.size - margin,
                fill=color, outline='', stipple=stipple,
            )
            self._canvas.tag_lower(layer_id, self._image_item)
            self._glow_layer_ids.append(layer_id)

        # Use first layer ID as sentinel for glow-active check
        self._glow_item_id = self._glow_layer_ids[0]
        logger.debug('[AVATAR] Golden hover glow shown')

    def _hide_hover_glow(self) -> None:
        """Remove the hover glow effect from the canvas."""
        if self._glow_item_id is not None:
            for layer_id in getattr(self, '_glow_layer_ids', []):
                self._canvas.delete(layer_id)
            self._glow_layer_ids = []
            self._glow_item_id = None
            logger.debug('[AVATAR] Golden hover glow hidden')

    # ========================================================================
    # Event Handlers
    # ========================================================================

    def _on_right_click(self, event: tk.Event) -> None:
        """Handle right-click to close widget."""
        logger.info('Avatar widget closed via right-click')
        self.stop()

    def _on_drag_start(self, event: tk.Event) -> None:
        """Start drag operation and save previous foreground window."""
        self._drag_x = event.x
        self._drag_y = event.y

        # Store the foreground window before drag (for focus restoration)
        if sys.platform == 'win32' and win32gui:
            try:
                self._drag_prev_hwnd = win32gui.GetForegroundWindow()
            except Exception:
                self._drag_prev_hwnd = None

    def _on_drag_motion(self, event: tk.Event) -> None:
        """Handle drag motion to move window."""
        x = self._root.winfo_x() + (event.x - self._drag_x)
        y = self._root.winfo_y() + (event.y - self._drag_y)
        self._root.geometry(f'+{x}+{y}')

    def _on_drag_release(self, event: tk.Event) -> None:
        """Save position when drag ends and restore focus to previous window."""
        _save_position(self._root.winfo_x(), self._root.winfo_y())

        # Restore focus to previous window after drag
        if self._drag_prev_hwnd and sys.platform == 'win32' and win32gui:
            def restore_focus() -> None:
                try:
                    win32gui.SetForegroundWindow(self._drag_prev_hwnd)
                except Exception:
                    pass
            self._root.after(50, restore_focus)
            self._drag_prev_hwnd = None

    # ========================================================================
    # Interactive Controls
    # ========================================================================

    def _on_mouse_enter(self, event: tk.Event) -> None:
        """Handle mouse entering avatar area - show controls, glow, and pause cycling."""
        logger.debug('[AVATAR] Mouse entered avatar area')
        if not self._buttons_visible:
            self._show_buttons()
        self._show_hover_glow()

        # Hover lock: pause variant cycling while mouse is over avatar
        if not self._hover_locked:
            self._hover_locked = True
            if self._cycle_after_id is not None:
                self._was_cycling = True
                with contextlib.suppress(tk.TclError):
                    self._root.after_cancel(self._cycle_after_id)
                self._cycle_after_id = None
                logger.debug('[AVATAR] Hover lock engaged - cycling paused')
            else:
                self._was_cycling = False

    def _on_mouse_leave(self, event: tk.Event) -> None:
        """Handle mouse leaving avatar area - hide buttons and resume cycling."""
        # Schedule check after short delay to allow mouse to enter button area
        self._root.after(100, self._check_hide_buttons)
        self._root.after(100, self._check_release_hover_lock)

    def _check_hide_buttons(self) -> None:
        """Check if mouse is still over avatar/buttons area, hide if not."""
        if not self._buttons_visible:
            return

        try:
            x, y = self._root.winfo_pointerxy()
            canvas_x = self._canvas.winfo_rootx()
            canvas_y = self._canvas.winfo_rooty()
            canvas_w = self._canvas.winfo_width()
            canvas_h = self._canvas.winfo_height()

            # If mouse is outside canvas area, hide buttons and glow
            if not (canvas_x <= x <= canvas_x + canvas_w and canvas_y <= y <= canvas_y + canvas_h):
                self._hide_buttons()
                self._hide_hover_glow()
        except tk.TclError:
            pass

    def _check_release_hover_lock(self) -> None:
        """Release hover lock if mouse has truly left the avatar area."""
        if not self._hover_locked:
            return

        try:
            x, y = self._root.winfo_pointerxy()
            canvas_x = self._canvas.winfo_rootx()
            canvas_y = self._canvas.winfo_rooty()
            canvas_w = self._canvas.winfo_width()
            canvas_h = self._canvas.winfo_height()

            still_over_canvas = (canvas_x <= x <= canvas_x + canvas_w
                                 and canvas_y <= y <= canvas_y + canvas_h)

            if not still_over_canvas:
                self._hover_locked = False

                # Resume variant cycling if it was active before hover
                if self._was_cycling:
                    self._was_cycling = False
                    variants = self._get_variants(self.current_emotion)
                    if len(variants) > 1 and self._cycle_after_id is None:
                        self._cycle_after_id = self._root.after(
                            VARIANT_CYCLE_INTERVAL_MS, self._cycle_variant
                        )
                    logger.debug('[AVATAR] Hover lock released - cycling resumed')
        except tk.TclError:
            pass

    # ========================================================================
    # Canvas Control Buttons (overlay drawn on canvas)
    # ========================================================================

    def _create_rounded_rect(
        self, x: int, y: int, width: int, height: int,
        radius: int, tag: str, **kwargs: Any,
    ) -> int:
        """Create a rounded rectangle on the canvas using a smooth polygon.

        Args:
            x: Left edge x coordinate.
            y: Top edge y coordinate.
            width: Rectangle width in pixels.
            height: Rectangle height in pixels.
            radius: Corner radius in pixels.
            tag: Canvas tag for the item.
            **kwargs: Additional arguments passed to create_polygon (fill, outline, etc).

        Returns:
            Canvas item ID of the polygon.
        """
        r = min(radius, width // 2, height // 2)
        x2, y2 = x + width, y + height
        points = [
            x + r, y,
            x2 - r, y,
            x2, y,
            x2, y + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x + r, y2,
            x, y2,
            x, y2 - r,
            x, y + r,
            x, y,
        ]
        return self._canvas.create_polygon(
            points, smooth=True, tags=tag, **kwargs,
        )

    def _get_btn_color(self, tag: str) -> str:
        """Get the current fill color for a button based on its state."""
        if tag == 'ctrl_tts':
            return BTN_COLOR_ACTIVE if self._tts_enabled else BTN_COLOR_INACTIVE
        if tag == 'ctrl_stt':
            return BTN_COLOR_ACTIVE if self._stt_enabled else BTN_COLOR_INACTIVE
        return BTN_COLOR_NEUTRAL

    def _get_btn_hover_color(self, tag: str) -> str:
        """Get the hover fill color for a button based on its state."""
        if tag == 'ctrl_tts':
            return BTN_COLOR_HOVER_ACTIVE if self._tts_enabled else BTN_COLOR_HOVER_INACTIVE
        if tag == 'ctrl_stt':
            return BTN_COLOR_HOVER_ACTIVE if self._stt_enabled else BTN_COLOR_HOVER_INACTIVE
        return BTN_COLOR_HOVER_NEUTRAL

    def _create_canvas_button(
        self, x: int, y: int, width: int, height: int, text: str, tag: str,
        click_handler: Any, fill_color: str = BTN_COLOR_NEUTRAL,
    ) -> tuple[int, int]:
        """Create a canvas-based button overlay with rounded corners and shadow.

        Args:
            x: Left edge x coordinate.
            y: Top edge y coordinate.
            width: Button width in pixels.
            height: Button height in pixels.
            text: Button label text.
            tag: Canvas tag for grouping (used for event binding and deletion).
            click_handler: Callback for button click.
            fill_color: Background fill color for the button.

        Returns:
            Tuple of (background_rect_id, text_id).
        """
        # Drop shadow (offset behind the button)
        self._create_rounded_rect(
            x + BTN_SHADOW_OFFSET, y + BTN_SHADOW_OFFSET, width, height,
            BTN_CORNER_RADIUS, tag, fill=BTN_SHADOW_COLOR, outline='',
        )

        # Rounded rectangle background
        bg_id = self._create_rounded_rect(
            x, y, width, height, BTN_CORNER_RADIUS, tag,
            fill=fill_color, outline='#555555',
        )

        text_id = self._canvas.create_text(
            x + width // 2, y + height // 2,
            text=text,
            fill='#cccccc',
            font=('Segoe UI Emoji', 11),
            tags=tag,
        )

        # Wrap click handler with focus restoration
        def handle_click_with_focus_restore(event: tk.Event) -> None:
            """Execute button handler and restore focus to previous window."""
            # Get foreground window before our window takes focus
            prev_hwnd = None
            if sys.platform == 'win32' and win32gui:
                try:
                    prev_hwnd = win32gui.GetForegroundWindow()
                except Exception:
                    pass

            # Execute the actual button handler
            click_handler()

            # Restore focus to previous window after a short delay
            if prev_hwnd and sys.platform == 'win32' and win32gui:
                def restore_focus() -> None:
                    try:
                        win32gui.SetForegroundWindow(prev_hwnd)
                    except Exception:
                        pass
                self._root.after(50, restore_focus)

        self._canvas.tag_bind(tag, '<Button-1>', handle_click_with_focus_restore)
        self._canvas.tag_bind(tag, '<Enter>', lambda e: self._on_ctrl_btn_enter(tag))
        self._canvas.tag_bind(tag, '<Leave>', lambda e: self._on_ctrl_btn_leave(tag))

        return bg_id, text_id

    def _on_ctrl_btn_enter(self, tag: str) -> None:
        """Highlight a canvas control button on hover and show preview avatar.

        When hover-locked, only the button color changes -- the locked avatar
        image stays visible.
        """
        if tag in self._ctrl_btn_ids:
            bg_id, text_id = self._ctrl_btn_ids[tag]
            self._canvas.itemconfig(bg_id, fill=self._get_btn_hover_color(tag))
            self._canvas.itemconfig(text_id, fill='#ffffff')

        # Skip avatar preview when hover-locked (locked image stays visible)
        if self._hover_locked:
            return

        # Show hover avatar for all control buttons
        preview_map = {
            'ctrl_tts': 'tts',
            'ctrl_stt': 'stt',
            'ctrl_close': 'close',
            'ctrl_tags': 'tags',
        }
        if tag in preview_map:
            self._preview_image(preview_map[tag])

    def _on_ctrl_btn_leave(self, tag: str) -> None:
        """Restore a canvas control button on hover leave and restore emotion.

        When hover-locked, only the button color reverts -- the locked avatar
        image stays visible (no restore needed since no preview was shown).
        """
        if tag in self._ctrl_btn_ids:
            bg_id, text_id = self._ctrl_btn_ids[tag]
            self._canvas.itemconfig(bg_id, fill=self._get_btn_color(tag))
            self._canvas.itemconfig(text_id, fill='#cccccc')

        # Skip restore when hover-locked (no preview was shown)
        if self._hover_locked:
            return

        # Restore emotion for all control buttons
        if tag in ('ctrl_tts', 'ctrl_stt', 'ctrl_close', 'ctrl_tags'):
            self._restore_emotion()

    def _open_tag_editor(self, event: tk.Event | None = None) -> None:
        """Open the tag editor dialog for the currently displayed image.

        Finds the ImageEntry matching the current avatar path and opens
        a TagEditorDialog populated with all known tags in the registry.
        Fully error-guarded to prevent crashes from killing the widget.

        Args:
            event: Optional Tkinter event (from canvas click binding).
        """
        logger.debug('[AVATAR] Tag editor requested')

        # Prevent opening multiple dialogs simultaneously
        if self._tag_editor_open:
            logger.debug('[TAGS] Tag editor already open, ignoring')
            return

        if not self.current_avatar_path or not self._image_registry:
            logger.warning('[TAGS] No current image or empty registry')
            return

        try:
            # Find the ImageEntry for the current image
            current_entry: ImageEntry | None = None
            for img in self._image_registry:
                if img.path == self.current_avatar_path:
                    current_entry = img
                    break
                # Fall back to resolved path comparison (guard against OSError)
                with contextlib.suppress(OSError):
                    if img.path.resolve() == self.current_avatar_path.resolve():
                        current_entry = img
                        break

            if current_entry is None:
                logger.warning(f'[TAGS] Current image not in registry: {self.current_avatar_path}')
                return

            # Collect all tags across the entire registry
            all_tags: set[str] = set()
            for img in self._image_registry:
                all_tags.update(img.tags)

            # Also include all known valid tags so user can add new ones
            all_tags.update(VALID_EMOTIONS)
            all_tags.update(VALID_CONTROL_TAGS)

            self._tag_editor_open = True

            # Open dialog
            dialog = TagEditorDialog(
                self._root,
                current_entry,
                all_tags,
                lambda new_tags: self._save_image_tags(current_entry, new_tags),
            )

            # Reset guard when dialog is destroyed (save or cancel)
            dialog.dialog.bind('<Destroy>', lambda e: setattr(self, '_tag_editor_open', False))

            logger.info(f'[TAGS] Opened editor for: {current_entry.path.name}')
        except Exception as e:
            self._tag_editor_open = False
            logger.error(f'[TAGS] Failed to open tag editor: {e}', exc_info=True)

    def _save_image_tags(self, image_entry: ImageEntry, new_tags: list[str]) -> None:
        """Save updated tags for an image to both memory and config file.

        Updates the in-memory ImageEntry, invalidates the variant cache so
        the new tags take effect immediately, and persists to disk via
        avatar_tags.update_image_tags().

        Args:
            image_entry: The image entry being updated.
            new_tags: New list of tags to assign.
        """
        old_tags = image_entry.tags[:]
        image_entry.tags = new_tags
        logger.info(f'[TAGS] Updated {image_entry.path.name}: {old_tags} -> {new_tags}')

        # Invalidate variant cache so tag changes take effect immediately
        self._variant_cache.clear()

        # Persist to config file
        try:
            from pyagentvox.avatar_tags import update_image_tags

            update_image_tags(image_entry.path, new_tags)
            logger.info(f'[TAGS] Saved to config: {image_entry.path.name}')
        except ImportError:
            logger.error('[TAGS] avatar_tags module not available, changes only in memory')
            messagebox.showwarning(
                'Save Warning',
                'Tags updated in memory but could not persist to config file.\n'
                'The avatar_tags module is not available.',
                parent=self._root,
            )
        except Exception as e:
            logger.error(f'[TAGS] Failed to save: {e}')
            messagebox.showerror(
                'Save Error',
                f'Failed to save tags to config file:\n{e}',
                parent=self._root,
            )

    # ========================================================================
    # Control Buttons (canvas-based overlays at bottom of avatar)
    # ========================================================================

    def _show_buttons(self) -> None:
        """Show control buttons at bottom of avatar as canvas overlays."""
        if self._buttons_visible:
            return

        # Disable click-through when showing buttons
        if sys.platform == 'win32':
            self._disable_click_through()

        # Button layout: 4 buttons centered at bottom of canvas
        btn_w, btn_h = 40, 28
        gap = 6
        num_buttons = 4
        total_w = num_buttons * btn_w + (num_buttons - 1) * gap
        canvas_w = self._canvas.winfo_width()
        canvas_h = self._canvas.winfo_height()
        start_x = (canvas_w - total_w) // 2
        y = canvas_h - btn_h - 10  # 10px margin from bottom

        # TTS toggle button (green when enabled, red when disabled)
        tts_icon = '\U0001f50a' if self._tts_enabled else '\U0001f507'
        tts_color = BTN_COLOR_ACTIVE if self._tts_enabled else BTN_COLOR_INACTIVE
        self._ctrl_btn_ids['ctrl_tts'] = self._create_canvas_button(
            start_x, y, btn_w, btn_h, tts_icon, 'ctrl_tts', self._toggle_tts, tts_color,
        )

        # STT toggle button (green when enabled, red when disabled)
        stt_icon = '\U0001f3a4' if self._stt_enabled else '\U0001f507'
        stt_color = BTN_COLOR_ACTIVE if self._stt_enabled else BTN_COLOR_INACTIVE
        x2 = start_x + btn_w + gap
        self._ctrl_btn_ids['ctrl_stt'] = self._create_canvas_button(
            x2, y, btn_w, btn_h, stt_icon, 'ctrl_stt', self._toggle_stt, stt_color,
        )

        # Tag editor button (neutral)
        x3 = x2 + btn_w + gap
        self._ctrl_btn_ids['ctrl_tags'] = self._create_canvas_button(
            x3, y, btn_w, btn_h, '\U0001f3f7\ufe0f', 'ctrl_tags', self._open_tag_editor,
        )

        # Close button (far right, neutral)
        x4 = x3 + btn_w + gap
        self._ctrl_btn_ids['ctrl_close'] = self._create_canvas_button(
            x4, y, btn_w, btn_h, '\u274c', 'ctrl_close', self._close_with_animation,
        )

        self._buttons_visible = True
        logger.debug('[AVATAR] Control buttons shown (4 canvas buttons at bottom)')

    def _hide_buttons(self) -> None:
        """Hide all canvas control buttons."""
        if not self._buttons_visible:
            return

        for tag in list(self._ctrl_btn_ids.keys()):
            self._canvas.delete(tag)
        self._ctrl_btn_ids.clear()

        self._buttons_visible = False

        # Re-enable click-through when hiding buttons
        if sys.platform == 'win32':
            self._enable_click_through()

        # Restore emotion if preview was active
        if self._preview_active:
            self._restore_emotion()

        logger.debug('[AVATAR] Control buttons hidden')

    def _preview_image(self, control_type: str) -> None:
        """Show a contextual avatar image when hovering over a control button.

        Uses BUTTON_HOVER_TAGS with tag-based registry lookup to find an avatar
        that visually communicates the button's function (e.g., headphones for
        TTS, listening pose for STT).

        Args:
            control_type: Type of control ('tts', 'stt', 'close', or 'tags').
        """
        if not self._preview_active:
            self._preview_emotion = self.current_emotion
            self._preview_active = True

        # Tags button keeps the current image visible (no preview)
        if control_type == 'tags':
            return

        # Determine tag to search for based on button type and state
        if control_type == 'tts':
            avatar_key = 'tts_on' if self._tts_enabled else 'tts_off'
        elif control_type == 'stt':
            avatar_key = 'stt_on' if self._stt_enabled else 'stt_off'
        elif control_type == 'close':
            avatar_key = 'close'
        else:
            return

        # Tag-based lookup from image registry (if hover tag is configured)
        hover_tag = BUTTON_HOVER_TAGS.get(avatar_key)
        if hover_tag and self._image_registry:
            matching = [
                img for img in self._image_registry
                if hover_tag.lower() in img.tag_set
            ]
            if matching:
                # Pick a random match for visual variety
                chosen = random.choice(matching)
                self._display_variant(chosen.path)
                logger.debug(
                    f'[AVATAR] Button hover preview: {chosen.path.name} '
                    f'(tag={hover_tag}, key={avatar_key})'
                )
                return

        # Fall back to control-tag system with state-aware tag name
        # Maps avatar_key (e.g., 'tts_on') to control tag (e.g., 'control-tts-hover-on')
        control_tag_map = {
            'tts_on': 'control-tts-hover-on',
            'tts_off': 'control-tts-hover-off',
            'stt_on': 'control-stt-hover-on',
            'stt_off': 'control-stt-hover-off',
            'close': 'control-close-hover',
        }
        fallback_tag = control_tag_map.get(avatar_key, f'control-{control_type}-hover')
        logger.debug(f'[AVATAR] Trying control tag fallback: {fallback_tag}')
        self._load_control_image(fallback_tag)

    def _restore_emotion(self) -> None:
        """Restore previous emotion after preview."""
        if self._preview_active and self._preview_emotion:
            self._preview_active = False
            emotion_to_restore = self._preview_emotion
            self._preview_emotion = None

            # Force switch back to previous emotion by clearing variant cache
            # and using the existing path reset instead of setting current_emotion
            # to empty string (which races with emotion polling every 200ms).
            self.current_avatar_path = None  # Forces _switch_emotion guard to pass
            self._switch_emotion(emotion_to_restore)

    def _load_control_image(self, control_tag: str) -> None:
        """Load and display image by control tag.

        Uses tag-based lookup if image registry is populated, otherwise falls
        back to filename-based lookup in controls subdirectory with legacy
        filename mapping for backward compatibility.

        Args:
            control_tag: Control tag to look up (e.g., 'control-tts-hover-on',
                        'control-close-hover'). Also accepts legacy names for
                        backward compatibility.
        """
        # Legacy filename mapping for backward compatibility
        legacy_map = {
            'tts-on': 'control-tts-hover-on',
            'tts-off': 'control-tts-hover-off',
            'stt-on': 'control-stt-hover-on',
            'stt-off': 'control-stt-hover-off',
            'close': 'control-close-hover',
            'pleading': 'control-close-hover',        # Legacy name
            'tts-toggled': 'control-tts-clicked',
            'stt-toggled': 'control-stt-clicked',
            'crying': 'control-close-animation',      # Legacy name
        }

        # Normalize: map legacy names to functional tags
        if not control_tag.startswith('control-'):
            control_tag = legacy_map.get(control_tag, f'control-{control_tag}')

        # Tag-based lookup (if registry is populated)
        if self._image_registry:
            for img in self._image_registry:
                if control_tag.lower() in img.tag_set:
                    self._display_variant(img.path)
                    logger.debug(f'Loaded control image by tag: {control_tag}')
                    return

        # Fallback: filename-based lookup in controls subdirectory
        # Try functional tag name first (strip 'control-' prefix), then legacy filenames
        base_name = control_tag.replace('control-', '') if control_tag.startswith('control-') else control_tag

        # Build list of filenames to try: functional name, then any legacy names that map here
        filenames_to_try = [base_name]
        for legacy_name, functional_tag in legacy_map.items():
            if functional_tag == control_tag and legacy_name not in filenames_to_try:
                filenames_to_try.append(legacy_name)

        controls_dir = self.avatar_dir / 'controls'
        if not controls_dir.exists():
            logger.warning(f'Controls directory not found and no tag match: {controls_dir}')
            return

        # Try to find image with any supported extension and filename variant
        img_path = None
        for filename in filenames_to_try:
            for ext in ['.png', '.jpg', '.jpeg', '.webp']:
                candidate = controls_dir / f'{filename}{ext}'
                if candidate.exists():
                    img_path = candidate
                    break
            if img_path:
                break

        if img_path:
            self._display_variant(img_path)
            logger.debug(f'Loaded control image by filename: {img_path.stem}')
        else:
            logger.warning(f'Control image not found by tag or filename: {control_tag}')

    def _toggle_tts(self) -> None:
        """Toggle TTS enabled/disabled state."""
        self._tts_enabled = not self._tts_enabled
        self._write_tts_state(self._tts_enabled)
        self._update_canvas_button_icon(
            'ctrl_tts', self._tts_enabled, '\U0001f50a', '\U0001f507',
        )
        self._show_feedback('tts')
        logger.info(f'TTS {"enabled" if self._tts_enabled else "disabled"}')

    def _toggle_stt(self) -> None:
        """Toggle STT enabled/disabled state."""
        self._stt_enabled = not self._stt_enabled
        self._write_stt_state(self._stt_enabled)
        self._update_canvas_button_icon(
            'ctrl_stt', self._stt_enabled, '\U0001f3a4', '\U0001f507',
        )
        self._show_feedback('stt')
        logger.info(f'STT {"enabled" if self._stt_enabled else "disabled"}')

    def _update_canvas_button_icon(
        self, tag: str, enabled: bool, on_icon: str, off_icon: str,
    ) -> None:
        """Update canvas button text and background color based on enabled state.

        Args:
            tag: Canvas tag identifying the button.
            enabled: Whether the feature is enabled.
            on_icon: Icon to show when enabled.
            off_icon: Icon to show when disabled.
        """
        if tag in self._ctrl_btn_ids:
            bg_id, text_id = self._ctrl_btn_ids[tag]
            self._canvas.itemconfig(text_id, text=on_icon if enabled else off_icon)
            self._canvas.itemconfig(
                bg_id, fill=BTN_COLOR_ACTIVE if enabled else BTN_COLOR_INACTIVE,
            )

    def _show_feedback(self, feedback_type: str) -> None:
        """Show confirmation image for 1 second, then restore emotion.

        Sets up preview state so _restore_emotion can properly revert
        to the previous emotion after the feedback image is shown.

        Args:
            feedback_type: Type of feedback ('tts' or 'stt').
        """
        if not self._preview_active:
            self._preview_emotion = self.current_emotion
            self._preview_active = True

        control_tag = f'control-{feedback_type}-clicked'
        self._load_control_image(control_tag)
        self._root.after(1000, self._restore_emotion)

    def _write_tts_state(self, enabled: bool) -> None:
        """Write TTS enabled state to IPC file.

        Args:
            enabled: Whether TTS is enabled.
        """
        if self.monitor_pid is None:
            logger.warning('[AVATAR] Cannot write TTS state: no monitor PID')
            return

        state_file = Path(tempfile.gettempdir()) / f'pyagentvox_tts_enabled_{self.monitor_pid}.txt'
        try:
            state_file.write_text('1' if enabled else '0', encoding='utf-8')
            logger.info(f'[AVATAR] Wrote TTS state: {"enabled" if enabled else "disabled"} -> {state_file}')
        except OSError as e:
            logger.error(f'[AVATAR] Failed to write TTS state: {e}')

    def _write_stt_state(self, enabled: bool) -> None:
        """Write STT enabled state to IPC file.

        Args:
            enabled: Whether STT is enabled.
        """
        if self.monitor_pid is None:
            logger.warning('[AVATAR] Cannot write STT state: no monitor PID')
            return

        state_file = Path(tempfile.gettempdir()) / f'pyagentvox_stt_enabled_{self.monitor_pid}.txt'
        try:
            state_file.write_text('1' if enabled else '0', encoding='utf-8')
            logger.info(f'[AVATAR] Wrote STT state: {"enabled" if enabled else "disabled"} -> {state_file}')
        except OSError as e:
            logger.error(f'[AVATAR] Failed to write STT state: {e}')

    def _close_with_animation(self) -> None:
        """Show crying Luna and animate slide-down with fade-out.

        Crying Luna is the ONLY image shown during the exit sequence.
        The slide starts slow and accelerates (ease-in), while the
        window fades out at the same rate as the slide.
        """
        # Hide control buttons so only crying image is visible
        self._hide_buttons()

        # Show close animation image (crying Luna)
        self._load_control_image('control-close-animation')
        self._root.update()
        time.sleep(0.5)

        # Animate slide-down with simultaneous fade-out using ease-in curve
        steps = 40
        distance = 350
        total_duration = 1.2  # seconds
        delay = total_duration / steps

        start_x = self._root.winfo_x()
        start_y = self._root.winfo_y()

        for i in range(steps):
            # Ease-in (cubic): slow start, accelerating exit
            t = i / steps
            eased = t * t * t

            offset = int(distance * eased)
            alpha = max(0.0, 1.0 - eased)

            self._root.geometry(f'+{start_x}+{start_y + offset}')
            if sys.platform == 'win32':
                with contextlib.suppress(tk.TclError):
                    self._root.attributes('-alpha', alpha)
            self._root.update()
            time.sleep(delay)

        logger.info('Avatar closed with animation')
        self.stop()

    def _enable_click_through(self) -> None:
        """Enable click-through mode (Windows only)."""
        # Currently just a placeholder - the transparent background already provides
        # most click-through behavior. Full WS_EX_TRANSPARENT would require win32 API.
        pass

    def _disable_click_through(self) -> None:
        """Disable click-through mode to allow button interaction (Windows only)."""
        # Currently just a placeholder - buttons work without special handling.
        pass

    # ========================================================================
    # Filter Control File Monitoring
    # ========================================================================

    def _poll_filter_control_file(self) -> None:
        """Poll the filter control file and update tag filters on changes.

        Control file format (one command per line):
            include:tag1,tag2,tag3
            exclude:tag4,tag5
            require_all:true
            reset
        """
        if not self._running or self.monitor_pid is None:
            return

        filter_file = Path(tempfile.gettempdir()) / f'agent_avatar_filter_{self.monitor_pid}.txt'

        try:
            if filter_file.exists():
                commands = filter_file.read_text(encoding='utf-8').strip().split('\n')

                for cmd in commands:
                    if cmd.startswith('include:'):
                        tags = cmd[8:].split(',')
                        self._include_tags = [t.strip() for t in tags if t.strip()]
                        logger.info(f'[FILTER] Include tags: {self._include_tags}')

                    elif cmd.startswith('exclude:'):
                        tags = cmd[8:].split(',')
                        self._exclude_tags = [t.strip() for t in tags if t.strip()]
                        logger.info(f'[FILTER] Exclude tags: {self._exclude_tags}')

                    elif cmd.startswith('require_all:'):
                        self._require_all_include = cmd[12:].lower() == 'true'
                        logger.info(f'[FILTER] Require all: {self._require_all_include}')

                    elif cmd == 'reset':
                        self._include_tags = []
                        self._exclude_tags = []
                        self._require_all_include = False
                        logger.info('[FILTER] Filters reset')

                # Clear variant cache to force re-filtering
                self._variant_cache.clear()

                # Refresh current emotion display with new filters
                # (bypass _switch_emotion guard which blocks same-emotion transitions)
                variants = self._get_variants(self.current_emotion)
                if variants:
                    self._current_variant_index = 0
                    self._display_variant(variants[0])

                # Delete control file
                filter_file.unlink()

        except Exception as e:
            logger.error(f'Error polling filter control file: {e}')

        # Schedule next poll
        if self._running:
            self._filter_poll_after_id = self._root.after(
                FILTER_POLL_INTERVAL_MS, self._poll_filter_control_file
            )

    # ========================================================================
    # Emotion File Monitoring
    # ========================================================================

    def _poll_emotion_file(self) -> None:
        """Poll the emotion IPC file and update avatar on changes.

        Scheduled on the Tkinter main loop to avoid threading issues.
        """
        if not self._running or self.monitor_pid is None:
            return

        try:
            emotion = read_emotion_state(self.monitor_pid)

            if emotion:
                # Determine if TTS is speaking (any emotion except waiting/bored/sleeping)
                is_speaking = emotion not in [WAITING_STATE, 'bored', 'sleeping']

                if is_speaking and not self._is_speaking:
                    # TTS started speaking - reset idle timer and show indicator
                    self._is_speaking = True
                    self._reset_idle_timer()
                    self._show_speaking_indicator()
                    logger.debug(f'[AVATAR] TTS started speaking: {emotion}')
                elif not is_speaking and self._is_speaking:
                    # TTS stopped speaking - start idle timer and hide indicator
                    self._is_speaking = False
                    self._start_idle_timer()
                    self._hide_speaking_indicator()
                    logger.debug(f'[AVATAR] TTS stopped speaking, entering: {emotion}')

                # Only resolve emotion if it changed from last poll (avoid redundant discover_variants calls)
                if not hasattr(self, '_last_raw_emotion'):
                    self._last_raw_emotion = ''

                if emotion != self._last_raw_emotion:
                    # Resolve emotion through hierarchy if needed
                    resolved_emotion = resolve_emotion_hierarchy(emotion, self.avatar_dir)
                    self._last_raw_emotion = emotion

                    if resolved_emotion != self.current_emotion:
                        logger.debug(f'[AVATAR] Emotion file changed: {emotion} -> {resolved_emotion}')
                        self._fade_transition(resolved_emotion)
        except Exception as e:
            logger.error(f'[AVATAR] Error polling emotion file: {e}')

        # Schedule next poll
        if self._running:
            self._root.after(EMOTION_POLL_INTERVAL_MS, self._poll_emotion_file)

    # ========================================================================
    # Visibility Guard
    # ========================================================================

    def _guard_visibility(self) -> None:
        """Periodically re-assert topmost and visibility state.

        On Windows 11, other applications or system events can occasionally
        push the avatar behind other windows. This guard runs every 5 seconds
        to ensure the widget stays visible and on top.
        """
        if not self._running:
            return

        try:
            # Re-assert topmost (cheap no-op if already topmost)
            self._root.attributes('-topmost', False)
            self._root.attributes('-topmost', True)
            self._root.lift()
        except tk.TclError:
            pass

        # Schedule next guard check
        if self._running:
            self._root.after(5000, self._guard_visibility)

    # ========================================================================
    # Lifecycle
    # ========================================================================

    def run(self) -> None:
        """Start the avatar widget and enter the Tkinter main loop.

        This method blocks until the widget is closed.
        """
        # Start polling emotion file if monitoring a PID
        if self.monitor_pid is not None:
            emotion_file = get_emotion_file_path(self.monitor_pid)
            logger.info(f'[AVATAR] Monitoring emotion file: {emotion_file}')
            logger.debug(f'[AVATAR] Emotion file exists: {emotion_file.exists()}')
            self._root.after(EMOTION_POLL_INTERVAL_MS, self._poll_emotion_file)

            # Start polling filter control file
            filter_file = get_filter_control_file_path(self.monitor_pid)
            logger.debug(f'[AVATAR] Monitoring filter control file: {filter_file}')
            self._root.after(FILTER_POLL_INTERVAL_MS, self._poll_filter_control_file)

        # Start idle timer for bored/sleeping transitions
        self._start_idle_timer()

        # Start periodic visibility guard (re-asserts topmost)
        self._root.after(5000, self._guard_visibility)

        # Final visibility check before entering mainloop
        logger.debug(f'[AVATAR] Window state before mainloop: {self._root.state()}')
        logger.debug(f'[AVATAR] Window alpha: {self._root.attributes("-alpha")}')
        logger.debug(f'[AVATAR] Window geometry: {self._root.geometry()}')
        logger.info('[AVATAR] Starting tkinter mainloop (right-click to close)')

        try:
            self._root.mainloop()
        except KeyboardInterrupt:
            logger.info('[AVATAR] Widget interrupted by KeyboardInterrupt')
        except Exception as e:
            logger.error(f'[AVATAR] Mainloop crashed: {e}', exc_info=True)
        finally:
            self._running = False
            logger.debug('[AVATAR] Mainloop exited')

    def stop(self) -> None:
        """Stop the avatar widget and save position."""
        logger.info('[AVATAR] Stopping avatar widget...')
        self._running = False

        # Cancel variant cycling
        if self._cycle_after_id is not None:
            with contextlib.suppress(tk.TclError):
                self._root.after_cancel(self._cycle_after_id)
            self._cycle_after_id = None

        # Cancel idle checking
        if self._idle_check_after_id is not None:
            with contextlib.suppress(tk.TclError):
                self._root.after_cancel(self._idle_check_after_id)
            self._idle_check_after_id = None

        # Cancel filter polling
        if self._filter_poll_after_id is not None:
            with contextlib.suppress(tk.TclError):
                self._root.after_cancel(self._filter_poll_after_id)
            self._filter_poll_after_id = None

        # Cancel any in-progress fade animation
        if self._fade_after_id is not None:
            with contextlib.suppress(tk.TclError):
                self._root.after_cancel(self._fade_after_id)
            self._fade_after_id = None

        # Cancel any in-progress shimmer animation
        if self._shimmer_after_id is not None:
            with contextlib.suppress(tk.TclError):
                self._root.after_cancel(self._shimmer_after_id)
            self._shimmer_after_id = None

        # Cancel speaking indicator animation
        if self._speaking_anim_after_id is not None:
            with contextlib.suppress(tk.TclError):
                self._root.after_cancel(self._speaking_anim_after_id)
            self._speaking_anim_after_id = None

        # Clean up control state files
        if self.monitor_pid is not None:
            tts_file = Path(tempfile.gettempdir()) / f'pyagentvox_tts_enabled_{self.monitor_pid}.txt'
            stt_file = Path(tempfile.gettempdir()) / f'pyagentvox_stt_enabled_{self.monitor_pid}.txt'
            with contextlib.suppress(OSError):
                tts_file.unlink(missing_ok=True)
            with contextlib.suppress(OSError):
                stt_file.unlink(missing_ok=True)

        # Save final position
        with contextlib.suppress(tk.TclError):
            _save_position(self._root.winfo_x(), self._root.winfo_y())

        with contextlib.suppress(tk.TclError):
            self._root.quit()
            self._root.destroy()

        logger.info('Avatar widget stopped')

    def set_mood(self, emotion: str) -> None:
        """Manually set the avatar mood (for external callers).

        Thread-safe: can be called from any thread.

        Args:
            emotion: Emotion name (e.g., 'cheerful', 'focused', 'waiting').
        """
        avatar_name = EMOTION_AVATAR_MAP.get(emotion, emotion)
        if avatar_name != self.current_emotion:
            self._root.after(0, self._fade_transition, avatar_name)

    def invalidate_variant_cache(self) -> None:
        """Clear the variant cache, forcing re-discovery on next access.

        Useful if images are added/removed at runtime.
        """
        self._variant_cache.clear()
        logger.debug('Variant cache invalidated')


# ============================================================================
# Avatar Scanning & Discovery
# ============================================================================

def scan_avatar_directory(avatar_dir: Path) -> dict[str, list[str]]:
    """Scan avatar directory and discover all available emotions with images.

    Looks for both subdirectories (e.g., excited/, waiting/) and prefixed files
    (e.g., excited-1.png, waiting.jpg) to build a complete inventory.

    Args:
        avatar_dir: Path to the avatar image directory.

    Returns:
        Dictionary mapping emotion names to lists of image filenames.
    """
    emotions: dict[str, list[str]] = {}
    supported_formats = {'.png', '.jpg', '.jpeg', '.webp'}

    if not avatar_dir.exists():
        logger.error(f'Avatar directory does not exist: {avatar_dir}')
        return emotions

    # Scan for emotion subdirectories
    for item in avatar_dir.iterdir():
        if item.is_dir():
            emotion_name = item.name
            images = []
            for img_path in item.iterdir():
                if img_path.suffix.lower() in supported_formats:
                    images.append(img_path.name)

            if images:
                emotions[emotion_name] = sorted(images)

    # Scan for prefixed files in root directory
    for img_path in avatar_dir.glob('*'):
        if img_path.is_file() and img_path.suffix.lower() in supported_formats:
            # Extract emotion name from filename (e.g., "excited-1.png" -> "excited")
            name = img_path.stem
            # Handle both "excited.png" and "excited-1.png" formats
            if '-' in name:
                emotion_name = name.split('-')[0]
            else:
                emotion_name = name

            if emotion_name not in emotions:
                emotions[emotion_name] = []
            emotions[emotion_name].append(img_path.name)

    # Sort and deduplicate
    for emotion in emotions:
        emotions[emotion] = sorted(set(emotions[emotion]))

    return emotions


def print_avatar_scan(avatar_dir: Path | None = None) -> None:
    """Scan and print a formatted report of available avatar emotions.

    Args:
        avatar_dir: Path to avatar directory. Uses default if None.
    """
    scan_dir = avatar_dir or AVATAR_DIR
    emotions = scan_avatar_directory(scan_dir)

    print('\n' + '=' * 70)
    print(f'AVATAR SCAN: {scan_dir}')
    print('=' * 70 + '\n')

    if not emotions:
        print('❌ No avatar images found!\n')
        return

    # Separate standard emotions from special ones
    standard_emotions = set(EMOTION_AVATAR_MAP.values()) | {WAITING_STATE, 'bored', 'sleeping'}
    special_emotions = {e for e in emotions if e not in standard_emotions}

    print(f'📊 Found {len(emotions)} emotion categories with {sum(len(imgs) for imgs in emotions.values())} total images\n')

    print('🎭 STANDARD EMOTIONS (for TTS tags):')
    print('-' * 70)
    for emotion in sorted(standard_emotions):
        if emotion in emotions:
            count = len(emotions[emotion])
            print(f'  ✅ {emotion:15} ({count:2} variants)')
        else:
            print(f'  ❌ {emotion:15} (no images)')
    print()

    if special_emotions:
        print('✨ SPECIAL EMOTIONS (manually triggered):')
        print('-' * 70)
        for emotion in sorted(special_emotions):
            count = len(emotions[emotion])
            # Check if it has a hierarchy mapping
            generic = EMOTION_HIERARCHY.get(emotion)
            suffix = f' → {generic}' if generic else ''
            print(f'  💫 {emotion:15} ({count:2} variants){suffix}')
        print()

    print('💡 TIP: Use [emotion] tags in your responses to trigger avatar changes')
    print('   Example: "Hello! [cheerful] Your code works! [excited]"\n')


# ============================================================================
# CLI Entry Point
# ============================================================================

def main() -> None:
    """Run the avatar widget standalone or scan for available emotions."""
    import argparse
    import traceback

    parser = argparse.ArgumentParser(description='Luna Avatar Widget')
    parser.add_argument(
        '--size', type=int, default=DEFAULT_SIZE,
        help=f'Widget size in pixels (default: {DEFAULT_SIZE})'
    )
    parser.add_argument(
        '--avatar-dir', type=str, default=None,
        help=f'Avatar image directory (default: {AVATAR_DIR})'
    )
    parser.add_argument(
        '--pid', type=int, default=None,
        help='PID of PyAgentVox main process to monitor for emotion changes'
    )
    parser.add_argument(
        '--scan', action='store_true',
        help='Scan avatar directory and show available emotions (don\'t launch widget)'
    )
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(message)s',
    )

    logger.info(f'[AVATAR] Starting avatar widget (PID: {os.getpid()})')
    logger.debug(f'[AVATAR] Args: size={args.size}, avatar_dir={args.avatar_dir}, '
                 f'pid={args.pid}, debug={args.debug}')
    logger.debug(f'[AVATAR] Python: {sys.version}')
    logger.debug(f'[AVATAR] Platform: {sys.platform}')
    logger.debug(f'[AVATAR] CWD: {Path.cwd()}')

    avatar_dir = Path(args.avatar_dir) if args.avatar_dir else None

    # Scan mode: show available emotions and exit
    if args.scan:
        print_avatar_scan(avatar_dir)
        return

    # Normal mode: launch widget with full error trapping
    try:
        widget = AvatarWidget(
            avatar_dir=avatar_dir,
            size=args.size,
            monitor_pid=args.pid,
        )
        widget.run()
    except Exception as e:
        logger.error(f'[AVATAR] Fatal error: {e}', exc_info=True)
        # Also print to stderr in case logging is broken
        traceback.print_exc(file=sys.stderr)
        raise SystemExit(1) from e


if __name__ == '__main__':
    main()
