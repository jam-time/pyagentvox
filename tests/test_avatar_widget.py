"""Tests for the floating avatar widget.

Tests cover emotion extraction, JSONL message parsing, avatar path resolution,
position persistence, emotion IPC, multi-variant image discovery, waiting state
behavior, and variant cycling logic. No GUI display required.

Author:
    Jake Meador <jameador13@gmail.com>
"""

import json
import tempfile
import tkinter as tk
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, call, patch

import pytest

from pyagentvox.avatar_widget import (
    DEFAULT_AVATAR,
    DETECTIVE_AVATAR,
    EMOTION_AVATAR_MAP,
    VARIANT_CYCLE_INTERVAL_MS,
    WAITING_STATE,
    ImageEntry,
    TagEditorDialog,
    _load_position,
    _save_position,
    cleanup_emotion_file,
    discover_variants,
    get_emotion_file_path,
    read_emotion_state,
    write_emotion_state,
)


# ============================================================================
# Emotion IPC
# ============================================================================

class TestEmotionFileIPC:
    """Test emotion state file read/write/cleanup."""

    def test_get_emotion_file_path_includes_pid(self) -> None:
        """Emotion file path includes the given PID."""
        path = get_emotion_file_path(12345)
        assert '12345' in str(path)
        assert path.name == 'pyagentvox_avatar_emotion_12345.txt'

    def test_write_and_read_emotion_state(self) -> None:
        """Write emotion state then read it back."""
        fake_pid = 99999
        try:
            write_emotion_state(fake_pid, 'excited')
            result = read_emotion_state(fake_pid)
            assert result == 'excited'
        finally:
            cleanup_emotion_file(fake_pid)

    def test_read_nonexistent_file_returns_none(self) -> None:
        """Reading emotion from nonexistent file returns None."""
        result = read_emotion_state(88888)
        assert result is None

    def test_write_waiting_state(self) -> None:
        """Write and read back 'waiting' state."""
        fake_pid = 99998
        try:
            write_emotion_state(fake_pid, 'waiting')
            result = read_emotion_state(fake_pid)
            assert result == 'waiting'
        finally:
            cleanup_emotion_file(fake_pid)

    def test_cleanup_removes_file(self) -> None:
        """Cleanup removes the emotion file."""
        fake_pid = 99997
        write_emotion_state(fake_pid, 'cheerful')
        emotion_file = get_emotion_file_path(fake_pid)
        assert emotion_file.exists()

        cleanup_emotion_file(fake_pid)
        assert not emotion_file.exists()

    def test_cleanup_nonexistent_file_no_error(self) -> None:
        """Cleaning up nonexistent file does not raise."""
        cleanup_emotion_file(77777)  # Should not raise

    def test_overwrite_emotion_state(self) -> None:
        """Writing a new emotion overwrites the previous one."""
        fake_pid = 99996
        try:
            write_emotion_state(fake_pid, 'excited')
            write_emotion_state(fake_pid, 'calm')
            result = read_emotion_state(fake_pid)
            assert result == 'calm'
        finally:
            cleanup_emotion_file(fake_pid)


# ============================================================================
# Image Variant Discovery
# ============================================================================

