"""Voice input injector for Claude Code.

This module monitors PyAgentVox STT output and automatically types transcribed
speech into the Claude Code window using Windows messaging API. Runs as a
separate subprocess launched by PyAgentVox main process.

Features:
    - Auto-detects PyAgentVox output file
    - Background keyboard input using PostMessage (no focus stealing)
    - Works while you're focused on other windows
    - "Stop listening" voice command support

Usage:
    # Auto-detect and use foreground window (captures target on startup)
    python -m pyagentvox.voice_injector --use-foreground

    # Specify output file and window title
    python -m pyagentvox.voice_injector --output-file /tmp/agent_output_12345.txt --window-title "Claude Code"

Platform:
    Windows only (uses win32gui, win32api, win32con)

Author:
    Jake Meador <jameador13@gmail.com>
"""

import contextlib
import logging
import os
import signal
import sys
import time
import traceback
from pathlib import Path
from typing import Optional

__author__ = 'Jake Meador <jameador13@gmail.com>'
__all__ = ['VoiceInjector', 'main']

logger = logging.getLogger('pyagentvox.voice_injector')

if sys.platform == 'win32':
    import win32gui
    import win32api
    import win32con
else:
    logger.error(f'Platform {sys.platform} not yet supported. Windows only for now.')
    sys.exit(1)


