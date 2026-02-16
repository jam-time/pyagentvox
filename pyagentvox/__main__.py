"""CLI entry point for PyAgentVox voice system.

This module provides subcommand-based CLI for controlling PyAgentVox.

Usage:
    python -m pyagentvox start [options]    # Start PyAgentVox
    python -m pyagentvox stop               # Stop running instance
    python -m pyagentvox switch <profile>   # Switch voice profile
    python -m pyagentvox tts on|off         # Control TTS
    python -m pyagentvox stt on|off         # Control STT
    python -m pyagentvox modify <key>=<val> # Modify voice settings
    python -m pyagentvox status             # Show status

Author:
    Jake Meador <jameador13@gmail.com>
"""

import argparse
import hashlib
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from . import config
from .pyagentvox import run

try:
    import psutil
except ImportError:
    psutil = None

__author__ = 'Jake Meador <jameador13@gmail.com>'
__all__ = ['main']

logger = logging.getLogger('pyagentvox')


def find_conversation_file() -> Path | None:
    """Find the Claude Code conversation JSONL file for this window.

    Returns:
        Path to conversation file, or None if not found
    """
    # Check for CLAUDE_CONVERSATION_FILE env var (can be set by skills)
    if 'CLAUDE_CONVERSATION_FILE' in os.environ:
        conv_file = Path(os.environ['CLAUDE_CONVERSATION_FILE'])
        if conv_file.exists():
            return conv_file

    # Look for conversation files in common locations
    possible_dirs = [
        Path.home() / '.claude' / 'projects',
        Path.home() / 'AppData' / 'Roaming' / 'Claude' / 'conversations',
        Path.home() / 'Library' / 'Application Support' / 'Claude' / 'conversations',
    ]

    # Find the most recently modified conversation file
    latest_file = None
    latest_time = 0

    for directory in possible_dirs:
        if not directory.exists():
            continue

        for jsonl_file in directory.rglob('*.jsonl'):
            mtime = jsonl_file.stat().st_mtime
            if mtime > latest_time:
                latest_time = mtime
                latest_file = jsonl_file

    return latest_file


def get_lock_id() -> str:
    """Get unique lock ID for this Claude Code window.

    Uses conversation file path to create per-window lock.
    Falls back to global lock if conversation file not found.

    Returns:
        Lock ID string (8-char hash or 'global')
    """
    conv_file = find_conversation_file()
    if conv_file:
        # Create hash of conversation file path for unique lock per window
        path_hash = hashlib.md5(str(conv_file).encode()).hexdigest()[:8]
        return path_hash
    return 'global'


def get_pid_file() -> Path:
    """Get PID file path for this window."""
    lock_id = get_lock_id()
    return Path(tempfile.gettempdir()) / f'pyagentvox_{lock_id}.pid'


def get_running_pid() -> int | None:
    """Get PID of running PyAgentVox instance for this window.

    Returns:
        PID if running, None otherwise
    """
    if psutil is None:
        return None

    pid_file = get_pid_file()
    if not pid_file.exists():
        return None

    try:
        pid = int(pid_file.read_text().strip())
        if psutil.pid_exists(pid):
            return pid
    except (ValueError, OSError):
        pass

    return None