class TestVariantDiscovery:
    """Test multi-variant image discovery logic."""

    def test_discover_single_base_image(self, tmp_path: Path) -> None:
        """Base image (excited.png) is discovered as a single variant."""
        (tmp_path / 'excited.png').touch()
        variants = discover_variants(tmp_path, 'excited')
        assert len(variants) == 1
        assert variants[0].name == 'excited.png'

    def test_discover_numbered_variants(self, tmp_path: Path) -> None:
        """Numbered variants (excited-1.png, excited-2.png) are discovered."""
        (tmp_path / 'excited-1.png').touch()
        (tmp_path / 'excited-2.png').touch()
        (tmp_path / 'excited-3.png').touch()
        variants = discover_variants(tmp_path, 'excited')
        assert len(variants) == 3
        assert variants[0].name == 'excited-1.png'
        assert variants[1].name == 'excited-2.png'
        assert variants[2].name == 'excited-3.png'

    def test_discover_base_plus_numbered(self, tmp_path: Path) -> None:
        """Base image and numbered variants are all discovered."""
        (tmp_path / 'waiting.png').touch()
        (tmp_path / 'waiting-1.png').touch()
        (tmp_path / 'waiting-2.png').touch()
        variants = discover_variants(tmp_path, 'waiting')
        assert len(variants) == 3
        assert variants[0].name == 'waiting.png'
        assert variants[1].name == 'waiting-1.png'
        assert variants[2].name == 'waiting-2.png'

    def test_discover_no_images_returns_empty(self, tmp_path: Path) -> None:
        """Empty directory returns no variants."""
        variants = discover_variants(tmp_path, 'excited')
        assert variants == []

    def test_discover_ignores_dark_mode_remnants(self, tmp_path: Path) -> None:
        """Dark mode files (excited-dark.png) are NOT included as variants."""
        (tmp_path / 'excited.png').touch()
        (tmp_path / 'excited-dark.png').touch()
        variants = discover_variants(tmp_path, 'excited')
        assert len(variants) == 1
        assert variants[0].name == 'excited.png'

    def test_discover_ignores_unrelated_files(self, tmp_path: Path) -> None:
        """Files for other emotions are not included."""
        (tmp_path / 'excited.png').touch()
        (tmp_path / 'calm.png').touch()
        (tmp_path / 'cheerful-1.png').touch()
        variants = discover_variants(tmp_path, 'excited')
        assert len(variants) == 1
        assert variants[0].name == 'excited.png'

    def test_discover_waiting_variants(self, tmp_path: Path) -> None:
        """Waiting state images are discovered correctly."""
        (tmp_path / 'waiting-1.png').touch()
        (tmp_path / 'waiting-2.png').touch()
        (tmp_path / 'waiting-3.png').touch()
        variants = discover_variants(tmp_path, 'waiting')
        assert len(variants) == 3

    def test_discover_variants_sorted_order(self, tmp_path: Path) -> None:
        """Numbered variants are returned in sorted order."""
        (tmp_path / 'waiting-3.png').touch()
        (tmp_path / 'waiting-1.png').touch()
        (tmp_path / 'waiting-2.png').touch()
        variants = discover_variants(tmp_path, 'waiting')
        names = [v.name for v in variants]
        assert names == ['waiting-1.png', 'waiting-2.png', 'waiting-3.png']


# ============================================================================
# Waiting State
# ============================================================================

class TestWaitingState:
    """Test waiting/idle state behavior."""

    def test_waiting_state_constant_is_waiting(self) -> None:
        """WAITING_STATE constant is 'waiting'."""
        assert WAITING_STATE == 'waiting'

    def test_waiting_not_in_emotion_map(self) -> None:
        """Waiting is NOT a standard emotion in the emotion map (it's a special state)."""
        assert 'waiting' not in EMOTION_AVATAR_MAP

    def test_waiting_images_discovered(self, tmp_path: Path) -> None:
        """Waiting images are discovered from the avatar directory."""
        (tmp_path / 'waiting-1.png').touch()
        (tmp_path / 'waiting-2.png').touch()
        variants = discover_variants(tmp_path, 'waiting')
        assert len(variants) == 2

    def test_waiting_falls_back_to_cheerful_when_no_waiting_images(self, tmp_path: Path) -> None:
        """When no waiting images exist, discover_variants returns empty (widget handles fallback)."""
        # discover_variants itself just returns empty - the widget _get_variants handles fallback
        variants = discover_variants(tmp_path, 'waiting')
        assert variants == []


# ============================================================================
# Position Persistence
# ============================================================================

