"""PyAgentVox main module - unified two-way voice communication for AI agents.

This module provides the core PyAgentVox class that orchestrates speech-to-text
input monitoring, text-to-speech output with multi-emotion support, and automatic
integration with Claude Code via subprocess coordination.

Features:
    - Real-time speech recognition using Google Speech API
    - Multi-voice TTS with emotion tag support ([cheerful], [calm], etc.)
    - Automatic instruction file injection for Claude integration
    - Background subprocess management for voice injector and TTS monitor
    - Async message queueing to prevent TTS interruption

Usage:
    # Programmatic usage
    from pyagentvox import PyAgentVox
    agent = PyAgentVox(config={'neutral': {'voice': 'en-US-MichelleNeural'}})
    await agent.run()

    # CLI usage
    python -m pyagentvox --profile male_voices --debug

Author:
    Jake Meador <jameador13@gmail.com>
"""

import asyncio
import atexit
import contextlib
import hashlib
import logging
import os
import psutil
import re
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import edge_tts
import pygame
from mutagen.mp3 import MP3

try:
    import speech_recognition as sr
except (ImportError, AttributeError) as e:
    # Can't use logger here since it's not defined yet
    print('=' * 60, file=sys.stderr)
    print('FATAL: Speech recognition not available!', file=sys.stderr)
    print('=' * 60, file=sys.stderr)
    print('', file=sys.stderr)
    print('PyAudio is required but not installed.', file=sys.stderr)
    print('On Windows, PyAudio can be tricky to install.', file=sys.stderr)
    print('', file=sys.stderr)
    print('Try one of these:', file=sys.stderr)
    print('  1. pip install pipwin && pipwin install pyaudio', file=sys.stderr)
    print('  2. Download wheel from: https://www.lfd.uci.edu/~gohlke/pythonlibs/', file=sys.stderr)
    print('  3. Install PortAudio first, then: pip install pyaudio', file=sys.stderr)
    print('', file=sys.stderr)
    print(f'Error: {e}', file=sys.stderr)
    print('=' * 60, file=sys.stderr)
    raise SystemExit(1) from e

__author__ = 'Jake Meador <jameador13@gmail.com>'
__all__ = ['PyAgentVox', 'run', 'main']

# Import config and instruction modules (handle both package and script usage)
try:
    from . import config
    from . import instruction
    from .avatar_widget import cleanup_emotion_file, write_emotion_state
except ImportError:
    import config
    import instruction
    from avatar_widget import cleanup_emotion_file, write_emotion_state

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

logger = logging.getLogger('pyagentvox')


def _find_conversation_file() -> Path | None:
    """Find the Claude Code conversation file for per-window locking.

    Returns:
        Path to conversation file, or None if not found
    """
    # Check environment variable first
    if 'CLAUDE_CONVERSATION_FILE' in os.environ:
        conv_file = Path(os.environ['CLAUDE_CONVERSATION_FILE'])
        if conv_file.exists():
            return conv_file

    # Common conversation file locations
    search_paths = []

    # All platforms: ~/.claude/projects/<hash>/*.jsonl
    home = Path.home()
    search_paths.append(home / '.claude' / 'projects')

    # Also check current directory
    search_paths.append(Path.cwd() / '.claude' / 'projects')

    # Find most recent conversation file (exclude subagent files)
    latest_file = None
    latest_time = 0.0

    for search_path in search_paths:
        if not search_path.exists():
            continue

        # Search all subdirectories for .jsonl files, excluding subagents
        for jsonl_file in search_path.rglob('*.jsonl'):
            # Skip subagent files
            if 'subagents' in str(jsonl_file):
                continue

            mtime = jsonl_file.stat().st_mtime
            if mtime > latest_time:
                latest_time = mtime
                latest_file = jsonl_file

    return latest_file


def _get_lock_id() -> str:
    """Get unique lock ID for this Claude Code window.

    Uses conversation file path hash, falls back to 'global'.

    Returns:
        Lock ID string (8-char hash or 'global')
    """
    conv_file = _find_conversation_file()
    if conv_file is None:
        return 'global'

    # Create short hash of conversation file path
    path_hash = hashlib.md5(str(conv_file).encode()).hexdigest()[:8]
    return path_hash