def cmd_start(args: argparse.Namespace) -> None:
    """Start PyAgentVox."""
    # Check if already running
    existing_pid = get_running_pid()
    if existing_pid:
        print(f'⚠️  PyAgentVox is already running (PID: {existing_pid})', file=sys.stderr)
        print(f'Stop it first with: python -m pyagentvox stop', file=sys.stderr)
        sys.exit(1)

    if args.background:
        if sys.platform != 'win32':
            raise NotImplementedError('Background mode only supported on Windows')

        cmd = [sys.executable, '-m', 'pyagentvox', 'start']
        if args.config:
            cmd.extend(['--config', args.config])
        if args.profile:
            cmd.extend(['--profile', args.profile])
        if args.instructions_path:
            cmd.extend(['--instructions-path', args.instructions_path])
        if args.set:
            cmd.extend(['--set', args.set])
        if args.modify:
            cmd.extend(['--modify', args.modify])
        if args.save:
            cmd.append('--save')
        if args.debug:
            cmd.append('--debug')
        if args.log_file:
            cmd.extend(['--log-file', args.log_file])
        if args.tts_only:
            cmd.append('--tts-only')

        CREATE_NO_WINDOW = 0x08000000
        proc = subprocess.Popen(cmd, creationflags=CREATE_NO_WINDOW,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        print(f'🌙 PyAgentVox started in background (PID: {proc.pid})')
        print(f'Stop with: python -m pyagentvox stop')
        return

    config_overrides = {}
    if args.instructions_path:
        config_overrides['instructions_path'] = args.instructions_path

    if args.set:
        set_overrides = config.parse_set_string(args.set)
        logger.debug(f'Parsed --set: {set_overrides}')
        config_overrides = config.merge_dicts(config_overrides, set_overrides)

    if args.modify:
        temp_config, _ = config.load_config(config_path=args.config, profile=args.profile)
        modify_overrides = config.parse_modify_string(args.modify, temp_config)
        logger.debug(f'Parsed --modify: {modify_overrides}')
        config_overrides = config.merge_dicts(config_overrides, modify_overrides)

    if not config_overrides:
        config_overrides = None

    run(
        config_path=args.config,
        profile=args.profile,
        config_overrides=config_overrides,
        save_overrides=args.save,
        debug=args.debug,
        log_file=args.log_file,
        tts_only=args.tts_only,
    )


def cmd_stop(args: argparse.Namespace) -> None:
    """Stop running PyAgentVox instance."""
    if psutil is None:
        print('ERROR: psutil is required for stop command', file=sys.stderr)
        print('Install with: pip install psutil', file=sys.stderr)
        sys.exit(1)

    pid = get_running_pid()
    if not pid:
        print('⚠️  PyAgentVox is not running for this window')
        # Clean up stale PID file
        pid_file = get_pid_file()
        if pid_file.exists():
            pid_file.unlink()
            print('   Cleaned up stale PID file')
        sys.exit(0)

    try:
        process = psutil.Process(pid)
        process.terminate()
        process.wait(timeout=5)
        print(f'✓ Stopped PyAgentVox (PID: {pid})')

        # Clean up PID file
        pid_file = get_pid_file()
        if pid_file.exists():
            pid_file.unlink()

    except psutil.TimeoutExpired:
        process.kill()
        print(f'✓ Force killed PyAgentVox (PID: {pid})')
    except Exception as e:
        print(f'ERROR: {e}', file=sys.stderr)
        sys.exit(1)


def cmd_switch(args: argparse.Namespace) -> None:
    """Switch voice profile of running instance."""
    if psutil is None:
        print('ERROR: psutil is required for switch command', file=sys.stderr)
        print('Install with: pip install psutil', file=sys.stderr)
        sys.exit(1)

    pid = get_running_pid()
    if not pid:
        print('ERROR: PyAgentVox is not running', file=sys.stderr)
        print('Start it first with: python -m pyagentvox start', file=sys.stderr)
        sys.exit(1)

    try:
        # Write profile to control file
        control_file = Path(tempfile.gettempdir()) / f'agent_profile_{pid}.txt'
        control_file.write_text(args.profile, encoding='utf-8')

        print(f'✓ Switching to profile: {args.profile}')
        print(f'  PID: {pid}')

    except Exception as e:
        print(f'ERROR: {e}', file=sys.stderr)
        sys.exit(1)


def cmd_tts(args: argparse.Namespace) -> None:
    """Control TTS (on/off)."""
    pid = get_running_pid()
    if not pid:
        print('ERROR: PyAgentVox is not running', file=sys.stderr)
        sys.exit(1)

    # Write control command to control file
    control_file = Path(tempfile.gettempdir()) / f'agent_control_{pid}.txt'
    control_file.write_text(f'tts:{args.state}', encoding='utf-8')

    state_text = 'enabled' if args.state == 'on' else 'disabled'
    print(f'✓ TTS {state_text}')


def cmd_stt(args: argparse.Namespace) -> None:
    """Control STT (on/off)."""
    pid = get_running_pid()
    if not pid:
        print('ERROR: PyAgentVox is not running', file=sys.stderr)
        sys.exit(1)

    # Write control command to control file
    control_file = Path(tempfile.gettempdir()) / f'agent_control_{pid}.txt'
    control_file.write_text(f'stt:{args.state}', encoding='utf-8')

    state_text = 'enabled' if args.state == 'on' else 'disabled'
    print(f'✓ STT {state_text}')


def cmd_modify(args: argparse.Namespace) -> None:
    """Modify voice settings at runtime."""
    pid = get_running_pid()
    if not pid:
        print('ERROR: PyAgentVox is not running', file=sys.stderr)
        sys.exit(1)

    # Write modification to control file
    control_file = Path(tempfile.gettempdir()) / f'agent_modify_{pid}.txt'
    control_file.write_text(args.setting, encoding='utf-8')

    print(f'✓ Modification queued: {args.setting}')
    print('  Changes will take effect for next TTS message')


def cmd_status(args: argparse.Namespace) -> None:
    """Show status of PyAgentVox instance."""
    if psutil is None:
        print('ERROR: psutil is required for status command', file=sys.stderr)
        print('Install with: pip install psutil', file=sys.stderr)
        sys.exit(1)

    pid = get_running_pid()
    lock_id = get_lock_id()

    print('PyAgentVox Status')
    print('=' * 50)
    print(f'Lock ID: {lock_id}')

    if pid:
        try:
            process = psutil.Process(pid)
            print(f'Status: ✓ Running')
            print(f'PID: {pid}')
            print(f'Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB')
            print(f'CPU: {process.cpu_percent()}%')

            # Show control files
            temp_dir = Path(tempfile.gettempdir())
            print(f'\nControl files:')
            print(f'  Profile: {temp_dir / f"agent_profile_{pid}.txt"}')
            print(f'  Control: {temp_dir / f"agent_control_{pid}.txt"}')
            print(f'  Modify: {temp_dir / f"agent_modify_{pid}.txt"}')

        except Exception as e:
            print(f'Status: ⚠️  Error reading process info')
            print(f'Error: {e}')
    else:
        print('Status: ✗ Not running')
        print('\nStart with: python -m pyagentvox start')


def main() -> None:
    """Parse CLI arguments and execute subcommand."""
    parser = argparse.ArgumentParser(
        description='PyAgentVox - Two-way voice communication for AI agents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest='command', help='Subcommands')

    # START subcommand
    start_parser = subparsers.add_parser('start', help='Start PyAgentVox')
    start_parser.add_argument('--config', type=str, help='Path to config file (JSON or YAML)')
    start_parser.add_argument('--profile', type=str, help='Load config profile')
    start_parser.add_argument('--instructions-path', type=str, help='Path to CLAUDE.md')
    start_parser.add_argument('--set', type=str, metavar='KEY=VALUE ...',
                              help='Set config values')
    start_parser.add_argument('--modify', type=str, metavar='KEY=MODIFIER ...',
                              help='Modify config values')
    start_parser.add_argument('--save', action='store_true', help='Save changes to config')
    start_parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    start_parser.add_argument('--log-file', type=str, help='Write logs to file')
    start_parser.add_argument('--background', action='store_true', help='Run in background')
    start_parser.add_argument('--tts-only', action='store_true', help='TTS only (no STT)')
    start_parser.set_defaults(func=cmd_start)

    # STOP subcommand
    stop_parser = subparsers.add_parser('stop', help='Stop running instance')
    stop_parser.set_defaults(func=cmd_stop)

    # SWITCH subcommand
    switch_parser = subparsers.add_parser('switch', help='Switch voice profile')
    switch_parser.add_argument('profile', help='Profile name (michelle, jenny, etc.)')
    switch_parser.set_defaults(func=cmd_switch)

    # TTS subcommand
    tts_parser = subparsers.add_parser('tts', help='Control TTS output')
    tts_parser.add_argument('state', choices=['on', 'off'], help='Enable or disable TTS')
    tts_parser.set_defaults(func=cmd_tts)

    # STT subcommand
    stt_parser = subparsers.add_parser('stt', help='Control speech recognition')
    stt_parser.add_argument('state', choices=['on', 'off'], help='Enable or disable STT')
    stt_parser.set_defaults(func=cmd_stt)

    # MODIFY subcommand
    modify_parser = subparsers.add_parser('modify', help='Modify voice settings at runtime')
    modify_parser.add_argument('setting', help='Setting to modify (e.g., pitch=+5, neutral.speed=-10)')
    modify_parser.set_defaults(func=cmd_modify)

    # STATUS subcommand
    status_parser = subparsers.add_parser('status', help='Show status')
    status_parser.set_defaults(func=cmd_status)

    # Parse arguments
    args = parser.parse_args()

    # Default to 'start' if no subcommand provided (backward compatibility)
    if not args.command:
        # Re-parse with start subcommand
        sys.argv.insert(1, 'start')
        args = parser.parse_args()

    # Execute subcommand
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
