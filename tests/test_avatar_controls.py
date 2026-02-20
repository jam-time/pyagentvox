"""Tests for avatar widget interactive controls.

Tests the hover detection, canvas-based button system, preview functionality,
and IPC communication for TTS/STT toggles.
"""

import os
import tempfile
import time
import tkinter as tk
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from pyagentvox.avatar_widget import AvatarWidget


@pytest.fixture
def mock_avatar_dir(tmp_path):
    """Create a mock avatar directory with control images."""
    avatar_dir = tmp_path / 'avatar'
    avatar_dir.mkdir()

    # Create controls subdirectory
    controls_dir = avatar_dir / 'controls'
    controls_dir.mkdir()

    # Create mock control images (empty files for testing)
    control_images = [
        'tts-off.png', 'tts-on.png', 'tts-toggled.png',
        'stt-off.png', 'stt-on.png', 'stt-toggled.png',
        'pleading.png', 'crying.png'
    ]
    for img_name in control_images:
        (controls_dir / img_name).write_text('')

    # Create a base emotion image
    (avatar_dir / 'cheerful.png').write_text('')

    return avatar_dir


@pytest.fixture
def widget(mock_avatar_dir):
    """Create an AvatarWidget instance for testing."""
    widget = AvatarWidget(avatar_dir=mock_avatar_dir, monitor_pid=os.getpid())
    yield widget
    widget.stop()


class TestButtonCreation:
    """Test canvas-based button creation and initial state."""

    def test_buttons_created_on_show(self, widget):
        """Test that canvas buttons are created when _show_buttons is called."""
        widget._show_buttons()

        assert widget._buttons_visible is True
        assert 'ctrl_tts' in widget._ctrl_btn_ids
        assert 'ctrl_stt' in widget._ctrl_btn_ids
        assert 'ctrl_close' in widget._ctrl_btn_ids
        assert 'ctrl_tags' in widget._ctrl_btn_ids

    def test_initial_button_state(self, widget):
        """Test that buttons show correct initial state."""
        # Default state should be enabled
        assert widget._tts_enabled is True
        assert widget._stt_enabled is True

    def test_buttons_hidden_initially(self, widget):
        """Test that buttons are hidden on widget creation."""
        assert widget._buttons_visible is False
        assert len(widget._ctrl_btn_ids) == 0

    def test_each_button_has_bg_and_text_ids(self, widget):
        """Test that each canvas button has a background rect and text item."""
        widget._show_buttons()

        for name, (bg_id, text_id) in widget._ctrl_btn_ids.items():
            assert isinstance(bg_id, int), f'{name} bg_id should be int'
            assert isinstance(text_id, int), f'{name} text_id should be int'


class TestHoverDetection:
    """Test mouse hover detection and button visibility."""

    @patch.object(AvatarWidget, '_disable_click_through')
    def test_show_buttons_on_hover(self, mock_disable, widget):
        """Test that buttons appear when mouse enters avatar."""
        assert widget._buttons_visible is False

        widget._show_buttons()

        assert widget._buttons_visible is True
        assert len(widget._ctrl_btn_ids) == 4
        mock_disable.assert_called_once()

    @patch.object(AvatarWidget, '_enable_click_through')
    def test_hide_buttons_on_leave(self, mock_enable, widget):
        """Test that buttons hide when mouse leaves avatar."""
        # First show buttons
        widget._show_buttons()
        assert widget._buttons_visible is True

        # Then hide them
        widget._hide_buttons()

        assert widget._buttons_visible is False
        assert len(widget._ctrl_btn_ids) == 0
        mock_enable.assert_called_once()

    def test_show_buttons_idempotent(self, widget):
        """Test that calling _show_buttons twice doesn't duplicate buttons."""
        widget._show_buttons()
        first_ids = dict(widget._ctrl_btn_ids)

        widget._show_buttons()

        assert widget._ctrl_btn_ids == first_ids

    def test_hide_buttons_idempotent(self, widget):
        """Test that calling _hide_buttons when already hidden is safe."""
        assert widget._buttons_visible is False
        widget._hide_buttons()  # Should not crash
        assert widget._buttons_visible is False


