"""CLI entry point for PyAgentVox voice system.

This module provides command-line argument parsing and main entry point
for running PyAgentVox from the command line.

Usage:
    # Basic usage with defaults
    python -m pyagentvox

    # Load profile
    python -m pyagentvox --profile male_voices

    # Override config values
    python -m pyagentvox --set "speed=15 pitch=5"

    # Modify existing values
    python -m pyagentvox --modify "speed=+5 pitch=-3"

    # Run in background (Windows)
    python -m pyagentvox --background --log-file vox.log

Author:
    Jake Meador <jameador13@gmail.com>
"""

import argparse
import logging
import subprocess
import sys

from . import config
from .pyagentvox import run

__author__ = 'Jake Meador <jameador13@gmail.com>'
__all__ = ['main']

logger = logging.getLogger('pyagentvox')


def main() -> None:
    """Parse CLI arguments and run PyAgentVox."""
    parser = argparse.ArgumentParser(
        description='PyAgentVox - Two-way voice communication for AI agents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  pyagentvox
  pyagentvox --profile male_voices
  pyagentvox --set "neutral.voice=michelle speed=10 pitch=-5"
  pyagentvox --modify "speed=5 pitch=-3"
  pyagentvox --background --log-file vox.log

Config file discovery:
  1. --config path (if provided)
  2. pyagentvox.json in current directory
  3. pyagentvox.yaml in current directory
  4. config.example.yaml in package directory

Shorthands:
  speed=10    → applies to all emotions
  pitch=+5Hz  → applies to all emotions
  voice=jenny → applies to all emotions
        '''
    )

    parser.add_argument('--config', type=str, help='Path to config file (JSON or YAML)')
    parser.add_argument('--profile', type=str, help='Load config profile')
    parser.add_argument('--instructions-path', type=str, help='Path to instructions file (default: auto-detect CLAUDE.md)')
    parser.add_argument('--set', type=str, metavar='KEY=VALUE ...',
                        help='Set config values (space-separated)')
    parser.add_argument('--modify', type=str, metavar='KEY=MODIFIER ...',
                        help='Modify config values by adding amounts')
    parser.add_argument('--save', action='store_true', help='Save changes to config file')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--log-file', type=str, help='Write logs to file')
    parser.add_argument('--background', action='store_true', help='Run as background process (Windows only)')
    parser.add_argument('--tts-only', action='store_true', help='TTS output only (disable speech recognition)')

    args = parser.parse_args()

    if args.background:
        if sys.platform != 'win32':
            logger.error('Background mode only supported on Windows')
            sys.exit(1)

        cmd = [sys.executable, '-m', 'pyagentvox']
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

        CREATE_NO_WINDOW = 0x08000000
        proc = subprocess.Popen(cmd, creationflags=CREATE_NO_WINDOW,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        logger.info(f'PyAgentVox started in background (PID: {proc.pid})')
        logger.info(f'Stop with: taskkill /PID {proc.pid}')
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


if __name__ == '__main__':
    main()
