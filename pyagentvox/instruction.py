"""Instruction file management for PyAgentVox.

This module handles automatic injection and removal of voice control instructions
into project instruction files (like CLAUDE.md). Finds instruction files via
current directory, parent directory, or Claude sessions index.

Usage:
    # Auto-inject voice instructions
    success, message = inject_voice_instructions()

    # Clean up on exit
    remove_voice_instructions()

Author:
    Jake Meador <jameador13@gmail.com>
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

__author__ = 'Jake Meador <jameador13@gmail.com>'
__all__ = [
    'find_instructions_file',
    'inject_voice_instructions',
    'remove_voice_instructions',
]

logger = logging.getLogger('pyagentvox')

VOICE_SECTION_MARKER_START = '<!-- PYAGENTVOX_START -->'
VOICE_SECTION_MARKER_END = '<!-- PYAGENTVOX_END -->'

VOICE_INSTRUCTIONS = '''
<!-- PYAGENTVOX_START -->
# Voice Output Active 🎤

Your responses are **spoken aloud**. Control voice with emotion tags anywhere in your message:

**Available emotions:** `[neutral]` `[cheerful]` `[excited]` `[empathetic]` `[warm]` `[calm]` `[focused]`

**Usage:** Place tags to switch voice mid-message:
- `Hello! [cheerful] Your code works! [calm] Let me explain why...`

Tags are removed from spoken text. Multiple emotions = multiple voice segments.
<!-- PYAGENTVOX_END -->
'''


def find_instructions_file(filename: str = 'CLAUDE.md') -> Optional[Path]:
    """Find instructions file via current dir, parent, or sessions-index.json.

    Args:
        filename: Name of instructions file (default: CLAUDE.md)
    """
    cwd = Path.cwd()
    if (file := cwd / filename).exists():
        return file

    if (parent_file := cwd.parent / filename).exists():
        return parent_file

    home = Path.home()
    projects_dir = home / '.claude' / 'projects'
    if not projects_dir.exists():
        return None

    project_dirs = [d for d in projects_dir.iterdir() if d.is_dir()]
    if not project_dirs:
        return None

    recent = max(project_dirs, key=lambda p: p.stat().st_mtime)
    sessions_index = recent / 'sessions-index.json'

    if sessions_index.exists():
        try:
            with open(sessions_index, encoding='utf-8') as f:
                data = json.load(f)
                if original_path := data.get('originalPath'):
                    if (file := Path(original_path) / filename).exists():
                        return file
        except Exception as e:
            logger.warning(f'Could not read sessions-index.json: {e}')

    if (project_file := recent / filename).exists():
        return project_file

    return None


def inject_voice_instructions(instructions_path: Optional[Path] = None) -> tuple[bool, Optional[str]]:
    """Inject voice instructions into instructions file.

    Args:
        instructions_path: Optional path to instructions file (auto-detects CLAUDE.md if None)

    Returns:
        Tuple of (success: bool, message_to_agent: Optional[str])
        If successful, returns a message that should be sent to the agent to refresh the file.
    """
    if not instructions_path:
        instructions_path = find_instructions_file()

    if not instructions_path:
        logger.info('Instructions file not found, voice instructions not injected')
        return False, None

    try:
        content = instructions_path.read_text(encoding='utf-8')
    except Exception as e:
        logger.error(f'Error reading instructions file: {e}')
        return False, None

    if VOICE_SECTION_MARKER_START in content:
        logger.debug('Voice instructions already present')
        return True, None

    new_content = content.rstrip() + '\n\n' + VOICE_INSTRUCTIONS.strip() + '\n'

    try:
        instructions_path.write_text(new_content, encoding='utf-8')
        logger.info(f'Injected voice instructions into: {instructions_path}')

        refresh_message = (
            f'[SYSTEM] Voice instructions have been injected into {instructions_path.name}. '
            f'Please read this file again to see the voice control documentation.'
        )

        return True, refresh_message
    except Exception as e:
        logger.error(f'Error writing instructions file: {e}')
        return False, None


def remove_voice_instructions(instructions_path: Optional[Path] = None) -> bool:
    """Remove voice instructions from instructions file."""
    if not instructions_path:
        instructions_path = find_instructions_file()

    if not instructions_path:
        logger.debug('Instructions file not found, nothing to clean up')
        return False

    try:
        content = instructions_path.read_text(encoding='utf-8')
    except Exception as e:
        logger.error(f'Error reading instructions file: {e}')
        return False

    if VOICE_SECTION_MARKER_START not in content:
        logger.debug('No voice instructions to remove')
        return True

    pattern = rf'{re.escape(VOICE_SECTION_MARKER_START)}.*?{re.escape(VOICE_SECTION_MARKER_END)}'
    new_content = re.sub(pattern, '', content, flags=re.DOTALL)
    new_content = re.sub(r'\n\n\n+', '\n\n', new_content).strip() + '\n'

    try:
        instructions_path.write_text(new_content, encoding='utf-8')
        logger.info(f'Removed voice instructions from: {instructions_path}')
        return True
    except Exception as e:
        logger.error(f'Error writing instructions file: {e}')
        return False