class TestPreviewSystem:
    """Test avatar preview images for button hovers."""

    @patch.object(AvatarWidget, '_display_variant')
    def test_preview_tts_on(self, mock_display, widget):
        """Test TTS button hover shows correct preview via tag-based lookup."""
        widget._tts_enabled = True
        widget._preview_image('tts')

        # Tag-based lookup for 'headphones' should find a match and display it
        if widget._image_registry:
            mock_display.assert_called_once()
        assert widget._preview_active is True

    @patch.object(AvatarWidget, '_display_variant')
    def test_preview_tts_off(self, mock_display, widget):
        """Test TTS button hover shows correct preview when disabled."""
        widget._tts_enabled = False
        widget._preview_image('tts')

        # Tag-based lookup for 'shh' should find a match and display it
        if widget._image_registry:
            mock_display.assert_called_once()
        assert widget._preview_active is True

    @patch.object(AvatarWidget, '_display_variant')
    def test_preview_stt_on(self, mock_display, widget):
        """Test STT button hover shows correct preview."""
        widget._stt_enabled = True
        widget._preview_image('stt')

        # Tag-based lookup for 'listening' should find a match and display it
        if widget._image_registry:
            mock_display.assert_called_once()

    @patch.object(AvatarWidget, '_load_control_image')
    def test_preview_close(self, mock_load, widget):
        """Test close button hover falls through to control tag lookup."""
        widget._preview_image('close')

        # 'close' has no tag in BUTTON_HOVER_TAGS, so it falls through
        mock_load.assert_called_once_with('control-close-hover')

    @patch.object(AvatarWidget, '_switch_emotion')
    def test_restore_emotion_after_preview(self, mock_switch, widget):
        """Test that emotion is restored after preview ends."""
        widget.current_emotion = 'cheerful'
        widget._preview_emotion = 'cheerful'
        widget._preview_active = True

        widget._restore_emotion()

        assert widget._preview_active is False
        assert widget._preview_emotion is None


class TestToggleFunctionality:
    """Test TTS/STT toggle actions."""

    @patch.object(AvatarWidget, '_write_tts_state')
    @patch.object(AvatarWidget, '_show_feedback')
    @patch.object(AvatarWidget, '_update_canvas_button_icon')
    def test_toggle_tts_off(self, mock_icon, mock_feedback, mock_write, widget):
        """Test toggling TTS from on to off."""
        widget._tts_enabled = True

        widget._toggle_tts()

        assert widget._tts_enabled is False
        mock_write.assert_called_once_with(False)
        mock_feedback.assert_called_once_with('tts')
        mock_icon.assert_called_once()

    @patch.object(AvatarWidget, '_write_tts_state')
    @patch.object(AvatarWidget, '_show_feedback')
    @patch.object(AvatarWidget, '_update_canvas_button_icon')
    def test_toggle_tts_on(self, mock_icon, mock_feedback, mock_write, widget):
        """Test toggling TTS from off to on."""
        widget._tts_enabled = False

        widget._toggle_tts()

        assert widget._tts_enabled is True
        mock_write.assert_called_once_with(True)

    @patch.object(AvatarWidget, '_write_stt_state')
    @patch.object(AvatarWidget, '_show_feedback')
    @patch.object(AvatarWidget, '_update_canvas_button_icon')
    def test_toggle_stt_off(self, mock_icon, mock_feedback, mock_write, widget):
        """Test toggling STT from on to off."""
        widget._stt_enabled = True

        widget._toggle_stt()

        assert widget._stt_enabled is False
        mock_write.assert_called_once_with(False)
        mock_feedback.assert_called_once_with('stt')

    @patch.object(AvatarWidget, '_write_stt_state')
    @patch.object(AvatarWidget, '_show_feedback')
    @patch.object(AvatarWidget, '_update_canvas_button_icon')
    def test_toggle_stt_on(self, mock_icon, mock_feedback, mock_write, widget):
        """Test toggling STT from off to on."""
        widget._stt_enabled = False

        widget._toggle_stt()

        assert widget._stt_enabled is True
        mock_write.assert_called_once_with(True)