class VoiceInjector:
    """Monitors voice output and injects into Claude Code."""

    def __init__(self, output_file: Path, window_title: Optional[str] = None, use_foreground: bool = False):
        """Initialize voice injector.

        Args:
            output_file: Path to PyAgentVox output file to monitor
            window_title: Title of Claude Code window (default: None = auto-detect foreground)
            use_foreground: If True, use currently focused window as target
        """
        self.output_file = Path(output_file)
        self.window_title = window_title
        self.use_foreground = use_foreground
        self.last_position = 0
        self.last_content = ''
        self.hwnd: Optional[int] = None
        self.parent_pid = os.getppid()

        if not self.output_file.exists():
            raise FileNotFoundError(f'Output file not found: {output_file}')

        self.last_position = self.output_file.stat().st_size

        logger.info('[MIC] Voice Injector initialized')
        logger.info(f'   Monitoring: {self.output_file}')

        if use_foreground or window_title is None:
            self.hwnd = win32gui.GetForegroundWindow()
            target_title = win32gui.GetWindowText(self.hwnd)
            logger.info(f'   Target: Foreground window - \'{target_title}\'')
        else:
            logger.info(f'   Target: Window matching \'{self.window_title}\'')

    def find_window(self) -> Optional[int]:
        """Find Claude Code window handle."""
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if self.window_title.lower() in title.lower():
                    windows.append(hwnd)

        windows = []
        win32gui.EnumWindows(callback, windows)

        if windows:
            self.hwnd = windows[0]
            return self.hwnd

        return None

    def send_text_to_window(self, text: str) -> bool:
        """Send text to Claude Code window without stealing focus.

        Uses Windows messaging API (PostMessage) to send keystrokes directly to
        the window without requiring it to be in focus. This allows you to continue
        working in other windows while voice input is typed into Claude Code.

        Args:
            text: Text to send

        Returns:
            True if successful, False otherwise
        """
        if not self.hwnd:
            self.hwnd = self.find_window()
            if not self.hwnd:
                logger.warning('Claude Code window not found!')
                return False

        try:
            # Send each character as WM_CHAR message directly to the window
            for char in text:
                win32api.PostMessage(self.hwnd, win32con.WM_CHAR, ord(char), 0)
                time.sleep(0.01)  # Small delay for reliability

            time.sleep(0.05)

            # Send Enter key using WM_KEYDOWN/WM_KEYUP
            win32api.PostMessage(self.hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
            time.sleep(0.05)
            win32api.PostMessage(self.hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)

            # Send second Enter for stability (sometimes first doesn't register)
            time.sleep(0.05)
            win32api.PostMessage(self.hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
            time.sleep(0.05)
            win32api.PostMessage(self.hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)

            return True
        except Exception as e:
            logger.error(f'Error sending text to window: {e}')
            logger.debug(traceback.format_exc())
            return False

    @staticmethod
    def extract_speech_text(content: str) -> str:
        """Extract speech text from timestamped format.

        Args:
            content: Raw file content with timestamps

        Returns:
            Extracted speech text
        """
        lines = content.strip().split('\n')
        texts = []

        for line in lines:
            if '===' in line or 'Voice session started' in line:
                continue

            if ']' in line and line.strip().startswith('['):
                text = line.split(']', 1)[1].strip()
                if text:
                    texts.append(text)

        return ' '.join(texts)

    def check_for_new_speech(self) -> Optional[str]:
        """Check for new speech in output file.

        Returns:
            New speech text if found, None otherwise
        """
        try:
            # Check if file still exists
            if not self.output_file.exists():
                logger.error(f'Output file was deleted: {self.output_file}')
                logger.error('Voice injector cannot continue without the output file.')
                return 'EXIT'  # Special signal to stop

            current_size = self.output_file.stat().st_size
            if current_size <= self.last_position:
                return None

            with open(self.output_file, 'r', encoding='utf-8') as f:
                f.seek(self.last_position)
                new_content = f.read()
                self.last_position = f.tell()

            if not new_content.strip():
                return None

            speech_text = self.extract_speech_text(new_content)
            if not speech_text or speech_text == self.last_content:
                return None

            self.last_content = speech_text
            return speech_text

        except Exception as e:
            logger.error(f'Error checking for speech: {e}')
            logger.debug(traceback.format_exc())
            return None

    def run(self, poll_interval: float = 0.5):
        """Run the voice injector loop.

        Args:
            poll_interval: How often to check for new speech (seconds)
        """
        logger.info('\n[MIC] Voice Injector running!')
        logger.info(f'   Poll interval: {poll_interval}s')
        logger.info('   Say \'stop listening\' to stop PyAgentVox')
        logger.info('   Press Ctrl+C to stop\n')

        with contextlib.suppress(KeyboardInterrupt):
            while True:
                speech_text = self.check_for_new_speech()

                if not speech_text:
                    time.sleep(poll_interval)
                    continue

                # Check for file deletion signal
                if speech_text == 'EXIT':
                    logger.info('\n[EXIT] Output file deleted. Stopping...')
                    return

                logger.info(f'[MIC] Heard: {speech_text}')

                if speech_text.lower().strip() == 'stop listening':
                    logger.info('\n[STOP] Stop command detected!')
                    logger.info(f'   Terminating PyAgentVox (PID: {self.parent_pid})...')

                    try:
                        os.kill(self.parent_pid, signal.SIGTERM)
                        logger.info('   PyAgentVox stopped successfully!')
                    except Exception as e:
                        logger.warning(f'   Could not stop PyAgentVox: {e}')

                    logger.info('\n[BYE] Voice Injector stopped!')
                    return

                if self.send_text_to_window(speech_text):
                    logger.info('OK Sent to Claude Code')
                else:
                    logger.warning('Failed to send')

                time.sleep(poll_interval)

        logger.info('\n\n[BYE] Voice Injector stopped!')


def main():
    """Entry point for voice injector."""
    import argparse
    import glob
    import tempfile

    parser = argparse.ArgumentParser(description='Voice input injector for Claude Code')
    parser.add_argument('--output-file', type=str, help='PyAgentVox output file path (auto-detects if not provided)')
    parser.add_argument('--window-title', type=str, default=None, help='Claude Code window title (default: auto-detect foreground window)')
    parser.add_argument('--use-foreground', action='store_true', help='Use currently focused window as target (ignores --window-title)')
    parser.add_argument('--interval', type=float, default=0.5, help='Poll interval in seconds (default: 0.5)')
    parser.add_argument('--startup-delay', type=int, default=0, help='Seconds to wait before capturing foreground window (default: 0)')

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(message)s')

    # Get output file
    if not args.output_file:
        pattern = str(Path(tempfile.gettempdir()) / 'agent_output_*.txt')
        files = sorted(glob.glob(pattern), key=lambda x: Path(x).stat().st_mtime, reverse=True)

        if not files:
            logger.error('No PyAgentVox output files found!')
            logger.error('   Make sure PyAgentVox is running first.')
            sys.exit(1)

        output_file = Path(files[0])
        logger.info(f'[FILE] Auto-detected: {output_file}')
    else:
        output_file = Path(args.output_file)

    # Startup delay countdown
    if args.startup_delay > 0 and (args.use_foreground or args.window_title is None):
        logger.info('\n[COUNTDOWN] Focus your target window NOW!')
        for i in range(args.startup_delay, 0, -1):
            logger.info(f'  {i}...')
            time.sleep(1)
        logger.info('  Capturing foreground window!\n')

    try:
        injector = VoiceInjector(output_file, args.window_title, args.use_foreground)
        injector.run(args.interval)
    except FileNotFoundError as e:
        logger.error(f'{e}')
        sys.exit(1)
    except Exception as e:
        logger.error(f'Error: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
