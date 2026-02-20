"""Autonomous setup system for PyAgentVox.

Enables agents to configure PyAgentVox from scratch with zero human input.
Handles config generation, skill installation, and validation.

Key features:
    - Generates default pyagentvox.yaml with Ava voice profile
    - Copies Claude Code skills to ~/.claude/skills/ with path patching
    - Validates all components are ready to run
    - Cross-platform support (Windows/Unix)

Usage:
    python -m pyagentvox setup
    python -m pyagentvox setup --force  # Overwrite existing files

Author:
    Jake Meador <jameador13@gmail.com>
"""

import logging
import shutil
import sys
from pathlib import Path

__author__ = 'Jake Meador <jameador13@gmail.com>'
__all__ = ['run_setup']

logger = logging.getLogger('pyagentvox')

# Skill directories to install
SKILL_DIRS = [
    'voice',
    'voice-stop',
    'voice-switch',
    'voice-modify',
    'tts-control',
    'stt-control',
    'avatar-tags',
]


def _get_package_dir() -> Path:
    """Get the PyAgentVox package directory.

    Returns:
        Path to the package directory containing source files.
    """
    return Path(__file__).parent


def _get_project_root() -> Path:
    """Get the PyAgentVox project root directory.

    Returns:
        Path to the project root (parent of package dir).
    """
    return _get_package_dir().parent


def _get_skills_source_dir() -> Path:
    """Get the source directory containing Claude Code skills.

    Returns:
        Path to .claude/skills/ in the project root.
    """
    return _get_project_root() / '.claude' / 'skills'


def _get_skills_dest_dir() -> Path:
    """Get the destination directory for Claude Code skills.

    Returns:
        Path to ~/.claude/skills/ for the current user.
    """
    return Path.home() / '.claude' / 'skills'


def _get_pyagentvox_root_posix() -> str:
    """Get the PyAgentVox project root as a POSIX-style path string.

    Shell scripts use forward slashes even on Windows (Git Bash, MSYS2).

    Returns:
        POSIX-style path string for use in shell scripts.
    """
    return _get_project_root().as_posix()


def generate_config(target_dir: Path, force: bool = False) -> bool:
    """Generate default pyagentvox.yaml in the target directory.

    Copies the bundled config file from the package. The default config
    uses the Ava voice with all emotion mappings and voice profiles.

    Args:
        target_dir: Directory to write pyagentvox.yaml into.
        force: If True, overwrite existing config file.

    Returns:
        True if config was generated, False if skipped.
    """
    source_config = _get_package_dir() / 'pyagentvox.yaml'
    target_config = target_dir / 'pyagentvox.yaml'

    if target_config.exists() and not force:
        print(f'  [SKIP] Config already exists: {target_config}')
        return False

    if not source_config.exists():
        print(f'  [ERROR] Source config not found: {source_config}', file=sys.stderr)
        return False

    shutil.copy2(source_config, target_config)
    print(f'  [OK] Generated config: {target_config}')
    return True


def _patch_skill_script(script_path: Path, project_root: str) -> None:
    """Patch a skill shell script to use the correct project root path.

    Replaces the hardcoded PYAGENTVOX_ROOT variable in .sh files with the
    actual path where PyAgentVox is installed.

    Args:
        script_path: Path to the .sh skill script.
        project_root: POSIX-style path to the PyAgentVox project root.
    """
    content = script_path.read_text(encoding='utf-8')

    # Replace the hardcoded PYAGENTVOX_ROOT line with the actual install path
    patched = []
    for line in content.splitlines():
        if line.startswith('PYAGENTVOX_ROOT='):
            patched.append(f'PYAGENTVOX_ROOT="{project_root}"')
        else:
            patched.append(line)

    script_path.write_text('\n'.join(patched) + '\n', encoding='utf-8')


def install_skills(force: bool = False) -> tuple[int, int]:
    """Copy Claude Code skills to ~/.claude/skills/ with path patching.

    Each skill directory contains a SKILL.md and a .sh script. The .sh scripts
    have a hardcoded PYAGENTVOX_ROOT path that gets patched to the actual
    installation location.

    Args:
        force: If True, overwrite existing skill directories.

    Returns:
        Tuple of (installed_count, skipped_count).
    """
    source_dir = _get_skills_source_dir()
    dest_dir = _get_skills_dest_dir()
    project_root = _get_pyagentvox_root_posix()

    if not source_dir.exists():
        print(f'  [ERROR] Skills source not found: {source_dir}', file=sys.stderr)
        return 0, 0

    # Ensure destination parent exists
    dest_dir.mkdir(parents=True, exist_ok=True)

    installed = 0
    skipped = 0

    for skill_name in SKILL_DIRS:
        skill_source = source_dir / skill_name
        skill_dest = dest_dir / skill_name

        if not skill_source.exists():
            print(f'  [WARN] Skill not found in source: {skill_name}')
            skipped += 1
            continue

        if skill_dest.exists() and not force:
            print(f'  [SKIP] Skill already installed: {skill_name}')
            skipped += 1
            continue

        # Remove existing skill dir if force overwriting
        if skill_dest.exists():
            shutil.rmtree(skill_dest)

        # Copy entire skill directory
        shutil.copytree(skill_source, skill_dest)

        # Patch .sh scripts with correct project root
        for sh_file in skill_dest.glob('*.sh'):
            _patch_skill_script(sh_file, project_root)

        print(f'  [OK] Installed skill: {skill_name}')
        installed += 1

    return installed, skipped