class TestIPCStateFiles:
    """Test IPC file creation and content."""

    def test_write_tts_state_enabled(self, widget):
        """Test writing TTS enabled state to file."""
        widget._write_tts_state(True)

        state_file = Path(tempfile.gettempdir()) / f'pyagentvox_tts_enabled_{widget.monitor_pid}.txt'
        assert state_file.exists()
        assert state_file.read_text() == '1'

        # Cleanup
        state_file.unlink()

    def test_write_tts_state_disabled(self, widget):
        """Test writing TTS disabled state to file."""
        widget._write_tts_state(False)

        state_file = Path(tempfile.gettempdir()) / f'pyagentvox_tts_enabled_{widget.monitor_pid}.txt'
        assert state_file.exists()
        assert state_file.read_text() == '0'

        # Cleanup
        state_file.unlink()

    def test_write_stt_state_enabled(self, widget):
        """Test writing STT enabled state to file."""
        widget._write_stt_state(True)

        state_file = Path(tempfile.gettempdir()) / f'pyagentvox_stt_enabled_{widget.monitor_pid}.txt'
        assert state_file.exists()
        assert state_file.read_text() == '1'

        # Cleanup
        state_file.unlink()

    def test_write_stt_state_disabled(self, widget):
        """Test writing STT disabled state to file."""
        widget._write_stt_state(False)

        state_file = Path(tempfile.gettempdir()) / f'pyagentvox_stt_enabled_{widget.monitor_pid}.txt'
        assert state_file.exists()
        assert state_file.read_text() == '0'

        # Cleanup
        state_file.unlink()

    def test_state_files_cleaned_on_stop(self, widget):
        """Test that state files are removed when widget stops."""
        # Write state files
        widget._write_tts_state(True)
        widget._write_stt_state(True)

        tts_file = Path(tempfile.gettempdir()) / f'pyagentvox_tts_enabled_{widget.monitor_pid}.txt'
        stt_file = Path(tempfile.gettempdir()) / f'pyagentvox_stt_enabled_{widget.monitor_pid}.txt'

        assert tts_file.exists()
        assert stt_file.exists()

        # Stop widget
        widget.stop()

        # Files should be cleaned up
        assert not tts_file.exists()
        assert not stt_file.exists()


class TestControlImageLoading:
    """Test loading control images from subdirectory."""

    @patch.object(AvatarWidget, '_display_variant')
    def test_load_control_image_found(self, mock_display, widget, mock_avatar_dir):
        """Test loading control image when it exists."""
        widget._load_control_image('tts-off')

        # Should have called display with the control image path
        mock_display.assert_called_once()
        call_args = mock_display.call_args[0]
        assert 'tts-off.png' in str(call_args[0])

    @patch.object(AvatarWidget, '_display_variant')
    def test_load_control_image_not_found(self, mock_display, widget, mock_avatar_dir):
        """Test loading control image when it doesn't exist."""
        widget._load_control_image('nonexistent')

        # Should not have called display
        mock_display.assert_not_called()

    def test_load_control_image_no_controls_dir(self, widget, tmp_path):
        """Test graceful handling when controls directory doesn't exist."""
        widget.avatar_dir = tmp_path  # Directory without controls subdirectory

        # Should not crash
        widget._load_control_image('tts-off')


class TestCloseAnimation:
    """Test avatar close animation."""

    @patch.object(AvatarWidget, '_load_control_image')
    @patch.object(AvatarWidget, 'stop')
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_close_with_animation(self, mock_sleep, mock_stop, mock_load, widget):
        """Test that close animation shows crying image and calls stop."""
        # Mock the root window geometry update
        widget._root.geometry = Mock()
        widget._root.update = Mock()
        widget._root.winfo_x = Mock(return_value=100)
        widget._root.winfo_y = Mock(return_value=100)

        widget._close_with_animation()

        # Should load close animation image
        mock_load.assert_called_once_with('control-close-animation')

        # Should call stop
        mock_stop.assert_called_once()

        # Should have called geometry to move window
        assert widget._root.geometry.call_count > 0


