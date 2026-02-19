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
    from PIL import Image, ImageTk
except ImportError:
    print('ERROR: Pillow is required for the avatar widget.', file=sys.stderr)
    print('Install with: pip install Pillow', file=sys.stderr)
    raise SystemExit(1)

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

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
    """Load avatar configuration from pyagentvox.yaml.

    Returns:
        Avatar config dict with keys: directory, idle_states, emotion_hierarchy, etc.
        Returns default config if file not found or yaml not installed.
    """
    default_config = {
        'enabled': True,
        'directory': str(Path.home() / '.claude' / 'luna'),
        'default_size': 300,
        'cycle_interval': 4000,
        'idle_states': {'waiting': 0, 'bored': 120, 'sleeping': 300},
        'emotion_hierarchy': {},
        'filters': {
            'include_tags': [],
            'exclude_tags': [],
            'require_all_include': False,
        },
        'animation': {
            'flip_threshold': 0.5,
            'flip_duration': 300,
            'flip_steps': 15,
        },
        'images': [],
    }

    if yaml is None:
        logger.warning('PyYAML not installed, using default avatar config')
        return default_config

    # Look for config file in package directory
    try:
        config_path = Path(__file__).parent / 'pyagentvox.yaml'
        if config_path.exists():
            with open(config_path, encoding='utf-8') as f:
                full_config = yaml.safe_load(f)
                avatar_config = full_config.get('avatar', {})

                # Merge with defaults (deep merge for nested dicts)
                result = default_config.copy()
                for key, value in avatar_config.items():
                    if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                        result[key].update(value)
                    else:
                        result[key] = value

                # Expand ~ in directory path
                if 'directory' in result:
                    result['directory'] = str(Path(result['directory']).expanduser())

                return result
    except Exception as e:
        logger.warning(f'Failed to load avatar config: {e}')

    return default_config


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


# ============================================================================
# Emotion Resolution
# ============================================================================