def validate_setup() -> list[str]:
    """Validate that PyAgentVox setup is complete and ready to run.

    Checks for:
        - Config file in CWD or package directory
        - Required Python packages
        - Skills installed in ~/.claude/skills/
        - Platform compatibility

    Returns:
        List of validation issue strings. Empty list means all good.
    """
    issues = []

    # Check config exists somewhere findable
    cwd_config = Path.cwd() / 'pyagentvox.yaml'
    pkg_config = _get_package_dir() / 'pyagentvox.yaml'
    if not cwd_config.exists() and not pkg_config.exists():
        issues.append('No pyagentvox.yaml found (run setup to generate one)')

    # Check critical dependencies
    _check_dependency(issues, 'edge_tts', 'edge-tts')
    _check_dependency(issues, 'yaml', 'pyyaml')
    _check_dependency(issues, 'pygame', 'pygame')
    _check_dependency(issues, 'speech_recognition', 'speechrecognition')
    _check_dependency(issues, 'psutil', 'psutil')

    # Check platform-specific deps
    if sys.platform == 'win32':
        _check_dependency(issues, 'win32gui', 'pywin32')

    # Check skills installed
    dest_dir = _get_skills_dest_dir()
    missing_skills = []
    for skill_name in SKILL_DIRS:
        skill_dir = dest_dir / skill_name
        if not skill_dir.exists() or not (skill_dir / 'SKILL.md').exists():
            missing_skills.append(skill_name)

    if missing_skills:
        issues.append(f'Missing skills in ~/.claude/skills/: {", ".join(missing_skills)}')

    return issues


def _check_dependency(issues: list[str], import_name: str, package_name: str) -> None:
    """Check if a Python package is importable.

    Args:
        issues: List to append issues to.
        import_name: Python import name to check.
        package_name: pip package name for error message.
    """
    try:
        __import__(import_name)
    except ImportError:
        issues.append(f'Missing package: {package_name} (pip install {package_name})')


def run_setup(force: bool = False) -> bool:
    """Run the full autonomous setup process.

    This is the main entry point called by the CLI. It:
    1. Generates default pyagentvox.yaml in the current directory
    2. Installs Claude Code skills to ~/.claude/skills/
    3. Validates everything is ready
    4. Prints success message with next steps

    Args:
        force: If True, overwrite existing files.

    Returns:
        True if setup completed successfully, False otherwise.
    """
    print()
    print('=' * 60)
    print('  PyAgentVox Autonomous Setup')
    print('=' * 60)
    print()

    # Step 1: Generate config
    print('[1/3] Generating configuration...')
    generate_config(Path.cwd(), force=force)
    print()

    # Step 2: Install skills
    print('[2/3] Installing Claude Code skills...')
    installed, skipped = install_skills(force=force)
    print(f'       ({installed} installed, {skipped} skipped)')
    print()

    # Step 3: Validate
    print('[3/3] Validating setup...')
    issues = validate_setup()

    if issues:
        print()
        print('  ISSUES FOUND:')
        for issue in issues:
            print(f'    - {issue}')
        print()
        print('  Fix the issues above, then run setup again.')
        print()
        return False

    print('  [OK] All checks passed!')
    print()

    # Success message
    print('=' * 60)
    print('  Setup Complete!')
    print('=' * 60)
    print()
    print('  Start PyAgentVox:')
    print('    python -m pyagentvox start')
    print()
    print('  Start with a voice profile:')
    print('    python -m pyagentvox start --profile michelle')
    print()
    print('  Start in background:')
    print('    python -m pyagentvox start --background')
    print()
    print('  Start TTS only (no microphone):')
    print('    python -m pyagentvox start --tts-only')
    print()
    print('  Or use Claude Code skills:')
    print('    /voice              # Start with default voice')
    print('    /voice michelle     # Start with Michelle voice')
    print('    /voice tts-only     # Voice output only')
    print()
    print('  Available voice profiles:')
    print('    default, michelle, jenny, emma, aria, ava, sonia, libby')
    print()

    return True