class TestCanvasButtonIconUpdates:
    """Test canvas button icon updates based on state."""

    def test_update_canvas_button_icon_enabled(self, widget):
        """Test canvas button text shows enabled state."""
        widget._show_buttons()
        widget._update_canvas_button_icon('ctrl_tts', True, '\U0001f50a', '\U0001f507')

        _, text_id = widget._ctrl_btn_ids['ctrl_tts']
        actual_text = widget._canvas.itemcget(text_id, 'text')
        assert actual_text == '\U0001f50a'

    def test_update_canvas_button_icon_disabled(self, widget):
        """Test canvas button text shows disabled state."""
        widget._show_buttons()
        widget._update_canvas_button_icon('ctrl_tts', False, '\U0001f50a', '\U0001f507')

        _, text_id = widget._ctrl_btn_ids['ctrl_tts']
        actual_text = widget._canvas.itemcget(text_id, 'text')
        assert actual_text == '\U0001f507'

    def test_update_canvas_button_icon_missing_tag(self, widget):
        """Test graceful handling of missing button tag."""
        # Should not crash when tag doesn't exist
        widget._update_canvas_button_icon('nonexistent', True, '\U0001f50a', '\U0001f507')


class TestCanvasButtonHoverEffects:
    """Test canvas button hover highlight and restore effects."""

    def test_hover_enter_highlights_button(self, widget):
        """Test that hovering a button changes its fill color."""
        widget._show_buttons()
        bg_id, text_id = widget._ctrl_btn_ids['ctrl_tts']

        widget._on_ctrl_btn_enter('ctrl_tts')

        # TTS starts enabled (active), so hover color is bright green
        assert widget._canvas.itemcget(bg_id, 'fill') == '#3a8a52'
        assert widget._canvas.itemcget(text_id, 'fill') == '#ffffff'

    def test_hover_leave_restores_button(self, widget):
        """Test that leaving a button restores its fill color."""
        widget._show_buttons()
        bg_id, text_id = widget._ctrl_btn_ids['ctrl_tts']

        # Enter then leave
        widget._on_ctrl_btn_enter('ctrl_tts')
        widget._on_ctrl_btn_leave('ctrl_tts')

        # TTS starts enabled (active), so base color is muted green
        assert widget._canvas.itemcget(bg_id, 'fill') == '#2d6b3f'
        assert widget._canvas.itemcget(text_id, 'fill') == '#cccccc'

    def test_hover_enter_nonexistent_tag_no_crash(self, widget):
        """Test that hovering a nonexistent tag doesn't crash."""
        widget._on_ctrl_btn_enter('nonexistent')
        widget._on_ctrl_btn_leave('nonexistent')

    @patch.object(AvatarWidget, '_display_variant')
    def test_hover_tts_triggers_preview(self, mock_display, widget):
        """Test that hovering TTS button triggers preview image via tag lookup."""
        widget._show_buttons()
        widget._on_ctrl_btn_enter('ctrl_tts')

        # Tag-based lookup for 'headphones' should find a match and display it
        if widget._image_registry:
            mock_display.assert_called_once()

    @patch.object(AvatarWidget, '_load_control_image')
    def test_hover_tags_does_not_trigger_preview(self, mock_load, widget):
        """Test that hovering Tags button does NOT trigger preview image."""
        widget._show_buttons()
        widget._on_ctrl_btn_enter('ctrl_tags')

        mock_load.assert_not_called()


class TestFeedbackDisplay:
    """Test confirmation feedback display."""

    @patch.object(AvatarWidget, '_load_control_image')
    @patch.object(AvatarWidget, '_restore_emotion')
    def test_show_feedback(self, mock_restore, mock_load, widget):
        """Test that feedback image is shown and emotion restored after delay."""
        # Mock the after method to immediately call the callback
        def mock_after(delay, callback):
            callback()
            return 'after_id'

        widget._root.after = mock_after

        widget._show_feedback('tts')

        mock_load.assert_called_once_with('control-tts-clicked')
        mock_restore.assert_called_once()