def resolve_emotion_hierarchy(emotion: str, avatar_dir: Path) -> str:
    """Resolve an emotion through the hierarchy to find available images.

    Resolution order:
    1. Check if emotion has images directly
    2. Check EMOTION_AVATAR_MAP for standard emotion mappings
    3. Check EMOTION_HIERARCHY for specific → generic fallback
    4. Fall back to 'waiting' state

    Args:
        emotion: Emotion name from TTS (e.g., 'excited', 'celebrating').
        avatar_dir: Directory to check for images.

    Returns:
        Resolved emotion name that has images available.
    """
    # 1. Check if emotion has images directly
    if discover_variants(avatar_dir, emotion):
        return emotion

    # 2. Try standard emotion mapping (for the 7 TTS emotions)
    mapped_emotion = EMOTION_AVATAR_MAP.get(emotion)
    if mapped_emotion and discover_variants(avatar_dir, mapped_emotion):
        logger.debug(f'Emotion {emotion} -> {mapped_emotion} (standard mapping)')
        return mapped_emotion

    # 3. Try hierarchy fallback (for specific → generic mappings)
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

    for item in registry_config:
        if not isinstance(item, dict) or 'path' not in item or 'tags' not in item:
            logger.warning(f'Invalid image registry entry: {item}')
            continue

        path = Path(item['path'])
        tags = item['tags']

        # Resolve relative paths
        if not path.is_absolute():
            path = avatar_dir / path

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
            logger.warning(f'Image {path} has no emotion or control tag, skipping')
            continue

        entries.append(ImageEntry(path=path, tags=tags))

    logger.debug(f'Loaded {len(entries)} images from registry')
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
    (.png, .jpg, .jpeg, .webp). Falls back to root directory if no subdirectory exists.

    Args:
        avatar_dir: Directory containing avatar images (or emotion subdirectories).
        emotion: Base emotion name (e.g., 'excited', 'waiting').

    Returns:
        Sorted list of image paths. Empty if no images found.
    """
    variants: list[Path] = []
    supported_formats = ['*.png', '*.jpg', '*.jpeg', '*.webp']

    # Check for emotion subdirectory first (e.g., ~/.claude/luna/excited/)
    emotion_subdir = avatar_dir / emotion
    if emotion_subdir.is_dir():
        for pattern in supported_formats:
            variants.extend(sorted(emotion_subdir.glob(pattern)))
        return variants

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

    return list(dict.fromkeys(variants))  # Remove duplicates while preserving order


# ============================================================================
# Position Persistence
# ============================================================================

def _load_position() -> tuple[int, int] | None:
    """Load saved window position from temp file.

    Returns:
        Tuple of (x, y) coordinates, or None if no saved position.
    """
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
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, True)

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
        self.current_emotion: str = WAITING_STATE
        self.current_avatar_path: Path | None = None
        self._running = True
        self._fade_alpha = 1.0

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
        self._flip_threshold: float = ANIMATION_CONFIG['flip_threshold']
        self._flip_duration: int = ANIMATION_CONFIG['flip_duration']
        self._flip_steps: int = ANIMATION_CONFIG['flip_steps']

        # Load image registry from config
        self._image_registry = load_image_registry(self.avatar_dir, IMAGE_REGISTRY)

        # Interactive controls state
        self._buttons_visible = False
        self._button_frame: tk.Frame | None = None
        self._preview_active = False
        self._preview_emotion: str | None = None
        self._tts_enabled = True
        self._stt_enabled = True
        self._tts_button: tk.Button | None = None
        self._stt_button: tk.Button | None = None
        self._mouse_over_buttons = False

        # Hover lock state (pauses variant cycling while mouse is over avatar)
        self._hover_locked = False
        self._was_cycling = False

        # Tag editor button state (canvas items shown on hover)
        self._tag_button_bg_id: int | None = None
        self._tag_button_text_id: int | None = None

        logger.info(f'Avatar dir: {self.avatar_dir}')
        if monitor_pid:
            logger.info(f'Monitoring PID: {monitor_pid}')

        # Image cache: file_path_str -> PhotoImage
        self._image_cache: dict[str, ImageTk.PhotoImage] = {}

        # Build window
        self._root = tk.Tk()
        self._root.title('Luna Avatar')
        self._root.overrideredirect(True)
        self._root.attributes('-topmost', True)

        # Transparent background
        self._transparent_color = '#010101'
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

        # Image item on canvas (anchored to bottom-center)
        self._image_item = self._canvas.create_image(
            self.size // 2, self.size,
            anchor=tk.S,
        )

        # Position window
        saved_pos = _load_position()
        if saved_pos:
            self._root.geometry(f'{self.size}x{self.size}+{saved_pos[0]}+{saved_pos[1]}')
        else:
            self._position_bottom_right()

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

        # Make click-through on Windows (pass clicks to windows behind)
        if sys.platform == 'win32':
            self._setup_click_through()

        # Load initial avatar (waiting state)
        self._switch_emotion(WAITING_STATE)

        logger.info(f'Avatar widget initialized ({self.size}x{self.size})')

    def _position_bottom_right(self) -> None:
        """Position window in the bottom-right corner, anchored to bottom."""
        margin = 20
        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()
        x = screen_w - self.size - margin
        # Anchor to very bottom of screen (above taskbar ~40px)
        y = screen_h - self.size - 40
        self._root.geometry(f'{self.size}x{self.size}+{x}+{y}')

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
            variants = []

            # Tag-based lookup (if registry is populated)
            if self._image_registry:
                # Map emotion to avatar base name for consistency
                avatar_name = EMOTION_AVATAR_MAP.get(emotion, emotion)

                # Get all images with this emotion tag (exclude all control tags)
                control_tag_prefixes = {'control-', 'control'}
                emotion_images = [
                    img for img in self._image_registry
                    if (avatar_name.lower() in img.tag_set and
                        not any(tag.startswith('control') for tag in img.tag_set))
                ]

                # Apply tag filters
                if emotion_images:
                    filtered = filter_images_by_tags(
                        emotion_images,
                        self._include_tags,
                        self._exclude_tags,
                        self._require_all_include
                    )
                    variants = [img.path for img in filtered]

                # Fallback: if filters excluded everything, ignore filters for this emotion
                if not variants and emotion_images:
                    variants = [img.path for img in emotion_images]
                    logger.warning(f'Tag filters excluded all {emotion} images, ignoring filters')

            # Directory-based discovery (backward compatibility)
            if not variants:
                avatar_name = EMOTION_AVATAR_MAP.get(emotion, emotion)
                variants = discover_variants(self.avatar_dir, avatar_name)

            # For waiting state, try 'waiting' first, then fall back to cheerful
            if not variants and emotion == WAITING_STATE:
                cheerful_path = self.avatar_dir / f'{DEFAULT_AVATAR}.png'
                if cheerful_path.exists():
                    variants = [cheerful_path]

            # For any emotion with no variants, fall back to default avatar
            if not variants and emotion != WAITING_STATE:
                default_path = self.avatar_dir / f'{DEFAULT_AVATAR}.png'
                if default_path.exists():
                    variants = [default_path]
                    logger.warning(f'No variants for {emotion}, falling back to {DEFAULT_AVATAR}')

            self._variant_cache[emotion] = variants

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

        try:
            img = Image.open(image_path)
            img = img.convert('RGBA')

            # Maintain aspect ratio, fit within size
            img.thumbnail((self.size, self.size), Image.Resampling.LANCZOS)

            # Create transparent background and paste image anchored to bottom
            bg = Image.new('RGBA', (self.size, self.size), (1, 1, 1, 0))
            offset_x = (self.size - img.width) // 2
            offset_y = self.size - img.height  # Anchor to bottom
            bg.paste(img, (offset_x, offset_y), img)

            photo = ImageTk.PhotoImage(bg)
            self._image_cache[cache_key] = photo
            return photo
        except Exception as e:
            logger.error(f'Failed to load image {image_path}: {e}')
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
            logger.debug(f'Displaying: {image_path.name}')

    def _switch_emotion(self, emotion: str, force_flip: bool = False) -> None:
        """Switch to a new emotion, resetting variant cycling.

        Decides between fade and flip animations based on tag similarity.

        Args:
            emotion: New emotion name to display.
            force_flip: Force flip animation regardless of tag similarity.
        """
        if emotion == self.current_emotion:
            return

        old_emotion = self.current_emotion
        variants = self._get_variants(emotion)

        if not variants:
            logger.warning(f'No variants found for emotion: {emotion}')
            return

        # Choose a random variant for visual variety
        new_variant_index = random.randint(0, len(variants) - 1)
        new_image_path = variants[new_variant_index]

        # Determine if we should use flip animation based on tag similarity
        use_flip = force_flip
        if not use_flip and self._image_registry and self.current_avatar_path:
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
                use_flip = similarity < self._flip_threshold
                logger.debug(f'Tag similarity: {similarity:.2f}, flip={use_flip}')

        # Execute appropriate transition
        if use_flip:
            self._flip_transition(emotion, new_image_path)
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
            self._root.after(FADE_INTERVAL_MS, self._fade_in)
        else:
            self._root.after(FADE_INTERVAL_MS, self._fade_out)

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
            self._root.after(FADE_INTERVAL_MS, self._fade_in)

    def _flip_transition(self, new_emotion: str, new_image_path: Path) -> None:
        """Animate horizontal flip transition, changing image mid-flip.

        Animation sequence:
        1. Scale X from 1.0 → 0.0 (flip left, image disappears)
        2. Switch to new emotion and image (at X scale 0.0, invisible)
        3. Scale X from 0.0 → 1.0 (flip right, new image appears)

        Args:
            new_emotion: Emotion to transition to.
            new_image_path: Path to the new image to display.
        """
        if not self._running:
            return

        steps = self._flip_steps
        delay_ms = self._flip_duration / (steps * 2)  # Divide by 2 for flip-out + flip-in

        # Flip out (current image)
        def flip_out(step: int = 0) -> None:
            if not self._running or step >= steps:
                # Switch emotion and image at full transparency
                old_emotion = self.current_emotion
                self.current_emotion = new_emotion
                self._current_variant_index = 0
                self._display_variant(new_image_path)
                logger.info(f'Emotion: {old_emotion} -> {new_emotion} (flip animation)')

                # Start flip-in
                self._root.after(int(delay_ms), lambda: flip_in(0))
                return

            scale_x = 1.0 - (step / steps)
            self._scale_canvas_x(scale_x)
            self._root.after(int(delay_ms), lambda: flip_out(step + 1))

        # Flip in (new image)
        def flip_in(step: int = 0) -> None:
            if not self._running or step >= steps:
                # Restore normal scale
                self._scale_canvas_x(1.0)
                # Resume variant cycling if multiple variants exist
                variants = self._get_variants(self.current_emotion)
                if len(variants) > 1 and self._cycle_after_id is None:
                    self._cycle_after_id = self._root.after(
                        VARIANT_CYCLE_INTERVAL_MS, self._cycle_variant
                    )
                return

            scale_x = step / steps
            self._scale_canvas_x(scale_x)
            self._root.after(int(delay_ms), lambda: flip_in(step + 1))

        # Cancel any existing cycle timer
        if self._cycle_after_id is not None:
            with contextlib.suppress(tk.TclError):
                self._root.after_cancel(self._cycle_after_id)
            self._cycle_after_id = None

        # Start flip-out animation
        flip_out(0)

    def _scale_canvas_x(self, scale: float) -> None:
        """Scale canvas horizontally for flip effect.

        Uses PIL to horizontally scale the current image.

        Args:
            scale: Scale factor (0.0 = invisible, 1.0 = normal width).
        """
        if not self.current_avatar_path:
            return

        try:
            img = Image.open(self.current_avatar_path)
            img = img.convert('RGBA')

            # Scale width while maintaining height
            new_width = max(1, int(img.width * scale))
            scaled = img.resize((new_width, img.height), Image.Resampling.LANCZOS)

            # Maintain aspect ratio, fit within size
            scaled.thumbnail((self.size, self.size), Image.Resampling.LANCZOS)

            # Create transparent background and paste image anchored to bottom
            bg = Image.new('RGBA', (self.size, self.size), (1, 1, 1, 0))
            offset_x = (self.size - scaled.width) // 2
            offset_y = self.size - scaled.height  # Anchor to bottom
            bg.paste(scaled, (offset_x, offset_y), scaled)

            photo = ImageTk.PhotoImage(bg)
            self._canvas.itemconfig(self._image_item, image=photo)
            # Keep reference to prevent garbage collection
            self._canvas._current_photo = photo  # type: ignore[attr-defined]
        except Exception as e:
            logger.error(f'Failed to scale image {self.current_avatar_path}: {e}')

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
        """Reset idle timer (called when TTS starts speaking)."""
        self._idle_start_time = None
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
    # Event Handlers
    # ========================================================================

    def _on_right_click(self, event: tk.Event) -> None:
        """Handle right-click to close widget."""
        logger.info('Avatar widget closed via right-click')
        self.stop()

    def _on_drag_start(self, event: tk.Event) -> None:
        """Start drag operation."""
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag_motion(self, event: tk.Event) -> None:
        """Handle drag motion to move window."""
        x = self._root.winfo_x() + (event.x - self._drag_x)
        y = self._root.winfo_y() + (event.y - self._drag_y)
        self._root.geometry(f'+{x}+{y}')

    def _on_drag_release(self, event: tk.Event) -> None:
        """Save position when drag ends."""
        _save_position(self._root.winfo_x(), self._root.winfo_y())

    # ========================================================================
    # Interactive Controls
    # ========================================================================

    def _on_mouse_enter(self, event: tk.Event) -> None:
        """Handle mouse entering avatar area - show controls and pause cycling."""
        if not self._buttons_visible:
            self._show_buttons()

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

        # Show tag editor button
        self._show_tag_button()

    def _on_mouse_leave(self, event: tk.Event) -> None:
        """Handle mouse leaving avatar area - hide buttons and resume cycling."""
        # Schedule check after short delay to allow mouse to enter button area
        self._root.after(100, self._check_hide_buttons)
        self._root.after(100, self._check_release_hover_lock)

    def _check_hide_buttons(self) -> None:
        """Check if mouse is still over avatar/buttons area, hide if not."""
        if self._buttons_visible and not self._mouse_over_buttons:
            # Check if mouse is still over canvas
            try:
                x, y = self._root.winfo_pointerxy()
                canvas_x = self._canvas.winfo_rootx()
                canvas_y = self._canvas.winfo_rooty()
                canvas_w = self._canvas.winfo_width()
                canvas_h = self._canvas.winfo_height()

                # If mouse is outside both canvas and button frame, hide buttons
                if not (canvas_x <= x <= canvas_x + canvas_w and canvas_y <= y <= canvas_y + canvas_h):
                    if self._button_frame:
                        frame_x = self._button_frame.winfo_rootx()
                        frame_y = self._button_frame.winfo_rooty()
                        frame_w = self._button_frame.winfo_width()
                        frame_h = self._button_frame.winfo_height()
                        if not (frame_x <= x <= frame_x + frame_w and frame_y <= y <= frame_y + frame_h):
                            self._hide_buttons()
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

            still_over_buttons = False
            if self._button_frame and self._buttons_visible:
                frame_x = self._button_frame.winfo_rootx()
                frame_y = self._button_frame.winfo_rooty()
                frame_w = self._button_frame.winfo_width()
                frame_h = self._button_frame.winfo_height()
                still_over_buttons = (frame_x <= x <= frame_x + frame_w
                                      and frame_y <= y <= frame_y + frame_h)

            if not still_over_canvas and not still_over_buttons:
                self._hover_locked = False
                self._hide_tag_button()

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
    # Tag Editor Button (canvas overlay)
    # ========================================================================

    def _show_tag_button(self) -> None:
        """Display tag editor button in top-right corner of canvas."""
        if self._tag_button_bg_id is not None:
            return  # Already visible

        # Position in top-right corner with margin
        btn_w, btn_h = 30, 24
        margin = 8
        x = self._canvas.winfo_width() - btn_w - margin
        y = margin

        # Background rectangle
        self._tag_button_bg_id = self._canvas.create_rectangle(
            x, y, x + btn_w, y + btn_h,
            fill='#3a3a3a',
            outline='#888888',
            width=1,
            tags='tag_button',
        )

        # Label text
        self._tag_button_text_id = self._canvas.create_text(
            x + btn_w // 2, y + btn_h // 2,
            text='Tags',
            fill='#cccccc',
            font=('Segoe UI', 8),
            tags='tag_button',
        )

        # Bind click event on the tag
        self._canvas.tag_bind('tag_button', '<Button-1>', self._open_tag_editor)

        # Hover effect on tag button
        self._canvas.tag_bind('tag_button', '<Enter>', self._on_tag_button_enter)
        self._canvas.tag_bind('tag_button', '<Leave>', self._on_tag_button_leave)

        logger.debug('[AVATAR] Tag button shown')

    def _hide_tag_button(self) -> None:
        """Hide tag editor button from canvas."""
        if self._tag_button_bg_id is not None:
            self._canvas.delete('tag_button')
            self._tag_button_bg_id = None
            self._tag_button_text_id = None
            logger.debug('[AVATAR] Tag button hidden')

    def _on_tag_button_enter(self, event: tk.Event) -> None:
        """Highlight tag button on hover."""
        if self._tag_button_bg_id is not None:
            self._canvas.itemconfig(self._tag_button_bg_id, fill='#555555')
            self._canvas.itemconfig(self._tag_button_text_id, fill='#ffffff')

    def _on_tag_button_leave(self, event: tk.Event) -> None:
        """Restore tag button on hover leave."""
        if self._tag_button_bg_id is not None:
            self._canvas.itemconfig(self._tag_button_bg_id, fill='#3a3a3a')
            self._canvas.itemconfig(self._tag_button_text_id, fill='#cccccc')

    def _open_tag_editor(self, event: tk.Event | None = None) -> None:
        """Open the tag editor dialog for the currently displayed image.

        Finds the ImageEntry matching the current avatar path and opens
        a TagEditorDialog populated with all known tags in the registry.

        Args:
            event: Optional Tkinter event (from canvas click binding).
        """
        if not self.current_avatar_path or not self._image_registry:
            logger.warning('[TAGS] No current image or empty registry')
            return

        # Find the ImageEntry for the current image
        current_entry: ImageEntry | None = None
        for img in self._image_registry:
            if img.path == self.current_avatar_path or img.path.resolve() == self.current_avatar_path.resolve():
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

        # Open dialog
        TagEditorDialog(
            self._root,
            current_entry,
            all_tags,
            lambda new_tags: self._save_image_tags(current_entry, new_tags),
        )
        logger.info(f'[TAGS] Opened editor for: {current_entry.path.name}')

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
    # Control Buttons
    # ========================================================================

    def _show_buttons(self) -> None:
        """Show control buttons at bottom of avatar."""
        if self._buttons_visible:
            return

        # Disable click-through when showing buttons
        if sys.platform == 'win32':
            self._disable_click_through()

        # Create button frame if not exists
        if self._button_frame is None:
            self._button_frame = self._create_button_frame()

        self._button_frame.pack(side=tk.BOTTOM, pady=5)
        self._buttons_visible = True
        logger.debug('Control buttons shown')

    def _hide_buttons(self) -> None:
        """Hide control buttons and tag editor button."""
        if not self._buttons_visible:
            return

        if self._button_frame:
            self._button_frame.pack_forget()

        self._buttons_visible = False
        self._hide_tag_button()

        # Re-enable click-through when hiding buttons
        if sys.platform == 'win32':
            self._enable_click_through()

        # Restore emotion if preview was active
        if self._preview_active:
            self._restore_emotion()

        logger.debug('Control buttons hidden')

    def _create_button_frame(self) -> tk.Frame:
        """Create the control button frame.

        Returns:
            Frame containing TTS, STT, and Close buttons.
        """
        frame = tk.Frame(self._root, bg=self._transparent_color)

        # Bind hover events to frame to track when mouse is over buttons
        frame.bind('<Enter>', lambda e: setattr(self, '_mouse_over_buttons', True))
        frame.bind('<Leave>', lambda e: setattr(self, '_mouse_over_buttons', False))

        # TTS toggle button
        self._tts_button = tk.Button(
            frame,
            text='🔊' if self._tts_enabled else '🔇',
            command=self._toggle_tts,
            bg='#2a2a2a',
            fg='white',
            relief='flat',
            font=('Segoe UI Emoji', 14),
            width=3,
            cursor='hand2'
        )
        self._tts_button.bind('<Enter>', lambda e: self._preview_image('tts'))
        self._tts_button.bind('<Leave>', lambda e: self._restore_emotion())
        self._tts_button.pack(side='left', padx=2)

        # STT toggle button
        self._stt_button = tk.Button(
            frame,
            text='🎤' if self._stt_enabled else '🔇',
            command=self._toggle_stt,
            bg='#2a2a2a',
            fg='white',
            relief='flat',
            font=('Segoe UI Emoji', 14),
            width=3,
            cursor='hand2'
        )
        self._stt_button.bind('<Enter>', lambda e: self._preview_image('stt'))
        self._stt_button.bind('<Leave>', lambda e: self._restore_emotion())
        self._stt_button.pack(side='left', padx=2)

        # Close button
        close_button = tk.Button(
            frame,
            text='❌',
            command=self._close_with_animation,
            bg='#2a2a2a',
            fg='white',
            relief='flat',
            font=('Segoe UI Emoji', 14),
            width=3,
            cursor='hand2'
        )
        close_button.bind('<Enter>', lambda e: self._preview_image('close'))
        close_button.bind('<Leave>', lambda e: self._restore_emotion())
        close_button.pack(side='left', padx=2)

        return frame

    def _preview_image(self, control_type: str) -> None:
        """Show preview image for hovered button.

        Args:
            control_type: Type of control ('tts', 'stt', or 'close').
        """
        if not self._preview_active:
            self._preview_emotion = self.current_emotion
            self._preview_active = True

        # Determine preview image based on control type (functional tag names)
        if control_type == 'tts':
            control_tag = 'control-tts-hover-on' if self._tts_enabled else 'control-tts-hover-off'
        elif control_type == 'stt':
            control_tag = 'control-stt-hover-on' if self._stt_enabled else 'control-stt-hover-off'
        elif control_type == 'close':
            control_tag = 'control-close-hover'
        else:
            return

        self._load_control_image(control_tag)

    def _restore_emotion(self) -> None:
        """Restore previous emotion after preview."""
        if self._preview_active and self._preview_emotion:
            self._preview_active = False
            emotion_to_restore = self._preview_emotion
            self._preview_emotion = None

            # Force switch back to previous emotion
            self.current_emotion = ''  # Reset to force update
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
        self._update_button_icon(self._tts_button, self._tts_enabled, '🔊', '🔇')
        self._show_feedback('tts')
        logger.info(f'TTS {"enabled" if self._tts_enabled else "disabled"}')

    def _toggle_stt(self) -> None:
        """Toggle STT enabled/disabled state."""
        self._stt_enabled = not self._stt_enabled
        self._write_stt_state(self._stt_enabled)
        self._update_button_icon(self._stt_button, self._stt_enabled, '🎤', '🔇')
        self._show_feedback('stt')
        logger.info(f'STT {"enabled" if self._stt_enabled else "disabled"}')

    def _update_button_icon(self, button: tk.Button | None, enabled: bool, on_icon: str, off_icon: str) -> None:
        """Update button icon based on state.

        Args:
            button: Button widget to update.
            enabled: Whether the feature is enabled.
            on_icon: Icon to show when enabled.
            off_icon: Icon to show when disabled.
        """
        if button:
            button.config(text=on_icon if enabled else off_icon)

    def _show_feedback(self, feedback_type: str) -> None:
        """Show confirmation image for 1 second, then restore emotion.

        Args:
            feedback_type: Type of feedback ('tts' or 'stt').
        """
        control_tag = f'control-{feedback_type}-clicked'
        self._load_control_image(control_tag)
        self._root.after(1000, self._restore_emotion)

    def _write_tts_state(self, enabled: bool) -> None:
        """Write TTS enabled state to IPC file.

        Args:
            enabled: Whether TTS is enabled.
        """
        if self.monitor_pid is None:
            return

        state_file = Path(tempfile.gettempdir()) / f'pyagentvox_tts_enabled_{self.monitor_pid}.txt'
        with contextlib.suppress(OSError):
            state_file.write_text('1' if enabled else '0', encoding='utf-8')
            logger.debug(f'Wrote TTS state: {enabled}')

    def _write_stt_state(self, enabled: bool) -> None:
        """Write STT enabled state to IPC file.

        Args:
            enabled: Whether STT is enabled.
        """
        if self.monitor_pid is None:
            return

        state_file = Path(tempfile.gettempdir()) / f'pyagentvox_stt_enabled_{self.monitor_pid}.txt'
        with contextlib.suppress(OSError):
            state_file.write_text('1' if enabled else '0', encoding='utf-8')
            logger.debug(f'Wrote STT state: {enabled}')

    def _close_with_animation(self) -> None:
        """Show crying animation and slide avatar down off screen."""
        # Show close animation image
        self._load_control_image('control-close-animation')
        self._root.update()
        time.sleep(0.5)

        # Animate slide down
        steps = 30
        distance = 300
        delay = 0.033  # ~30 FPS

        start_x = self._root.winfo_x()
        start_y = self._root.winfo_y()

        for i in range(steps):
            offset = int((distance / steps) * i)
            self._root.geometry(f'+{start_x}+{start_y + offset}')
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
                self._switch_emotion(self.current_emotion)

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
                    # TTS started speaking - reset idle timer
                    self._is_speaking = True
                    self._reset_idle_timer()
                elif not is_speaking and self._is_speaking:
                    # TTS stopped speaking - start idle timer
                    self._is_speaking = False
                    self._start_idle_timer()

                # Resolve emotion through hierarchy if needed
                resolved_emotion = resolve_emotion_hierarchy(emotion, self.avatar_dir)

                if resolved_emotion != self.current_emotion:
                    logger.debug(f'Emotion file changed: {emotion} -> {resolved_emotion}')
                    self._fade_transition(resolved_emotion)
        except Exception as e:
            logger.error(f'Error polling emotion file: {e}')

        # Schedule next poll
        if self._running:
            self._root.after(EMOTION_POLL_INTERVAL_MS, self._poll_emotion_file)

    # ========================================================================
    # Lifecycle
    # ========================================================================

    def run(self) -> None:
        """Start the avatar widget and enter the Tkinter main loop.

        This method blocks until the widget is closed.
        """
        # Start polling emotion file if monitoring a PID
        if self.monitor_pid is not None:
            self._root.after(EMOTION_POLL_INTERVAL_MS, self._poll_emotion_file)
            logger.info(f'Monitoring emotion file for PID {self.monitor_pid}')

            # Start polling filter control file
            self._root.after(FILTER_POLL_INTERVAL_MS, self._poll_filter_control_file)
            logger.info(f'Monitoring filter control file for PID {self.monitor_pid}')

        # Start idle timer for bored/sleeping transitions
        self._start_idle_timer()

        logger.info('Avatar widget running (right-click to close)')

        try:
            self._root.mainloop()
        except KeyboardInterrupt:
            logger.info('Avatar widget interrupted')
        finally:
            self._running = False

    def stop(self) -> None:
        """Stop the avatar widget and save position."""
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

    avatar_dir = Path(args.avatar_dir) if args.avatar_dir else None

    # Scan mode: show available emotions and exit
    if args.scan:
        print_avatar_scan(avatar_dir)
        return

    # Normal mode: launch widget
    widget = AvatarWidget(
        avatar_dir=avatar_dir,
        size=args.size,
        monitor_pid=args.pid,
    )
    widget.run()


if __name__ == '__main__':
    main()