class PyAgentVox:
    """Voice communication system with TTS output and speech recognition input."""

    @staticmethod
    def _get_pid_file_path() -> Path:
        """Get the path to the PID lock file (per-window)."""
        lock_id = _get_lock_id()
        return Path(tempfile.gettempdir()) / f'pyagentvox_{lock_id}.pid'

    def _release_lock(self) -> None:
        """Release the lock file when shutting down."""
        if hasattr(self, 'pid_file') and self.pid_file:
            try:
                self.pid_file.unlink()
                logger.debug(f'Removed PID file: {self.pid_file}')
            except OSError as e:
                logger.debug(f'Could not remove PID file: {e}')

    @staticmethod
    def _check_and_create_lock() -> Path:
        """Check for existing PyAgentVox instance and create lock file.

        Uses PID checking with aggressive cleanup of stale locks.

        Returns:
            Path: pid_file_path

        Raises:
            RuntimeError: If another PyAgentVox instance is already running
        """
        pid_file = PyAgentVox._get_pid_file_path()
        current_pid = os.getpid()
        max_retries = 3

        for attempt in range(max_retries):
            # Check if PID file exists
            if pid_file.exists():
                try:
                    existing_pid = int(pid_file.read_text().strip())

                    # Check if that process is still running
                    if psutil.pid_exists(existing_pid):
                        try:
                            process = psutil.Process(existing_pid)
                            # Check if it's a Python process
                            cmdline = ' '.join(process.cmdline())
                            if 'python' in process.name().lower() and 'pyagentvox' in cmdline.lower():
                                # Process is running and is PyAgentVox
                                raise RuntimeError(
                                    f'PyAgentVox is already running (PID: {existing_pid})\n'
                                    f'To stop it, use: kill {existing_pid} (Linux/Mac) or taskkill /PID {existing_pid} /F (Windows)'
                                )
                            else:
                                # Process exists but isn't PyAgentVox - might be stale
                                logger.warning(f'PID {existing_pid} exists but is not PyAgentVox: {cmdline[:100]}')
                        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                            logger.debug(f'Process {existing_pid} check failed: {e}')

                    # Process not running or not pyagentvox, clean up stale PID file
                    logger.info(f'Removing stale PID file (PID {existing_pid} not running)')
                    try:
                        pid_file.unlink()
                    except OSError as e:
                        logger.warning(f'Could not remove stale PID file: {e}')
                        if attempt < max_retries - 1:
                            time.sleep(0.5)
                            continue
                        raise RuntimeError(f'Cannot remove stale lock file: {pid_file}') from e

                except PermissionError as e:
                    # File is locked - another instance is definitely running
                    logger.debug(f'PID file is locked (another instance running)')
                    raise RuntimeError(
                        f'PyAgentVox is already running (PID file locked)\n'
                        f'Lock file: {pid_file}\n'
                        f'If no instance is running, restart your terminal to clear stale locks.'
                    ) from e
                except (ValueError, OSError) as e:
                    logger.warning(f'Could not read PID file (attempt {attempt + 1}/{max_retries}): {e}')
                    try:
                        pid_file.unlink()
                    except (OSError, PermissionError):
                        if attempt < max_retries - 1:
                            time.sleep(0.5)
                            continue
                        raise RuntimeError(f'Cannot access lock file: {pid_file}') from e

            # Create PID file with current process ID
            try:
                pid_file.write_text(str(current_pid))
                logger.debug(f'Created PID lock file: {pid_file} (PID: {current_pid})')
                return pid_file
            except OSError as e:
                logger.error(f'Could not create PID file (attempt {attempt + 1}/{max_retries}): {e}')
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                raise RuntimeError('Cannot create PID lock file') from e

        raise RuntimeError('Failed to create lock file after multiple attempts')

    def __init__(
        self,
        config_dict: Optional[dict[str, Any]] = None,
        config_path: Optional[str] = None,
        profile_name: Optional[str] = None,
        tts_only: bool = False,
        avatar: bool = True,
    ) -> None:
        """Initialize PyAgentVox with configuration.

        Args:
            config_dict: Optional config dictionary (overrides file-based config)
            config_path: Optional path to config file (JSON or YAML)
            profile_name: Optional profile name (for voice instructions)
            tts_only: If True, only enable TTS output (disable speech recognition)
            avatar: If True, launch the floating avatar widget subprocess

        Raises:
            RuntimeError: If another PyAgentVox instance is already running
        """
        logger.info('Initializing PyAgentVox...')

        # Store profile name and TTS-only mode
        self.profile_name = profile_name
        self.tts_only = tts_only

        # Runtime control flags
        self.tts_enabled = True
        self.stt_enabled = not tts_only

        # Profile hot-swap queue (processes switches in order)
        self.profile_switch_queue: asyncio.Queue[str] = asyncio.Queue()

        # Check for existing instance and create lock file
        self.pid_file = self._check_and_create_lock()
        # Register cleanup to release lock on exit
        atexit.register(self._release_lock)

        if config_dict is not None:
            self.config: dict[str, Any] = config_dict
            self.config_file = None
        else:
            self.config, self.config_file = config.load_config(config_path)

        self.emotion_voices: dict[str, tuple[str, str, str]] = {}
        standard_emotions = ['neutral', 'cheerful', 'excited', 'empathetic', 'warm', 'calm', 'focused']

        for emotion in standard_emotions:
            if emotion in self.config and isinstance(self.config[emotion], dict):
                settings = self.config[emotion]
                voice = settings.get('voice', 'en-US-MichelleNeural')
                speed = settings.get('speed', '+10%')
                pitch = settings.get('pitch', '+10Hz')
                self.emotion_voices[emotion] = (voice, speed, pitch)
                logger.debug(f'Emotion {emotion}: {voice} @ {speed}, {pitch}')

        self.voice = self.emotion_voices.get('neutral', ('en-US-MichelleNeural', '+10%', '+10Hz'))[0]
        self.rate = self.emotion_voices.get('neutral', ('en-US-MichelleNeural', '+10%', '+10Hz'))[1]
        self.pitch = self.emotion_voices.get('neutral', ('en-US-MichelleNeural', '+10%', '+10Hz'))[2]

        logger.debug(f'Default Voice: {self.voice}, Rate: {self.rate}, Pitch: {self.pitch}')

        # Initialize pygame mixer for audio playback
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            logger.debug('Pygame mixer initialized for audio playback')
        except Exception as e:
            logger.error(f'Failed to initialize pygame mixer: {e}')
            raise RuntimeError('Cannot initialize audio playback') from e

        try:
            self.input_file = tempfile.NamedTemporaryFile(
                mode='w+', suffix='.txt', prefix='agent_input_', delete=False, encoding='utf-8'
            )
            self.output_file = tempfile.NamedTemporaryFile(
                mode='w+', suffix='.txt', prefix='agent_output_', delete=False, encoding='utf-8'
            )
        except OSError as e:
            logger.error(f'Failed to create temporary files: {e}')
            raise RuntimeError('Cannot initialize PyAgentVox: temp file creation failed') from e

        logger.info(f'Input file (for TTS): {self.input_file.name}')
        logger.info(f'Output file (from STT): {self.output_file.name}')

        atexit.register(self._cleanup)

        self.running: bool = True
        self._input_position: int = 0
        self.injector_process: Optional[subprocess.Popen] = None
        self.tts_monitor_process: Optional[subprocess.Popen] = None
        self.avatar_process: Optional[subprocess.Popen] = None
        self.tts_queue: Optional[asyncio.Queue] = None  # Created in run()

        # Auto-pause for speech recognition
        self.last_speech_time: float = time.time()
        self.stt_paused: bool = False
        self.stt_idle_timeout: float = 600.0  # 10 minutes in seconds

        # Speech recognition sensitivity
        stt_settings = self.config.get('stt', {})
        self.energy_threshold: int = stt_settings.get('energy_threshold', 4000)

        self._start_voice_injector()
        self._start_tts_monitor()

        if avatar:
            self._start_avatar_widget()

        instructions_path = self.config.get('instructions_path')
        if instructions_path:
            instructions_path = Path(instructions_path)

        success, refresh_message = instruction.inject_voice_instructions(
            instructions_path,
            config=self.config,
            profile_name=self.profile_name
        )
        if success and refresh_message:
            logger.info(f'\n{refresh_message}\n')

        self._print_header()


    def _print_header(self) -> None:
        """Print session header with configuration info."""
        logger.info('\n' + '=' * 60)
        logger.info('PYAGENTVOX - Two-Way Voice Communication')
        logger.info('=' * 60)
        logger.info(f'\nVoice: {self.voice}')
        logger.info(f'Speed: {self.rate} | Pitch: {self.pitch}')
        logger.info('\nInput file (write text for agent to speak):')
        logger.info(f'  {self.input_file.name}')
        logger.info('\nOutput file (your spoken words appear here):')
        logger.info(f'  {self.output_file.name}')
        logger.info('\nRuntime Controls:')
        profile_file = Path(tempfile.gettempdir()) / f'agent_profile_{os.getpid()}.txt'
        control_file = Path(tempfile.gettempdir()) / f'agent_control_{os.getpid()}.txt'
        modify_file = Path(tempfile.gettempdir()) / f'agent_modify_{os.getpid()}.txt'
        logger.info(f'  Profile: echo <profile> > {profile_file}')
        logger.info(f'  TTS/STT: echo tts:on|off > {control_file}')
        logger.info(f'  Modify:  echo pitch=+5 > {modify_file}')
        logger.info(f'  Or use: python -m pyagentvox switch/tts/stt/modify <args>')
        logger.info('\nBackground services:')
        logger.info('  - Voice Injector: Sends your speech to Claude Code')
        logger.info('  - TTS Monitor: Sends Claude responses to voice output')
        logger.info('\nPress Ctrl+C to stop\n')
        logger.info('=' * 60 + '\n')

    def _start_voice_injector(self) -> None:
        """Start voice injector process in background."""
        try:
            if sys.platform != 'win32':
                logger.warning('Voice injector only supported on Windows')
                return

            script_dir = Path(__file__).parent
            injector_script = script_dir / 'injection.py'

            if not injector_script.exists():
                logger.warning(f'Voice injector not found: {injector_script}')
                return

            self.injector_process = subprocess.Popen(
                [sys.executable, str(injector_script), '--output-file', self.output_file.name, '--use-foreground'],
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE
            )

            logger.info(f'Voice injector started (PID: {self.injector_process.pid})')

            time.sleep(0.5)

            if self.injector_process.poll() is not None:
                logger.error('Voice injector failed to start!')
                self.injector_process = None

        except Exception as e:
            logger.warning(f'Failed to start voice injector: {e}')
            logger.info('You can still run it manually: uv run voice_injector.py')

    def _start_tts_monitor(self) -> None:
        """Start TTS monitor process in background."""
        try:
            script_dir = Path(__file__).parent
            monitor_script = script_dir / 'tts.py'

            if not monitor_script.exists():
                logger.warning(f'TTS monitor not found: {monitor_script}')
                return

            logger.info('Starting TTS monitor...')
            self.tts_monitor_process = subprocess.Popen(
                [sys.executable, str(monitor_script), '--input-file', self.input_file.name],
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE
            )

            logger.info(f'TTS monitor started (PID: {self.tts_monitor_process.pid})')

            time.sleep(0.5)

            if self.tts_monitor_process.poll() is not None:
                logger.error('TTS monitor failed to start!')
                self.tts_monitor_process = None
            else:
                logger.debug('TTS monitor running successfully')

        except Exception as e:
            logger.error(f'Failed to start TTS monitor: {e}')
            logger.info('You can still run it manually: uv run python tts_monitor.py')

    def _start_avatar_widget(self) -> None:
        """Start the floating avatar widget as a subprocess.

        Forwards the --debug flag from the parent process so avatar logging
        is visible. Captures stderr for crash diagnostics.
        """
        try:
            script_dir = Path(__file__).parent
            avatar_script = script_dir / 'avatar_widget.py'

            if not avatar_script.exists():
                logger.warning(f'Avatar widget not found: {avatar_script}')
                return

            cmd = [sys.executable, str(avatar_script)]

            # Pass our PID so avatar can monitor our emotion state file
            cmd.extend(['--pid', str(os.getpid())])

            avatar_config = self.config.get('avatar', {})
            avatar_size = avatar_config.get('size')
            if avatar_size:
                cmd.extend(['--size', str(avatar_size)])

            # Forward debug flag so avatar subprocess gets debug-level logging
            if logger.isEnabledFor(logging.DEBUG):
                cmd.append('--debug')

            # Write initial waiting state so avatar starts in idle mode
            write_emotion_state(os.getpid(), 'waiting')

            logger.debug(f'Avatar widget command: {" ".join(cmd)}')

            # Let avatar inherit stderr so its logs are visible in the console.
            # Pipe stdout only (avatar doesn't use it for logging).
            self.avatar_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=None,  # Inherit parent stderr so logging output is visible
            )

            logger.info(f'Avatar widget started (PID: {self.avatar_process.pid})')

            time.sleep(0.5)

            if self.avatar_process.poll() is not None:
                returncode = self.avatar_process.returncode
                logger.warning(f'Avatar widget failed to start (exit code: {returncode})')
                # Try to read any stdout for diagnostics
                if self.avatar_process.stdout:
                    stdout_output = self.avatar_process.stdout.read().decode('utf-8', errors='replace')
                    if stdout_output.strip():
                        logger.warning(f'Avatar stdout: {stdout_output[:500]}')
                self.avatar_process = None

        except Exception as e:
            logger.warning(f'Failed to start avatar widget: {e}')
            logger.debug(f'Avatar start error details:', exc_info=True)

    async def _watch_avatar_process(self) -> None:
        """Monitor the avatar widget subprocess and restart if it dies.

        Polls every 5 seconds. If the process has exited, logs the exit code
        and restarts it automatically up to 3 times.
        """
        max_restarts = 3
        restart_count = 0
        poll_interval = 5.0

        while self.running:
            await asyncio.sleep(poll_interval)

            if self.avatar_process is None:
                continue

            rc = self.avatar_process.poll()
            if rc is not None:
                # Process exited
                logger.warning(f'[AVATAR] Widget process exited (code: {rc})')

                # Read any captured stdout for diagnostics
                if self.avatar_process.stdout:
                    with contextlib.suppress(Exception):
                        stdout_data = self.avatar_process.stdout.read().decode('utf-8', errors='replace')
                        if stdout_data.strip():
                            logger.warning(f'[AVATAR] Widget stdout: {stdout_data[:500]}')

                self.avatar_process = None

                if restart_count < max_restarts:
                    restart_count += 1
                    logger.info(f'[AVATAR] Restarting widget (attempt {restart_count}/{max_restarts})')
                    self._start_avatar_widget()
                else:
                    logger.error(f'[AVATAR] Widget crashed {max_restarts} times, giving up')
                    break

    @staticmethod
    def _clean_text_for_speech(text: str) -> str:
        """Clean text for TTS by removing markdown and formatting.

        Args:
            text: Raw text with possible markdown formatting

        Returns:
            Cleaned text suitable for speech synthesis
        """
        # Remove markdown bold/italic
        text = re.sub(r'\*\*\*(.+?)\*\*\*', r'\1', text)  # ***bold italic***
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)      # **bold**
        text = re.sub(r'\*(.+?)\*', r'\1', text)          # *italic*
        text = re.sub(r'__(.+?)__', r'\1', text)          # __bold__
        text = re.sub(r'_(.+?)_', r'\1', text)            # _italic_

        # Remove markdown links but keep text
        text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)   # [text](url)

        # Remove inline code
        text = re.sub(r'`(.+?)`', r'\1', text)            # `code`

        # Remove backslashes (escape characters)
        text = re.sub(r'\\(.)', r'\1', text)              # \x -> x

        # Remove bullet markers from lists (keeps the content, just removes "- " or "* ")
        # This ensures each list item becomes a separate line without the marker
        text = re.sub(r'^[-*]\s+', '', text, flags=re.MULTILINE)  # Remove bullets at line start
        text = re.sub(r'\n[-*]\s+', '\n', text)  # Remove bullets after newlines

        # Clean up multiple spaces BUT preserve single newlines
        text = re.sub(r'[ \t]+', ' ', text)               # Collapse spaces/tabs only
        text = re.sub(r'\n\n+', '\n', text)               # Multiple newlines → single newline

        return text.strip()

    @staticmethod
    def _ensure_sentence_ending(text: str) -> str:
        """Ensure text ends with proper punctuation for natural TTS pauses.

        Args:
            text: Text that may or may not end with punctuation

        Returns:
            Text ending with punctuation
        """
        text = text.strip()
        if text and text[-1] not in '.!?,;:':
            text += '.'
        return text

    def _parse_segments(self, text: str) -> list[tuple[Optional[str], str]]:
        """Parse text into emotion segments, splitting on newlines for natural pauses.

        Args:
            text: Text with emotion tags

        Returns:
            List of (emotion, text) tuples for each segment

        Examples:
            'Hello!' -> [(None, 'Hello!')]
            '[cheerful] Hello!' -> [('cheerful', 'Hello!')]
            '[cheerful] Line one\\nLine two' -> [('cheerful', 'Line one.'), ('cheerful', 'Line two.')]
            'Hello [cheerful] there [calm] friend!' ->
                [(None, 'Hello'), ('cheerful', 'there'), ('calm', 'friend!')]
        """
        # Split by emotion tags while capturing them
        emotion_pattern = re.compile(r'\[(\w+)\]')
        parts = emotion_pattern.split(text)

        segments = []
        current_emotion = None

        for i, part in enumerate(parts):
            if i % 2 == 0:
                if part.strip():
                    lines = part.split('\n')
                    for line in lines:
                        if line.strip():
                            cleaned_text = self._clean_text_for_speech(line)
                            if cleaned_text:
                                segments.append((current_emotion, cleaned_text))
            else:
                current_emotion = part.lower()

        if not segments:
            cleaned_text = self._clean_text_for_speech(text)
            if cleaned_text:
                segments.append((None, cleaned_text))

        return segments

    async def _generate_tts_file(self, emotion: Optional[str], text: str) -> Optional[str]:
        """Generate TTS audio file for a text segment.

        Args:
            emotion: Emotion tag or None for default
            text: Text to speak

        Returns:
            Path to generated audio file, or None if generation failed
        """
        if not text.strip():
            return None

        if emotion and emotion in self.emotion_voices:
            voice, rate, pitch = self.emotion_voices[emotion]
            logger.debug(f'[TTS] Generating {emotion} -> Voice: {voice}')
        else:
            voice = self.voice
            rate = self.rate
            pitch = self.pitch
            logger.debug(f'[TTS] Generating with default voice: {voice}')

        temp_fd, temp_path = tempfile.mkstemp(suffix='.mp3', prefix='agent_voice_')

        try:
            os.close(temp_fd)
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            await communicate.save(temp_path)
            logger.debug(f'[TTS] Generated: {temp_path}')
            return temp_path
        except Exception as e:
            logger.error(f'TTS generation error: {e}')
            return None

    async def _play_audio_file(self, audio_path: str, text_length: int = 0) -> None:
        """Play an audio file with pygame.

        Args:
            audio_path: Path to MP3 file
            text_length: Length of original text (for fallback timing)
        """
        try:
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()

            # Wait for playback to finish
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)

            logger.debug('[TTS] Playback complete')
        except Exception as e:
            logger.error(f'Pygame playback error: {e}')
            # Fallback: wait estimated duration if playback fails
            if text_length > 0:
                await asyncio.sleep((text_length / 14.0) + 0.5)

    def _cleanup_audio_file(self, audio_path: str) -> None:
        """Delete a temporary audio file.

        Args:
            audio_path: Path to file to delete
        """
        temp_file = Path(audio_path)
        try:
            if temp_file.exists():
                temp_file.unlink()
                logger.debug(f'[TTS] Cleaned up: {audio_path}')
        except PermissionError as e:
            logger.warning(f'Could not delete temp file (still locked): {e}')

    async def _speak_text(self, text: str) -> None:
        """Convert text to speech and play it.

        Supports emotion tags anywhere to switch voices mid-message:
        - [neutral] - Michelle (default, balanced)
        - [cheerful] - Jenny (upbeat, happy)
        - [excited] - Jenny (very enthusiastic)
        - [empathetic] - Emma (warm, caring)
        - [warm] - Emma (understanding)
        - [calm] - Aria (professional US)
        - [focused] - Ava (concentrated US)

        Args:
            text: Text to speak via TTS with optional [emotion] tags.
        """
        logger.debug(f'_speak_text called with: {text[:100]}...')

        if not text.strip():
            logger.warning('Empty text provided, skipping')
            return

        segments = self._parse_segments(text)
        logger.info(f'[TTS] Generating {len(segments)} segment(s) in parallel...')

        # Generate all audio files in parallel for faster playback
        generation_tasks = [
            self._generate_tts_file(emotion, segment_text)
            for emotion, segment_text in segments
        ]
        audio_paths = await asyncio.gather(*generation_tasks)

        # Play all segments sequentially (no generation delays between!)
        logger.info(f'[TTS] Playing {len(segments)} segment(s) sequentially...')
        my_pid = os.getpid()
        for idx, (audio_path, (emotion, segment_text)) in enumerate(zip(audio_paths, segments)):
            if audio_path:
                # Signal avatar widget: emotion starts playing
                avatar_emotion = emotion or 'neutral'
                write_emotion_state(my_pid, avatar_emotion)
                logger.debug(f'[TTS] Playing segment {idx+1}/{len(segments)}')
                await self._play_audio_file(audio_path, len(segment_text))
            else:
                logger.warning(f'[TTS] Skipping segment {idx+1} (generation failed)')

        # Signal avatar widget: all audio finished, return to waiting
        write_emotion_state(my_pid, 'waiting')

        # Cleanup all audio files after playback
        for audio_path in audio_paths:
            if audio_path:
                self._cleanup_audio_file(audio_path)

    async def _process_tts_queue(self) -> None:
        """Process TTS messages from queue sequentially."""
        logger.info('TTS queue processor started')

        while self.running:
            try:
                # Check if profile switch is queued (process all pending switches)
                try:
                    while True:
                        profile_name = self.profile_switch_queue.get_nowait()
                        logger.info(f'[PROFILE] Processing profile switch: {profile_name}')
                        await self._reload_profile(profile_name)
                        self.profile_switch_queue.task_done()
                except asyncio.QueueEmpty:
                    pass  # No more profile switches to process

                try:
                    text = await asyncio.wait_for(self.tts_queue.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    continue

                # Check if TTS is enabled before speaking
                if self.tts_enabled:
                    logger.info(f'[TTS] Speaking: {text[:60]}...')
                    await self._speak_text(text)
                else:
                    logger.debug(f'[TTS] Skipped (TTS disabled): {text[:60]}...')

                self.tts_queue.task_done()

                # Resume STT after TTS activity (if paused and not in TTS-only mode)
                self._resume_stt()

            except Exception as e:
                logger.error(f'Error processing TTS queue: {e}')

    async def _watch_input_file(self) -> None:
        """Watch input file for new text to queue for TTS."""
        last_content = ''
        logger.info('Started watching input file for TTS requests...')
        logger.debug(f'Watching: {self.input_file.name}')

        while self.running:
            try:
                input_path = Path(self.input_file.name)
                if input_path.exists():
                    # Get file size to detect if it's still being written
                    size1 = input_path.stat().st_size
                    await asyncio.sleep(0.05)  # Wait 50ms
                    size2 = input_path.stat().st_size

                    # If size changed, wait a bit more for write to complete
                    if size1 != size2:
                        await asyncio.sleep(0.05)

                    new_content = input_path.read_text(encoding='utf-8').strip()
                else:
                    logger.error(f'Input file was deleted: {input_path}')
                    logger.error('PyAgentVox cannot continue without the input file. Exiting...')
                    self.running = False
                    break
            except Exception as e:
                logger.error(f'Error reading input file: {e}')
                new_content = ''

            if new_content and new_content != last_content:
                logger.debug(f'[TTS] Queuing message: {new_content[:60]}...')
                await self.tts_queue.put(new_content)
                last_content = new_content

            await asyncio.sleep(0.4)  # Reduced from 0.5 since we added delays above

    async def _watch_profile_control(self) -> None:
        """Watch control file for profile hot-swap requests."""
        control_file = Path(tempfile.gettempdir()) / f'agent_profile_{os.getpid()}.txt'
        last_mtime = 0.0

        logger.info('Started watching for profile hot-swap requests...')
        logger.debug(f'Control file: {control_file}')

        while self.running:
            try:
                if control_file.exists():
                    current_mtime = control_file.stat().st_mtime

                    if current_mtime != last_mtime:
                        last_mtime = current_mtime

                        # Wait for write to complete
                        await asyncio.sleep(0.1)

                        # Read profile name
                        profile_name = control_file.read_text(encoding='utf-8').strip()

                        if profile_name:
                            logger.info(f'[PROFILE] Hot-swap request: {profile_name}')

                            # Add to queue (will be processed in order)
                            await self.profile_switch_queue.put(profile_name)
                            logger.debug(f'[PROFILE] Switch queued (position: {self.profile_switch_queue.qsize()})')

                        # Delete control file after processing
                        try:
                            control_file.unlink()
                            logger.debug('[PROFILE] Control file removed')
                        except OSError as e:
                            logger.warning(f'Could not remove control file: {e}')

            except Exception as e:
                logger.error(f'Error watching profile control file: {e}')

            await asyncio.sleep(0.5)

    async def _watch_control_file(self) -> None:
        """Watch control file for TTS/STT on/off commands.

        File format: agent_control_{pid}.txt
        Content: "tts:on", "tts:off", "stt:on", "stt:off"
        """
        control_file = Path(tempfile.gettempdir()) / f'agent_control_{os.getpid()}.txt'
        last_mtime = 0.0

        logger.info('Started watching for TTS/STT control commands...')
        logger.debug(f'Control file: {control_file}')

        while self.running:
            try:
                if control_file.exists():
                    current_mtime = control_file.stat().st_mtime

                    if current_mtime != last_mtime:
                        last_mtime = current_mtime

                        # Wait for write to complete
                        await asyncio.sleep(0.1)

                        # Read command
                        command = control_file.read_text(encoding='utf-8').strip()

                        if command == 'tts:off':
                            self.tts_enabled = False
                            logger.info('[CONTROL] TTS disabled')
                        elif command == 'tts:on':
                            self.tts_enabled = True
                            logger.info('[CONTROL] TTS enabled')
                        elif command == 'stt:off':
                            self.stt_enabled = False
                            logger.info('[CONTROL] STT disabled')
                        elif command == 'stt:on':
                            self.stt_enabled = True
                            logger.info('[CONTROL] STT enabled')
                        else:
                            logger.warning(f'[CONTROL] Unknown command: {command}')

                        # Delete control file after processing
                        try:
                            control_file.unlink()
                            logger.debug('[CONTROL] Control file removed')
                        except OSError as e:
                            logger.warning(f'Could not remove control file: {e}')

            except Exception as e:
                logger.error(f'Error watching control file: {e}')

            await asyncio.sleep(0.5)

    async def _watch_avatar_controls(self) -> None:
        """Watch avatar widget TTS/STT state files for control changes.

        Monitors separate state files written by the avatar widget when users
        toggle TTS/STT via the interactive controls.
        """
        tts_file = Path(tempfile.gettempdir()) / f'pyagentvox_tts_enabled_{os.getpid()}.txt'
        stt_file = Path(tempfile.gettempdir()) / f'pyagentvox_stt_enabled_{os.getpid()}.txt'
        last_tts_state = None
        last_stt_state = None

        logger.debug('Started watching avatar widget control states...')

        while self.running:
            try:
                # Check TTS state file
                if tts_file.exists():
                    tts_state = tts_file.read_text(encoding='utf-8').strip()
                    if tts_state != last_tts_state:
                        last_tts_state = tts_state
                        self.tts_enabled = (tts_state == '1')
                        logger.info(f'[AVATAR] TTS {"enabled" if self.tts_enabled else "disabled"}')

                # Check STT state file
                if stt_file.exists():
                    stt_state = stt_file.read_text(encoding='utf-8').strip()
                    if stt_state != last_stt_state:
                        last_stt_state = stt_state
                        new_stt_enabled = (stt_state == '1')

                        # Only log and update if state actually changed
                        if new_stt_enabled != self.stt_enabled:
                            self.stt_enabled = new_stt_enabled
                            logger.info(f'[AVATAR] STT {"enabled" if self.stt_enabled else "disabled"}')

            except Exception as e:
                logger.error(f'Error watching avatar control states: {e}')

            await asyncio.sleep(0.5)

    async def _watch_modify_file(self) -> None:
        """Watch modify file for runtime voice setting changes.

        File format: agent_modify_{pid}.txt
        Content: "pitch=+5", "neutral.speed=-10", "all.pitch=+3"
        """
        modify_file = Path(tempfile.gettempdir()) / f'agent_modify_{os.getpid()}.txt'
        last_mtime = 0.0

        logger.info('Started watching for voice modification commands...')
        logger.debug(f'Modify file: {modify_file}')

        while self.running:
            try:
                if modify_file.exists():
                    current_mtime = modify_file.stat().st_mtime

                    if current_mtime != last_mtime:
                        last_mtime = current_mtime

                        # Wait for write to complete
                        await asyncio.sleep(0.1)

                        # Read modification command
                        modification = modify_file.read_text(encoding='utf-8').strip()

                        if modification:
                            logger.info(f'[MODIFY] Processing: {modification}')
                            await self._apply_modification(modification)

                        # Delete modify file after processing
                        try:
                            modify_file.unlink()
                            logger.debug('[MODIFY] Modify file removed')
                        except OSError as e:
                            logger.warning(f'Could not remove modify file: {e}')

            except Exception as e:
                logger.error(f'Error watching modify file: {e}')

            await asyncio.sleep(0.5)

    async def _apply_modification(self, modification: str) -> None:
        """Apply runtime voice modification.

        Supports:
        - Global: pitch=+5, speed=-10
        - Emotion-specific: neutral.pitch=+10, cheerful.speed=-5
        - All emotions: all.pitch=+3
        """
        try:
            # Parse modification: "key=value" or "emotion.key=value"
            if '=' not in modification:
                logger.error(f'[MODIFY] Invalid format (missing =): {modification}')
                return

            key, value = modification.split('=', 1)

            if '.' in key:
                # Emotion-specific: neutral.pitch=+10
                emotion, setting = key.split('.', 1)

                if emotion == 'all':
                    # Apply to all emotions
                    emotions = ['neutral', 'cheerful', 'excited', 'empathetic', 'warm', 'calm', 'focused']
                else:
                    emotions = [emotion]

                for emo in emotions:
                    if emo in self.emotion_voices:
                        voice, speed, pitch = self.emotion_voices[emo]

                        if setting == 'pitch':
                            # Parse +5Hz or -10Hz
                            pitch = self._adjust_value(pitch, value)
                        elif setting == 'speed':
                            # Parse +10% or -5%
                            speed = self._adjust_value(speed, value)
                        elif setting == 'voice':
                            # Direct replacement
                            voice = value

                        self.emotion_voices[emo] = (voice, speed, pitch)
                        logger.info(f'[MODIFY] {emo}: {setting}={value}')
                    else:
                        logger.warning(f'[MODIFY] Unknown emotion: {emo}')
            else:
                # Global modification: pitch=+5 (applies to all)
                emotions = ['neutral', 'cheerful', 'excited', 'empathetic', 'warm', 'calm', 'focused']
                setting = key

                for emo in emotions:
                    if emo in self.emotion_voices:
                        voice, speed, pitch = self.emotion_voices[emo]

                        if setting == 'pitch':
                            pitch = self._adjust_value(pitch, value)
                        elif setting == 'speed':
                            speed = self._adjust_value(speed, value)

                        self.emotion_voices[emo] = (voice, speed, pitch)

                logger.info(f'[MODIFY] All emotions: {setting}={value}')

            # Update default voice settings
            if 'neutral' in self.emotion_voices:
                self.voice, self.rate, self.pitch = self.emotion_voices['neutral']

        except Exception as e:
            logger.error(f'[MODIFY] Error applying modification: {e}')
            logger.debug(f'Error details: {traceback.format_exc()}')

    def _adjust_value(self, current: str, modifier: str) -> str:
        """Adjust a value by a modifier.

        Examples:
        - _adjust_value('+20Hz', '+5Hz') → '+25Hz'
        - _adjust_value('+10%', '-5%') → '+5%'
        """
        # Extract number from current value (including negative sign)
        current_match = re.search(r'[+-]?\d+', current)
        if not current_match:
            logger.warning(f'[MODIFY] Could not parse current value: {current}')
            return current

        current_num = int(current_match.group())

        # Extract number and sign from modifier
        modifier_match = re.search(r'([+-]?\d+)', modifier)
        if not modifier_match:
            logger.warning(f'[MODIFY] Could not parse modifier: {modifier}')
            return current

        modifier_num = int(modifier_match.group())

        # Calculate new value
        new_num = current_num + modifier_num

        # Preserve units (Hz or %)
        unit = 'Hz' if 'Hz' in current else '%'
        sign = '+' if new_num >= 0 else ''

        return f'{sign}{new_num}{unit}'

    async def _reload_profile(self, profile_name: str) -> None:
        """Reload configuration with new profile and reinitialize TTS engine.

        Args:
            profile_name: Name of profile to load from config
        """
        try:
            logger.info(f'[PROFILE] Reloading profile: {profile_name}')

            # Load new config with profile
            new_config, _ = config.load_config(
                config_path=str(self.config_file) if self.config_file else None,
                profile=profile_name
            )

            # Update config and profile name
            self.config = new_config
            self.profile_name = profile_name

            # Re-inject voice instructions with new profile
            instructions_path = self.config.get('instructions_path')
            if instructions_path:
                instructions_path = Path(instructions_path)
            instruction.inject_voice_instructions(
                instructions_path,
                config=self.config,
                profile_name=self.profile_name
            )

            # Reinitialize emotion voices with new profile
            self.emotion_voices = {}
            standard_emotions = ['neutral', 'cheerful', 'excited', 'empathetic', 'warm', 'calm', 'focused']

            for emotion in standard_emotions:
                if emotion in self.config and isinstance(self.config[emotion], dict):
                    settings = self.config[emotion]
                    voice = settings.get('voice', 'en-US-MichelleNeural')
                    speed = settings.get('speed', '+10%')
                    pitch = settings.get('pitch', '+10Hz')
                    self.emotion_voices[emotion] = (voice, speed, pitch)

            self.voice = self.emotion_voices.get('neutral', ('en-US-MichelleNeural', '+10%', '+10Hz'))[0]
            self.rate = self.emotion_voices.get('neutral', ('en-US-MichelleNeural', '+10%', '+10Hz'))[1]
            self.pitch = self.emotion_voices.get('neutral', ('en-US-MichelleNeural', '+10%', '+10Hz'))[2]

            # Log voice configuration
            logger.info(f'[PROFILE] ✓ Successfully switched to profile: {profile_name}')
            logger.info(f'[PROFILE] Voice config:')
            for emotion in standard_emotions:
                if emotion in self.emotion_voices:
                    voice, speed, pitch = self.emotion_voices[emotion]
                    logger.info(f'  [{emotion}] {voice} @ {speed}, {pitch}')

        except Exception as e:
            logger.error(f'[PROFILE] Failed to reload profile: {e}')
            logger.error('[PROFILE] Keeping current profile')
            logger.debug(f'Error details: {traceback.format_exc()}')

    def _should_pause_stt(self) -> bool:
        """Check if STT should pause due to inactivity."""
        if self.stt_paused:
            return True

        idle_time = time.time() - self.last_speech_time
        if idle_time > self.stt_idle_timeout:
            self.stt_paused = True
            logger.info('[STT] Auto-paused after 10 minutes of inactivity')
            logger.info('[STT] Will resume when TTS plays a response')
            return True

        return False

    def _resume_stt(self) -> None:
        """Resume STT after TTS activity (if not in TTS-only mode)."""
        if not self.tts_only and self.stt_paused:
            self.stt_paused = False
            self.last_speech_time = time.time()
            logger.info('[STT] Resumed listening after TTS activity')

    def _speech_recognition_loop(self) -> None:
        """Run speech recognition loop with auto-pause on idle."""
        recognizer = sr.Recognizer()
        recognizer.pause_threshold = 3.5
        recognizer.energy_threshold = self.energy_threshold
        recognizer.dynamic_energy_threshold = True
        recognizer.non_speaking_duration = 1.0

        logger.info(f'[STT] Microphone sensitivity: {self.energy_threshold} (lower = more sensitive)')

        self.output_file.write(f"\n{'=' * 60}\n")
        self.output_file.write(f"Voice session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.output_file.write(f"{'=' * 60}\n\n")
        self.output_file.flush()

        logger.info('[STT] Voice recognition ready! (Auto-pauses after 10 min idle)\n')

        while self.running:
            if not self.running:
                break

            # Check if STT is disabled via runtime control
            if not self.stt_enabled:
                time.sleep(1)  # Check again in 1 second
                continue

            # Check if STT should pause due to inactivity
            if self._should_pause_stt():
                time.sleep(1)  # Check again in 1 second
                continue

            try:
                with sr.Microphone() as source:
                    if not self.running:
                        break
                    logger.debug('Listening...')
                    recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    audio = recognizer.listen(source, timeout=None, phrase_time_limit=30)

                try:
                    text = recognizer.recognize_google(audio)
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    log_entry = f'[{timestamp}] {text}\n'
                    logger.info(f'[STT] You: {text}')
                    self.output_file.write(log_entry)
                    self.output_file.flush()

                    # Update last speech time on successful recognition
                    self.last_speech_time = time.time()

                except sr.UnknownValueError:
                    pass
                except sr.RequestError as e:
                    logger.error(f'Google Speech API Error: {e}')
                    time.sleep(1)
            except sr.WaitTimeoutError:
                pass

    def _cleanup(self) -> None:
        """Cleanup temporary files and stop background processes."""
        instruction.remove_voice_instructions()

        # Stop voice injector
        if hasattr(self, 'injector_process') and self.injector_process:
            try:
                self.injector_process.terminate()
                self.injector_process.wait(timeout=2)
                logger.info('Voice injector stopped')
            except Exception as e:
                logger.warning(f'Error stopping voice injector: {e}')

        # Stop TTS monitor
        if hasattr(self, 'tts_monitor_process') and self.tts_monitor_process:
            try:
                self.tts_monitor_process.terminate()
                self.tts_monitor_process.wait(timeout=2)
                logger.info('TTS monitor stopped')
            except Exception as e:
                logger.warning(f'Error stopping TTS monitor: {e}')

        # Stop avatar widget
        if hasattr(self, 'avatar_process') and self.avatar_process:
            try:
                self.avatar_process.terminate()
                self.avatar_process.wait(timeout=2)
                logger.info('Avatar widget stopped')
            except Exception as e:
                logger.warning(f'Error stopping avatar widget: {e}')

        # Cleanup pygame mixer
        try:
            pygame.mixer.quit()
            logger.debug('Pygame mixer shut down')
        except Exception as e:
            logger.warning(f'Error stopping pygame mixer: {e}')

        # Clean up input file (separate try/except)
        if hasattr(self, 'input_file'):
            try:
                path = Path(self.input_file.name)
                self.input_file.close()
                if path.exists():
                    path.unlink()
            except Exception as e:
                logger.warning(f'Error cleaning input file: {e}')

        # Clean up output file (separate try/except)
        if hasattr(self, 'output_file'):
            try:
                path = Path(self.output_file.name)
                self.output_file.close()
                if path.exists():
                    path.unlink()
            except Exception as e:
                logger.warning(f'Error cleaning output file: {e}')

        # Clean up avatar emotion IPC file
        cleanup_emotion_file(os.getpid())

        # Clean up avatar control state files
        tts_state_file = Path(tempfile.gettempdir()) / f'pyagentvox_tts_enabled_{os.getpid()}.txt'
        stt_state_file = Path(tempfile.gettempdir()) / f'pyagentvox_stt_enabled_{os.getpid()}.txt'
        with contextlib.suppress(OSError):
            tts_state_file.unlink(missing_ok=True)
        with contextlib.suppress(OSError):
            stt_state_file.unlink(missing_ok=True)

        # Remove PID lock file
        if hasattr(self, 'pid_file'):
            try:
                if self.pid_file.exists():
                    self.pid_file.unlink()
                    logger.debug('Removed PID lock file')
            except Exception as e:
                logger.warning(f'Error removing PID file: {e}')

    async def run(self) -> None:
        """Run voice input and output concurrently."""
        # Create queue within event loop context
        self.tts_queue = asyncio.Queue()

        # Only start speech recognition if not in TTS-only mode
        if not self.tts_only:
            recognition_thread = threading.Thread(target=self._speech_recognition_loop, daemon=True)
            recognition_thread.start()
        else:
            logger.info('[STT] Speech recognition disabled (TTS-only mode)\n')

        try:
            # Run all watchers and queue processor concurrently
            await asyncio.gather(
                self._watch_input_file(),
                self._watch_profile_control(),
                self._watch_control_file(),      # TTS/STT control (legacy)
                self._watch_avatar_controls(),   # Avatar widget TTS/STT control
                self._watch_modify_file(),       # Voice modifications
                self._watch_avatar_process(),    # Avatar subprocess watchdog
                self._process_tts_queue()
            )
        except KeyboardInterrupt:
            logger.info('\n\nPyAgentVox stopped!')
            self.running = False
            self.output_file.write(f"\nSession ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.output_file.flush()
            self._cleanup()


def run(
    config_dict: Optional[dict[str, Any]] = None,
    config_path: Optional[str] = None,
    profile: Optional[str] = None,
    config_overrides: Optional[dict[str, Any]] = None,
    save_overrides: bool = False,
    debug: bool = False,
    log_file: Optional[str] = None,
    tts_only: bool = False,
    avatar: bool = True,
) -> None:
    """Run PyAgentVox voice system.

    Can be called programmatically or via CLI.

    Args:
        config_dict: Optional config dictionary (highest priority)
        config_path: Optional path to config file
        profile: Optional profile name to load
        config_overrides: Optional dictionary of config overrides
        save_overrides: If True, save CLI overrides back to config file
        debug: Enable debug logging
        log_file: Optional path to log file
        tts_only: If True, only enable TTS output (disable speech recognition)
        avatar: If True, launch the floating avatar widget
    """
    if config_dict is None:
        loaded_config, config_file = config.load_config(
            config_path=config_path,
            profile=profile,
            overrides=config_overrides,
            save_overrides=save_overrides
        )
    else:
        loaded_config = config_dict
        if config_overrides:
            loaded_config = config.merge_dicts(loaded_config, config_overrides)
        config_file = None

    log_level = logging.DEBUG if debug else logging.INFO
    log_format = '%(asctime)s [%(levelname)s] %(message)s'
    log_handlers = [logging.StreamHandler()]

    if log_file:
        log_handlers.append(logging.FileHandler(log_file))

    # Also log to unified voice system log for debugging
    unified_log = Path('C:/projects/unreal/ungambit/.claude/voice-unified.log')
    if unified_log.parent.exists():
        unified_handler = logging.FileHandler(unified_log)
        unified_handler.setFormatter(logging.Formatter('[%(asctime)s.%(msecs)03d] [PY] %(message)s', datefmt='%H:%M:%S'))
        log_handlers.append(unified_handler)

    logging.basicConfig(level=log_level, format=log_format, handlers=log_handlers)

    logger.info('=' * 60)
    logger.info(f'PyAgentVox starting (debug mode: {debug})')
    logger.info('=' * 60)

    agent_vox = None
    try:
        agent_vox = PyAgentVox(config_dict=loaded_config, profile_name=profile, tts_only=tts_only, avatar=avatar)
        asyncio.run(agent_vox.run())
    except KeyboardInterrupt:
        logger.info('\n\nGoodbye!')
        if agent_vox:
            agent_vox._cleanup()
    except Exception as e:
        logger.error(f'Fatal error: {e}')
        traceback.print_exc()
        if agent_vox:
            agent_vox._cleanup()


def main() -> None:
    """CLI entry point - delegates to __main__.main()."""
    from . import __main__
    __main__.main()


if __name__ == '__main__':
    main()
