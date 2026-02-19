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


def _generate_voice_instructions(config: Optional[dict] = None, profile_name: Optional[str] = None) -> str:
    """Generate voice instructions dynamically based on config and profile.

    Args:
        config: Configuration dictionary (optional)
        profile_name: Active profile name (optional)

    Returns:
        Formatted voice instructions string with profile description if available
    """
    base_instructions = '''<!-- PYAGENTVOX_START -->
# Voice Output Active 🎤

Your responses are **spoken aloud** and displayed as an animated avatar. Control voice with emotion tags anywhere in your message:

**Available emotions:** `[neutral]` `[cheerful]` `[excited]` `[empathetic]` `[warm]` `[calm]` `[focused]`

**Usage:** Place tags to switch voice mid-message:
- `Hello! [cheerful] Your code works! [calm] Let me explain why...`

Tags are removed from spoken text. Multiple emotions = multiple voice segments.

**Avatar:** Luna's avatar displays your current emotion and automatically transitions to bored/sleeping states during long idle periods.

## Avatar Tag System

The avatar uses a tag-based image system for fine-grained control over which images are displayed. Each avatar image has:
- **Emotion tag** (required): cheerful, excited, calm, focused, warm, empathetic, neutral, etc.
- **Custom tags** (optional): outfit names, poses, moods, contexts, etc.

**Manage avatar images:**
```bash
# Scan for unregistered images
python -m pyagentvox.avatar_tags scan

# Register new image
python -m pyagentvox.avatar_tags add path/to/image.png --tags cheerful,dress,wave

# Update image tags
python -m pyagentvox.avatar_tags update path/to/image.png --tags cheerful,dress,peace-sign

# List all registered images
python -m pyagentvox.avatar_tags list

# List images with specific tag
python -m pyagentvox.avatar_tags list --tag cheerful
```

**Runtime tag filtering** (requires PID from PyAgentVox startup):
```bash
# Show only specific tags
python -m pyagentvox.avatar_tags filter --pid <PID> --include casual,summer

# Hide specific tags
python -m pyagentvox.avatar_tags filter --pid <PID> --exclude formal

# Reset filters
python -m pyagentvox.avatar_tags filter --pid <PID> --reset
```

**Examples:**
- Switch to casual summer outfit: `--include daisy-dukes,casual`
- Hide formal outfits: `--exclude formal,ball-gown`
- Show only cheerful poses without hoodie: `--include cheerful --exclude hoodie`

**Animation:** Images with significantly different tags trigger a flip animation for smooth visual transitions.

**Avatar Tag Control:** Use the `/avatar-tags` skill to manage avatar filtering:
- `/avatar-tags list` - See all available tags with counts by category
- `/avatar-tags filter --include casual,summer` - Show only images with specific tags
- `/avatar-tags filter --exclude formal` - Hide images with specific tags
- `/avatar-tags filter --reset` - Clear all filters
- `/avatar-tags current` - Show current filter state'''

    # Add profile information if available
    profile_info = None
    if config:
        # Check for active profile description
        if profile_name and 'profiles' in config and profile_name in config['profiles']:
            profile_config = config['profiles'][profile_name]
            if 'description' in profile_config:
                profile_info = f"**Current Profile:** `{profile_name}` - {profile_config['description']}"
        # Fall back to default profile description
        elif 'description' in config and not profile_name:
            profile_info = f"**Current Profile:** Default - {config['description']}"

    # Add profile switching instructions
    switch_instructions = '\n\n**Switch Profiles:** Use the `/voice-switch` skill to change voice profiles during conversations.'

    # Add available profiles list if config has profiles
    if config and 'profiles' in config:
        profiles_list = '\n\n**Available Profiles:**'
        # Add default profile
        if 'description' in config:
            profiles_list += f"\n- `default` - {config['description']}"
        # Add named profiles
        for name, profile_config in config.get('profiles', {}).items():
            if isinstance(profile_config, dict) and 'description' in profile_config:
                profiles_list += f"\n- `{name}` - {profile_config['description']}"
        switch_instructions += profiles_list

    # Assemble final instructions
    instructions = base_instructions
    if profile_info:
        instructions += '\n\n' + profile_info
    instructions += switch_instructions
    instructions += '\n<!-- PYAGENTVOX_END -->'

    return instructions


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


def inject_voice_instructions(
    instructions_path: Optional[Path] = None,
    config: Optional[dict] = None,
    profile_name: Optional[str] = None
) -> tuple[bool, Optional[str]]:
    """Inject voice instructions into instructions file.

    Args:
        instructions_path: Optional path to instructions file (auto-detects CLAUDE.md if None)
        config: Optional configuration dictionary (for profile descriptions)
        profile_name: Optional active profile name

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

    # Generate instructions dynamically
    voice_instructions = _generate_voice_instructions(config, profile_name)

    # If instructions already exist, update them instead of duplicating
    if VOICE_SECTION_MARKER_START in content:
        logger.debug('Updating existing voice instructions')
        pattern = rf'{re.escape(VOICE_SECTION_MARKER_START)}.*?{re.escape(VOICE_SECTION_MARKER_END)}'
        new_content = re.sub(pattern, voice_instructions, content, flags=re.DOTALL)
    else:
        logger.debug('Injecting new voice instructions')
        new_content = content.rstrip() + '\n\n' + voice_instructions.strip() + '\n'

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
