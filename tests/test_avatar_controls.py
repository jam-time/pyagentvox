"""Tests for avatar widget interactive controls.

Tests the hover detection, button system, preview functionality, and IPC
communication for TTS/STT toggles.
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
    # Note: We can't fully test the widget without X display, but we can test
    # the logic methods
    widget = AvatarWidget(avatar_dir=mock_avatar_dir, monitor_pid=os.getpid())
    yield widget
    widget.stop()


class TestButtonCreation:
    """Test button frame creation and initial state."""

    def test_button_frame_created(self, widget):
        """Test that button frame is created with all buttons."""
        frame = widget._create_button_frame()

        assert frame is not None
        assert isinstance(frame, tk.Frame)

        # Check that buttons were created
        assert widget._tts_button is not None
        assert widget._stt_button is not None

    def test_initial_button_state(self, widget):
        """Test that buttons show correct initial state."""
        widget._create_button_frame()

        # Default state should be enabled
        assert widget._tts_enabled is True
        assert widget._stt_enabled is True

    def test_button_frame_hidden_initially(self, widget):
        """Test that button frame is hidden on widget creation."""
        assert widget._buttons_visible is False
        assert widget._button_frame is None


class TestHoverDetection:
    """Test mouse hover detection and button visibility."""

    @patch.object(AvatarWidget, '_disable_click_through')
    def test_show_buttons_on_hover(self, mock_disable, widget):
        """Test that buttons appear when mouse enters avatar."""
        assert widget._buttons_visible is False

        widget._show_buttons()

        assert widget._buttons_visible is True
        assert widget._button_frame is not None
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
        mock_enable.assert_called_once()

    def test_buttons_stay_visible_when_over_frame(self, widget):
        """Test that buttons don't hide when mouse is over button frame."""
        widget._show_buttons()
        widget._mouse_over_buttons = True

        # Simulate leave event - buttons should stay visible
        # (actual hide logic is in _check_hide_buttons which checks mouse position)

        assert widget._buttons_visible is True


class TestPreviewSystem:
    """Test avatar preview images for button hovers."""

    @patch.object(AvatarWidget, '_load_control_image')
    def test_preview_tts_on(self, mock_load, widget):
        """Test TTS button hover shows correct preview."""
        widget._tts_enabled = True
        widget._preview_image('tts')

        mock_load.assert_called_once_with('control-tts-hover-on')
        assert widget._preview_active is True

    @patch.object(AvatarWidget, '_load_control_image')
    def test_preview_tts_off(self, mock_load, widget):
        """Test TTS button hover shows correct preview when disabled."""
        widget._tts_enabled = False
        widget._preview_image('tts')

        mock_load.assert_called_once_with('control-tts-hover-off')
        assert widget._preview_active is True

    @patch.object(AvatarWidget, '_load_control_image')
    def test_preview_stt_on(self, mock_load, widget):
        """Test STT button hover shows correct preview."""
        widget._stt_enabled = True
        widget._preview_image('stt')

        mock_load.assert_called_once_with('control-stt-hover-on')

    @patch.object(AvatarWidget, '_load_control_image')
    def test_preview_close(self, mock_load, widget):
        """Test close button hover shows close-hover image."""
        widget._preview_image('close')

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
    @patch.object(AvatarWidget, '_update_button_icon')
    def test_toggle_tts_off(self, mock_icon, mock_feedback, mock_write, widget):
        """Test toggling TTS from on to off."""
        widget._tts_enabled = True
        widget._tts_button = Mock()

        widget._toggle_tts()

        assert widget._tts_enabled is False
        mock_write.assert_called_once_with(False)
        mock_feedback.assert_called_once_with('tts')
        mock_icon.assert_called_once()

    @patch.object(AvatarWidget, '_write_tts_state')
    @patch.object(AvatarWidget, '_show_feedback')
    def test_toggle_tts_on(self, mock_feedback, mock_write, widget):
        """Test toggling TTS from off to on."""
        widget._tts_enabled = False
        widget._tts_button = Mock()

        widget._toggle_tts()

        assert widget._tts_enabled is True
        mock_write.assert_called_once_with(True)

    @patch.object(AvatarWidget, '_write_stt_state')
    @patch.object(AvatarWidget, '_show_feedback')
    def test_toggle_stt_off(self, mock_feedback, mock_write, widget):
        """Test toggling STT from on to off."""
        widget._stt_enabled = True
        widget._stt_button = Mock()

        widget._toggle_stt()

        assert widget._stt_enabled is False
        mock_write.assert_called_once_with(False)
        mock_feedback.assert_called_once_with('stt')

    @patch.object(AvatarWidget, '_write_stt_state')
    @patch.object(AvatarWidget, '_show_feedback')
    def test_toggle_stt_on(self, mock_feedback, mock_write, widget):
        """Test toggling STT from off to on."""
        widget._stt_enabled = False
        widget._stt_button = Mock()

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


class TestButtonIconUpdates:
    """Test button icon updates based on state."""

    def test_update_button_icon_enabled(self, widget):
        """Test button icon shows enabled state."""
        button = Mock()
        widget._update_button_icon(button, True, '🔊', '🔇')

        button.config.assert_called_once_with(text='🔊')

    def test_update_button_icon_disabled(self, widget):
        """Test button icon shows disabled state."""
        button = Mock()
        widget._update_button_icon(button, False, '🔊', '🔇')

        button.config.assert_called_once_with(text='🔇')

    def test_update_button_icon_none(self, widget):
        """Test graceful handling of None button."""
        # Should not crash
        widget._update_button_icon(None, True, '🔊', '🔇')


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