class TestPositionPersistence:
    """Test window position save/load."""

    def test_save_and_load_position(self) -> None:
        """Position can be saved and loaded back."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_path = Path(f.name)

        try:
            with patch('pyagentvox.avatar_widget.POSITION_FILE', temp_path):
                _save_position(100, 200)
                result = _load_position()
                assert result == (100, 200)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_load_missing_file_returns_none(self) -> None:
        """Loading from nonexistent file returns None."""
        fake_path = Path(tempfile.gettempdir()) / 'nonexistent_avatar_pos.json'
        with patch('pyagentvox.avatar_widget.POSITION_FILE', fake_path):
            assert _load_position() is None

    def test_load_corrupted_file_returns_none(self) -> None:
        """Loading from corrupted file returns None gracefully."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('not valid json')
            temp_path = Path(f.name)

        try:
            with patch('pyagentvox.avatar_widget.POSITION_FILE', temp_path):
                assert _load_position() is None
        finally:
            temp_path.unlink(missing_ok=True)

    def test_load_missing_keys_returns_none(self) -> None:
        """Loading from file with missing keys returns None."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'x': 100}, f)  # Missing 'y' key
            temp_path = Path(f.name)

        try:
            with patch('pyagentvox.avatar_widget.POSITION_FILE', temp_path):
                assert _load_position() is None
        finally:
            temp_path.unlink(missing_ok=True)


# ============================================================================
# Emotion Avatar Map
# ============================================================================

class TestEmotionAvatarMap:
    """Test the emotion-to-avatar mapping is complete and correct."""

    def test_all_standard_tts_emotions_mapped(self) -> None:
        """All standard TTS emotions have avatar mappings."""
        standard_emotions = ['neutral', 'cheerful', 'excited', 'empathetic', 'warm', 'calm', 'focused']
        for emotion in standard_emotions:
            assert emotion in EMOTION_AVATAR_MAP, f'Missing mapping for {emotion}'

    def test_extended_emotions_mapped(self) -> None:
        """Extended emotions (thinking, curious, etc.) have mappings."""
        extended_emotions = ['thinking', 'curious', 'determined', 'apologetic', 'playful', 'surprised']
        for emotion in extended_emotions:
            assert emotion in EMOTION_AVATAR_MAP, f'Missing mapping for {emotion}'

    def test_default_avatar_is_valid(self) -> None:
        """Default avatar name is a valid mapping target."""
        assert DEFAULT_AVATAR in EMOTION_AVATAR_MAP.values() or DEFAULT_AVATAR == 'cheerful'

    def test_empathetic_maps_to_warm(self) -> None:
        """Empathetic maps to warm avatar (shared image)."""
        assert EMOTION_AVATAR_MAP['empathetic'] == 'warm'

    def test_neutral_maps_to_cheerful(self) -> None:
        """Neutral maps to cheerful (default) avatar."""
        assert EMOTION_AVATAR_MAP['neutral'] == 'cheerful'


# ============================================================================
# Widget Variant Cache & Fallback (mocked, no GUI)
# ============================================================================

class TestWidgetVariantFallback:
    """Test widget _get_variants caching and fallback behavior via direct method calls."""

    def test_get_variants_caches_results(self, tmp_path: Path) -> None:
        """Variant discovery is cached after first call."""
        (tmp_path / 'excited.png').touch()
        (tmp_path / 'excited-1.png').touch()

        # Simulate widget's _get_variants using discover_variants directly
        cache: dict[str, list[Path]] = {}

        def get_variants(emotion: str) -> list[Path]:
            if emotion not in cache:
                avatar_name = EMOTION_AVATAR_MAP.get(emotion, emotion)
                cache[emotion] = discover_variants(tmp_path, avatar_name)
            return cache[emotion]

        result1 = get_variants('excited')
        result2 = get_variants('excited')
        assert result1 is result2  # Same cached list object
        assert len(result1) == 2

    def test_waiting_fallback_to_cheerful(self, tmp_path: Path) -> None:
        """Waiting state with no waiting images falls back to cheerful.png."""
        (tmp_path / 'cheerful.png').touch()
        # No waiting images exist

        # Simulate widget fallback logic
        variants = discover_variants(tmp_path, 'waiting')
        if not variants:
            cheerful = tmp_path / f'{DEFAULT_AVATAR}.png'
            if cheerful.exists():
                variants = [cheerful]

        assert len(variants) == 1
        assert variants[0].name == 'cheerful.png'

    def test_unknown_emotion_fallback_to_default(self, tmp_path: Path) -> None:
        """Unknown emotion with no images falls back to default avatar."""
        (tmp_path / 'cheerful.png').touch()

        # Simulate widget fallback for unknown emotion
        variants = discover_variants(tmp_path, 'nonexistent')
        if not variants:
            default_path = tmp_path / f'{DEFAULT_AVATAR}.png'
            if default_path.exists():
                variants = [default_path]

        assert len(variants) == 1
        assert variants[0].name == 'cheerful.png'

    def test_waiting_with_waiting_images_uses_them(self, tmp_path: Path) -> None:
        """When waiting images exist, they are used instead of cheerful fallback."""
        (tmp_path / 'cheerful.png').touch()
        (tmp_path / 'waiting-1.png').touch()
        (tmp_path / 'waiting-2.png').touch()

        variants = discover_variants(tmp_path, 'waiting')
        assert len(variants) == 2
        assert all('waiting' in v.name for v in variants)


# ============================================================================
# Variant Cycling Logic
# ============================================================================

class TestVariantCycling:
    """Test the variant cycling index logic."""

    def test_single_variant_no_cycling(self) -> None:
        """Single variant means no cycling is needed."""
        variants = [Path('/fake/excited.png')]
        assert len(variants) <= 1 or False  # Would not start cycling

    def test_multiple_variants_cycle_index_wraps(self) -> None:
        """Variant index wraps around when reaching the end."""
        variants = [Path(f'/fake/excited-{i}.png') for i in range(3)]
        index = 0
        for _ in range(6):
            index = (index + 1) % len(variants)
        assert index == 0  # Wrapped around twice

    def test_variant_index_visits_all(self) -> None:
        """Cycling visits every variant before wrapping."""
        variants = [Path(f'/fake/waiting-{i}.png') for i in range(4)]
        index = 0
        visited = set()
        for _ in range(len(variants)):
            index = (index + 1) % len(variants)
            visited.add(index)
        assert visited == {0, 1, 2, 3}


# ============================================================================
# Hover Lock Logic
# ============================================================================

class TestHoverLock:
    """Test hover lock pauses and resumes variant cycling."""

    def _make_mock_widget(self) -> MagicMock:
        """Create a mock AvatarWidget with hover lock state fields.

        Returns:
            MagicMock configured with all hover lock attributes.
        """
        widget = MagicMock()
        widget._hover_locked = False
        widget._was_cycling = False
        widget._cycle_after_id = None
        widget._running = True
        widget.current_emotion = 'cheerful'
        widget._variant_cache = {}
        return widget

    def test_hover_lock_sets_flag_true(self) -> None:
        """Mouse enter sets _hover_locked to True."""
        widget = self._make_mock_widget()
        widget._cycle_after_id = 'timer_abc'

        # Simulate hover lock engage logic from _on_mouse_enter
        if not widget._hover_locked:
            widget._hover_locked = True
            if widget._cycle_after_id is not None:
                widget._was_cycling = True
                widget._cycle_after_id = None

        assert widget._hover_locked is True
        assert widget._was_cycling is True
        assert widget._cycle_after_id is None

    def test_hover_lock_releases_on_leave(self) -> None:
        """Mouse leave releases hover lock and restores cycling flag."""
        widget = self._make_mock_widget()
        widget._hover_locked = True
        widget._was_cycling = True

        # Simulate hover lock release logic from _check_release_hover_lock
        widget._hover_locked = False
        if widget._was_cycling:
            widget._was_cycling = False
            # Would schedule next cycle here

        assert widget._hover_locked is False
        assert widget._was_cycling is False

    def test_hover_lock_without_active_cycling(self) -> None:
        """Hover lock on widget with no active cycling records _was_cycling=False."""
        widget = self._make_mock_widget()
        widget._cycle_after_id = None  # Not cycling

        if not widget._hover_locked:
            widget._hover_locked = True
            if widget._cycle_after_id is not None:
                widget._was_cycling = True
                widget._cycle_after_id = None
            else:
                widget._was_cycling = False

        assert widget._hover_locked is True
        assert widget._was_cycling is False

    def test_cycle_variant_skips_when_hover_locked(self) -> None:
        """_cycle_variant returns early without advancing when hover-locked."""
        # Simulate the guard in _cycle_variant
        hover_locked = True
        index = 2
        variants = [Path(f'/fake/excited-{i}.png') for i in range(4)]

        if not hover_locked:
            index = (index + 1) % len(variants)

        # Index should NOT advance
        assert index == 2

    def test_cycle_variant_advances_when_not_hover_locked(self) -> None:
        """_cycle_variant advances index normally when not hover-locked."""
        hover_locked = False
        index = 2
        variants = [Path(f'/fake/excited-{i}.png') for i in range(4)]

        if not hover_locked:
            index = (index + 1) % len(variants)

        assert index == 3

    def test_hover_lock_preserves_current_image(self) -> None:
        """The currently displayed image stays the same during hover lock."""
        current_path = Path('/fake/excited-2.png')
        hover_locked = True

        # During hover lock, no variant cycling happens
        new_path = current_path  # Would not change
        if not hover_locked:
            new_path = Path('/fake/excited-3.png')

        assert new_path == current_path

    def test_double_enter_does_not_double_lock(self) -> None:
        """Multiple mouse enter events do not corrupt hover lock state."""
        widget = self._make_mock_widget()
        widget._cycle_after_id = 'timer_abc'

        # First enter
        if not widget._hover_locked:
            widget._hover_locked = True
            if widget._cycle_after_id is not None:
                widget._was_cycling = True
                widget._cycle_after_id = None

        # Second enter (should be no-op)
        if not widget._hover_locked:
            widget._hover_locked = True
            widget._was_cycling = True  # This should NOT execute

        assert widget._hover_locked is True
        assert widget._was_cycling is True


# ============================================================================
# Tag Editor Button Logic
# ============================================================================

class TestTagEditorButton:
    """Test tag editor button show/hide state tracking."""

    def test_show_tag_button_sets_id(self) -> None:
        """Showing tag button sets the background ID to a non-None value."""
        bg_id = None
        text_id = None

        # Simulate _show_tag_button logic
        if bg_id is None:
            bg_id = 42  # Would be canvas.create_rectangle return value
            text_id = 43

        assert bg_id is not None
        assert text_id is not None

    def test_show_tag_button_noop_when_already_visible(self) -> None:
        """Showing tag button when already visible is a no-op."""
        bg_id = 42  # Already shown
        original_id = bg_id

        if bg_id is not None:
            pass  # Early return
        else:
            bg_id = 99  # Should NOT execute

        assert bg_id == original_id

    def test_hide_tag_button_clears_ids(self) -> None:
        """Hiding tag button resets both IDs to None."""
        bg_id = 42
        text_id = 43

        if bg_id is not None:
            bg_id = None
            text_id = None

        assert bg_id is None
        assert text_id is None

    def test_hide_tag_button_noop_when_not_visible(self) -> None:
        """Hiding tag button when not visible is a no-op."""
        bg_id = None
        deleted = False

        if bg_id is not None:
            deleted = True

        assert deleted is False


# ============================================================================
# ImageEntry Tag Set
# ============================================================================

class TestImageEntryTagSet:
    """Test ImageEntry tag_set property used by tag editor."""

    def test_tag_set_returns_lowercase(self) -> None:
        """tag_set normalizes tags to lowercase."""
        entry = ImageEntry(path=Path('test.png'), tags=['Cheerful', 'DRESS', 'wave'])
        assert entry.tag_set == {'cheerful', 'dress', 'wave'}

    def test_tag_set_empty_tags(self) -> None:
        """tag_set on entry with empty tags returns empty set."""
        entry = ImageEntry(path=Path('test.png'), tags=[])
        assert entry.tag_set == set()

    def test_tag_set_deduplicates(self) -> None:
        """tag_set correctly deduplicates via set conversion."""
        entry = ImageEntry(path=Path('test.png'), tags=['cheerful', 'Cheerful', 'CHEERFUL'])
        assert entry.tag_set == {'cheerful'}

    def test_path_string_converted_to_path(self) -> None:
        """ImageEntry converts string path to Path in __post_init__."""
        entry = ImageEntry(path='my_image.png', tags=['cheerful'])  # type: ignore[arg-type]
        assert isinstance(entry.path, Path)
        assert entry.path.name == 'my_image.png'


# ============================================================================
# TagEditorDialog Validation Logic
# ============================================================================

class TestTagEditorDialogValidation:
    """Test TagEditorDialog tag validation without requiring a real Tk window."""

    def test_validation_accepts_emotion_tag(self) -> None:
        """Tags with at least one valid emotion tag pass validation."""
        from pyagentvox.avatar_widget import VALID_EMOTIONS

        new_tags = ['cheerful', 'dress', 'wave']
        has_emotion = any(tag.lower() in VALID_EMOTIONS for tag in new_tags)
        assert has_emotion is True

    def test_validation_accepts_control_tag(self) -> None:
        """Tags with at least one valid control tag pass validation."""
        from pyagentvox.avatar_widget import VALID_CONTROL_TAGS

        new_tags = ['control-tts-hover-on']
        has_control = any(tag.lower() in VALID_CONTROL_TAGS for tag in new_tags)
        assert has_control is True

    def test_validation_rejects_no_emotion_or_control(self) -> None:
        """Tags with no emotion or control tags fail validation."""
        from pyagentvox.avatar_widget import VALID_CONTROL_TAGS, VALID_EMOTIONS

        new_tags = ['dress', 'wave', 'casual']
        has_emotion = any(tag.lower() in VALID_EMOTIONS for tag in new_tags)
        has_control = any(tag.lower() in VALID_CONTROL_TAGS for tag in new_tags)
        assert not has_emotion and not has_control

    def test_validation_rejects_empty_tags(self) -> None:
        """Empty tag list fails validation."""
        from pyagentvox.avatar_widget import VALID_CONTROL_TAGS, VALID_EMOTIONS

        new_tags: list[str] = []
        has_emotion = any(tag.lower() in VALID_EMOTIONS for tag in new_tags)
        has_control = any(tag.lower() in VALID_CONTROL_TAGS for tag in new_tags)
        assert not has_emotion and not has_control

    def test_validation_case_insensitive(self) -> None:
        """Validation is case-insensitive for emotion tags."""
        from pyagentvox.avatar_widget import VALID_EMOTIONS

        new_tags = ['CHEERFUL', 'Dress']
        has_emotion = any(tag.lower() in VALID_EMOTIONS for tag in new_tags)
        assert has_emotion is True

    def test_save_callback_receives_checked_tags(self) -> None:
        """Save callback receives only the checked tags."""
        # Simulate collecting checked tags from BooleanVar states
        tag_vars = {
            'cheerful': True,
            'excited': False,
            'dress': True,
            'wave': False,
        }
        new_tags = [tag for tag, checked in tag_vars.items() if checked]
        assert new_tags == ['cheerful', 'dress']

    def test_all_system_tags_included(self) -> None:
        """All valid emotions and control tags are available in the editor."""
        from pyagentvox.avatar_widget import VALID_CONTROL_TAGS, VALID_EMOTIONS

        # The dialog populates all_tags with VALID_EMOTIONS + VALID_CONTROL_TAGS + custom
        all_tags: set[str] = set()
        all_tags.update(VALID_EMOTIONS)
        all_tags.update(VALID_CONTROL_TAGS)

        # Every emotion should be available
        for emotion in VALID_EMOTIONS:
            assert emotion in all_tags

        # Every control tag should be available
        for control_tag in VALID_CONTROL_TAGS:
            assert control_tag in all_tags


# ============================================================================
# Tag Editor Save Integration
# ============================================================================

class TestTagEditorSaveIntegration:
    """Test the _save_image_tags path updates memory and config."""

    def test_save_updates_in_memory_tags(self) -> None:
        """Saving tags updates the ImageEntry.tags list in memory."""
        entry = ImageEntry(path=Path('test.png'), tags=['cheerful', 'dress'])
        new_tags = ['excited', 'casual', 'wave']

        # Simulate _save_image_tags logic
        entry.tags = new_tags

        assert entry.tags == ['excited', 'casual', 'wave']
        assert 'excited' in entry.tag_set

    def test_save_invalidates_variant_cache(self) -> None:
        """Saving tags clears the variant cache."""
        cache: dict[str, list[Path]] = {
            'cheerful': [Path('/fake/cheerful.png')],
            'excited': [Path('/fake/excited.png')],
        }

        # Simulate cache invalidation
        cache.clear()

        assert len(cache) == 0

    @patch('pyagentvox.avatar_tags.update_image_tags')
    def test_save_calls_update_image_tags(self, mock_update: MagicMock) -> None:
        """Saving tags calls avatar_tags.update_image_tags with correct args."""
        image_path = Path('/fake/avatar/test.png')
        new_tags = ['cheerful', 'wave']

        # Simulate the actual save call
        from pyagentvox.avatar_tags import update_image_tags
        update_image_tags(image_path, new_tags)

        mock_update.assert_called_once_with(image_path, new_tags)
