"""Tests for voice injection module (background keyboard input).

These tests verify that the voice injector can send keystrokes to a
target window WITHOUT stealing focus, using Windows messaging API.
"""
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, call
import pytest


class TestVoiceInjector:
    """Test VoiceInjector class for background keyboard input."""

    @pytest.fixture
    def temp_output_file(self):
        """Create a temporary output file for testing."""
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', prefix='test_output_', delete=False) as f:
            f.write('[12:00:00] test message\n')
            f.flush()
            yield Path(f.name)
        # Cleanup
        Path(f.name).unlink(missing_ok=True)

    @pytest.fixture
    def mock_win32(self):
        """Mock win32 modules for testing."""
        # Patch the actual module methods directly
        with patch('pyagentvox.injection.win32gui') as mock_win32gui, \
             patch('pyagentvox.injection.win32api') as mock_win32api, \
             patch('pyagentvox.injection.win32con') as mock_win32con:

            # Setup mock window handle
            mock_win32gui.GetForegroundWindow.return_value = 12345
            mock_win32gui.GetWindowText.return_value = 'Test Window'
            mock_win32gui.IsWindowVisible.return_value = True

            # Setup win32con constants
            mock_win32con.WM_CHAR = 0x0102
            mock_win32con.WM_KEYDOWN = 0x0100
            mock_win32con.WM_KEYUP = 0x0101
            mock_win32con.VK_RETURN = 0x0D

            yield {
                'win32gui': mock_win32gui,
                'win32api': mock_win32api,
                'win32con': mock_win32con
            }

    def test_send_text_without_focus_stealing(self, temp_output_file, mock_win32):
        """Test that text is sent WITHOUT calling SetForegroundWindow."""
        from pyagentvox.injection import VoiceInjector

        injector = VoiceInjector(temp_output_file, use_foreground=True)
        injector.hwnd = 12345  # Mock window handle

        # Send test text
        result = injector.send_text_to_window('hello')

        # Verify success
        assert result is True

        # CRITICAL: Verify SetForegroundWindow was NOT called
        mock_win32['win32gui'].SetForegroundWindow.assert_not_called()

        # Verify PostMessage was called for each character
        win32api = mock_win32['win32api']
        win32con = mock_win32['win32con']

        # Should have 5 character calls + 4 key calls (2 Enter keys with DOWN/UP each)
        assert win32api.PostMessage.call_count >= 5  # At least the characters

        # Verify character messages
        char_calls = [
            call(12345, win32con.WM_CHAR, ord('h'), 0),
            call(12345, win32con.WM_CHAR, ord('e'), 0),
            call(12345, win32con.WM_CHAR, ord('l'), 0),
            call(12345, win32con.WM_CHAR, ord('l'), 0),
            call(12345, win32con.WM_CHAR, ord('o'), 0),
        ]

        for expected_call in char_calls:
            assert expected_call in win32api.PostMessage.call_args_list

    def test_send_text_includes_enter_key(self, temp_output_file, mock_win32):
        """Test that Enter key is sent after text."""
        from pyagentvox.injection import VoiceInjector

        injector = VoiceInjector(temp_output_file, use_foreground=True)
        injector.hwnd = 12345

        result = injector.send_text_to_window('test')
        assert result is True

        win32api = mock_win32['win32api']
        win32con = mock_win32['win32con']

        # Verify Enter key DOWN and UP messages (2 Enter presses for stability)
        enter_calls = [
            call(12345, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0),
            call(12345, win32con.WM_KEYUP, win32con.VK_RETURN, 0),
        ]

        for expected_call in enter_calls:
            assert expected_call in win32api.PostMessage.call_args_list

    def test_extract_speech_text_from_timestamped_format(self, temp_output_file):
        """Test extraction of speech text from timestamped output file format."""
        from pyagentvox.injection import VoiceInjector

        content = """
[12:00:00] hello world
[12:00:05] how are you
===================
[12:00:10] testing
"""
        result = VoiceInjector.extract_speech_text(content)
        assert result == 'hello world how are you testing'

    def test_window_handle_persistence(self, temp_output_file, mock_win32):
        """Test that window handle is captured once and reused."""
        from pyagentvox.injection import VoiceInjector

        injector = VoiceInjector(temp_output_file, use_foreground=True)

        # Window handle should be captured during init
        assert injector.hwnd == 12345
        assert mock_win32['win32gui'].GetForegroundWindow.call_count == 1

        # Send multiple messages
        injector.send_text_to_window('test1')
        injector.send_text_to_window('test2')

        # Window handle should NOT be queried again
        assert mock_win32['win32gui'].GetForegroundWindow.call_count == 1

    @patch('time.time')
    def test_background_typing_simulation(self, mock_time, temp_output_file, mock_win32):
        """Integration test: Simulate background typing scenario.

        Scenario:
        1. VoiceInjector captures Claude Code window handle
        2. User switches to browser (different window)
        3. User speaks
        4. Text is typed into Claude Code WITHOUT switching focus
        """
        from pyagentvox.injection import VoiceInjector

        # Setup timeline
        mock_time.side_effect = [0, 0.1, 0.2, 0.3]  # Timestamps for delays

        # Step 1: Initialize with Claude Code focused
        claude_window_handle = 12345
        mock_win32['win32gui'].GetForegroundWindow.return_value = claude_window_handle

        injector = VoiceInjector(temp_output_file, use_foreground=True)
        assert injector.hwnd == claude_window_handle

        # Step 2: User switches to browser (simulate different foreground window)
        browser_window_handle = 67890
        mock_win32['win32gui'].GetForegroundWindow.return_value = browser_window_handle

        # Step 3: User speaks and text is injected
        result = injector.send_text_to_window('Hello Claude')

        # Verify success
        assert result is True

        # Step 4: CRITICAL - Verify focus was NOT changed
        # SetForegroundWindow should NEVER be called
        mock_win32['win32gui'].SetForegroundWindow.assert_not_called()

        # Verify text was sent to ORIGINAL window (Claude Code), not current foreground
        win32api = mock_win32['win32api']

        # All PostMessage calls should target the Claude Code window
        for call_args in win32api.PostMessage.call_args_list:
            hwnd = call_args[0][0]  # First positional arg
            assert hwnd == claude_window_handle, \
                f"Message sent to wrong window! Expected {claude_window_handle}, got {hwnd}"

    def test_empty_text_handling(self, temp_output_file, mock_win32):
        """Test that empty text is handled gracefully."""
        from pyagentvox.injection import VoiceInjector

        injector = VoiceInjector(temp_output_file, use_foreground=True)
        injector.hwnd = 12345

        # Empty strings should still succeed (just sends Enter)
        result = injector.send_text_to_window('')
        assert result is True

        # Should still send Enter key
        win32con = mock_win32['win32con']
        assert any(
            call_args[0][1] == win32con.WM_KEYDOWN
            for call_args in mock_win32['win32api'].PostMessage.call_args_list
        )

    def test_special_characters_handling(self, temp_output_file, mock_win32):
        """Test handling of special characters in text."""
        from pyagentvox.injection import VoiceInjector

        injector = VoiceInjector(temp_output_file, use_foreground=True)
        injector.hwnd = 12345

        # Test with special characters
        special_text = 'Hello, World! @#$%'
        result = injector.send_text_to_window(special_text)

        assert result is True

        # Verify each character is sent
        win32api = mock_win32['win32api']
        win32con = mock_win32['win32con']

        for char in special_text:
            expected_call = call(12345, win32con.WM_CHAR, ord(char), 0)
            assert expected_call in win32api.PostMessage.call_args_list
