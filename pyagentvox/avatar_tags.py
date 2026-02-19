"""Avatar tag system management for PyAgentVox.

This module provides tools for managing avatar images with tags:
- Scan directories to find unregistered images
- Register images with emotion and custom tags
- Update tags for existing images
- Remove images from registry
- Apply runtime tag filters

Can be used as a CLI tool or imported by agent skills.

Usage:
    # Scan for unregistered images
    python -m pyagentvox.avatar_tags scan

    # Register a new image
    python -m pyagentvox.avatar_tags add path/to/image.png --tags cheerful,dress,wave

    # Update image tags
    python -m pyagentvox.avatar_tags update path/to/image.png --tags cheerful,dress,peace-sign

    # Remove image from registry
    python -m pyagentvox.avatar_tags remove path/to/image.png

    # List all registered images
    python -m pyagentvox.avatar_tags list

    # List images with specific tag
    python -m pyagentvox.avatar_tags list --tag cheerful

    # Apply runtime filters
    python -m pyagentvox.avatar_tags filter --include casual,summer
    python -m pyagentvox.avatar_tags filter --exclude formal
    python -m pyagentvox.avatar_tags filter --reset

Author:
    Jake Meador <jameador13@gmail.com>
"""

import argparse
import logging
import sys
import tempfile
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    print('ERROR: PyYAML is required for avatar tag management.', file=sys.stderr)
    print('Install with: pip install pyyaml', file=sys.stderr)
    raise SystemExit(1)

__author__ = 'Jake Meador <jameador13@gmail.com>'
__all__ = [
    'scan_unregistered_images',
    'add_image_to_config',
    'update_image_tags',
    'remove_image_from_config',
    'list_images',
    'list_tags',
    'apply_filters',
    'read_current_filters',
]

logger = logging.getLogger('pyagentvox.avatar_tags')

# Valid emotion tags
VALID_EMOTIONS = {
    'cheerful', 'excited', 'calm', 'focused', 'warm', 'empathetic', 'neutral',
    'thinking', 'curious', 'determined', 'apologetic', 'playful', 'surprised',
    'waiting', 'bored', 'sleeping'
}

# Valid control tags (specialty tags for interactive controls)
# Naming convention: control-<component>-<trigger>[-<state>]
# Tags describe FUNCTION (when/why shown), not content (what they look like)
VALID_CONTROL_TAGS = {
    # Button hover states (function: when hovering over buttons)
    'control-tts-hover-on',      # TTS button hover when enabled
    'control-tts-hover-off',     # TTS button hover when disabled
    'control-stt-hover-on',      # STT button hover when enabled
    'control-stt-hover-off',     # STT button hover when disabled
    'control-close-hover',       # Close button hover

    # Button click feedback (function: confirmation after click)
    'control-tts-clicked',       # TTS button clicked confirmation
    'control-stt-clicked',       # STT button clicked confirmation

    # Special animations (function: when animation triggers)
    'control-close-animation',   # Close button animation (before slide down)
}

# All valid first tags (emotion or control)
VALID_FIRST_TAGS = VALID_EMOTIONS | VALID_CONTROL_TAGS

# Known outfit/clothing tags for categorization
KNOWN_OUTFIT_TAGS = {
    'dress', 'daisy-dukes', 'tank-top', 'casual', 'hoodie', 'formal',
    'ball-gown', 'sundress', 'shorts', 'skirt', 'jeans', 'sweater',
    'jacket', 'coat', 'swimsuit', 'bikini', 'pajamas', 'armor',
    'uniform', 'costume', 'apron', 't-shirt', 'blouse', 'crop-top',
    'leggings', 'boots', 'heels', 'sneakers', 'sandals', 'hat',
    'scarf', 'glasses', 'sunglasses', 'overalls', 'romper', 'robe',
}


# ============================================================================
# Config Management
# ============================================================================

def find_config_file() -> Optional[Path]:
    """Find pyagentvox.yaml in current directory or package directory.

    Returns:
        Path to config file, or None if not found.
    """
    # Check current directory
    cwd = Path.cwd()
    if (config := cwd / 'pyagentvox.yaml').exists():
        return config

    # Check parent directory
    if (config := cwd.parent / 'pyagentvox.yaml').exists():
        return config

    # Check package directory
    try:
        package_dir = Path(__file__).parent
        if (config := package_dir / 'pyagentvox.yaml').exists():
            return config
    except NameError:
        pass

    return None


def load_config(config_path: Optional[Path] = None) -> dict:
    """Load configuration from pyagentvox.yaml.

    Args:
        config_path: Optional path to config file (auto-detects if None).

    Returns:
        Configuration dictionary.

    Raises:
        FileNotFoundError: If config file not found.
    """
    if not config_path:
        config_path = find_config_file()

    if not config_path:
        raise FileNotFoundError('Could not find pyagentvox.yaml')

    with open(config_path, encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_config(config: dict, config_path: Optional[Path] = None) -> None:
    """Save configuration to pyagentvox.yaml.

    Args:
        config: Configuration dictionary to save.
        config_path: Optional path to config file (auto-detects if None).

    Raises:
        FileNotFoundError: If config file not found.
    """
    if not config_path:
        config_path = find_config_file()

    if not config_path:
        raise FileNotFoundError('Could not find pyagentvox.yaml')

    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


# ============================================================================
# Image Registry Management
# ============================================================================

def scan_unregistered_images(
    avatar_dir: Optional[Path] = None,
    config_path: Optional[Path] = None
) -> list[Path]:
    """Find all image files not yet registered in config.

    Args:
        avatar_dir: Directory to scan (uses config default if None).
        config_path: Path to config file (auto-detects if None).

    Returns:
        Sorted list of unregistered image paths.
    """
    config = load_config(config_path)

    if not avatar_dir:
        avatar_dir = Path(config['avatar']['directory']).expanduser()

    if not avatar_dir.exists():
        logger.error(f'Avatar directory does not exist: {avatar_dir}')
        return []

    # Get all image files
    all_images = []
    for ext in ['*.png', '*.jpg', '*.jpeg', '*.webp']:
        all_images.extend(avatar_dir.rglob(ext))

    # Get registered paths
    registered_paths = set()
    for img_entry in config.get('avatar', {}).get('images', []):
        path = Path(img_entry['path'])
        if not path.is_absolute():
            path = avatar_dir / path
        registered_paths.add(path.resolve())

    # Find unregistered
    unregistered = [p for p in all_images if p.resolve() not in registered_paths]

    return sorted(unregistered)


def add_image_to_config(
    image_path: Path,
    tags: list[str],
    config_path: Optional[Path] = None
) -> None:
    """Add new image entry to config file.

    Args:
        image_path: Path to the image file.
        tags: List of tags (must include at least one emotion tag).
        config_path: Path to config file (auto-detects if None).

    Raises:
        ValueError: If no emotion tag provided or image already registered.
        FileNotFoundError: If config file not found.
    """
    # Validate at least one emotion or control tag
    tag_set = {tag.lower() for tag in tags}
    has_valid_first_tag = any(tag in VALID_FIRST_TAGS for tag in tag_set)

    if not has_valid_first_tag:
        raise ValueError(
            f'Image must have at least one emotion or control tag.\n'
            f'Emotions: {sorted(VALID_EMOTIONS)}\n'
            f'Control tags: {sorted(VALID_CONTROL_TAGS)}'
        )

    # Load config
    config = load_config(config_path)
    avatar_dir = Path(config['avatar']['directory']).expanduser()

    # Ensure avatar section exists
    if 'avatar' not in config:
        config['avatar'] = {}
    if 'images' not in config['avatar']:
        config['avatar']['images'] = []

    # Check if already registered
    for img in config['avatar']['images']:
        existing_path = Path(img['path'])
        if not existing_path.is_absolute():
            existing_path = avatar_dir / existing_path
        if existing_path.resolve() == image_path.resolve():
            raise ValueError(f'Image already registered: {image_path}')

    # Make path relative to avatar directory if possible
    try:
        relative_path = str(image_path.relative_to(avatar_dir))
        # Convert backslashes to forward slashes for cross-platform consistency
        relative_path = relative_path.replace('\\', '/')
    except ValueError:
        relative_path = str(image_path)

    # Add entry
    config['avatar']['images'].append({
        'path': relative_path,
        'tags': tags
    })

    # Save
    save_config(config, config_path)
    logger.info(f'Added image: {relative_path} with tags: {tags}')


def update_image_tags(
    image_path: Path,
    tags: list[str],
    config_path: Optional[Path] = None
) -> None:
    """Update tags for existing image.

    Args:
        image_path: Path to the image file.
        tags: New list of tags (must include at least one emotion tag).
        config_path: Path to config file (auto-detects if None).

    Raises:
        ValueError: If no emotion tag provided or image not found.
        FileNotFoundError: If config file not found.
    """
    # Validate at least one emotion or control tag
    tag_set = {tag.lower() for tag in tags}
    has_valid_first_tag = any(tag in VALID_FIRST_TAGS for tag in tag_set)

    if not has_valid_first_tag:
        raise ValueError(
            f'Image must have at least one emotion or control tag.\n'
            f'Emotions: {sorted(VALID_EMOTIONS)}\n'
            f'Control tags: {sorted(VALID_CONTROL_TAGS)}'
        )

    # Load config
    config = load_config(config_path)
    avatar_dir = Path(config['avatar']['directory']).expanduser()

    # Find and update image
    found = False
    for img in config.get('avatar', {}).get('images', []):
        existing_path = Path(img['path'])
        if not existing_path.is_absolute():
            existing_path = avatar_dir / existing_path

        if existing_path.resolve() == image_path.resolve():
            img['tags'] = tags
            found = True
            logger.info(f'Updated tags for {img["path"]}: {tags}')
            break

    if not found:
        raise ValueError(f'Image not found in registry: {image_path}')

    # Save
    save_config(config, config_path)


def remove_image_from_config(
    image_path: Path,
    config_path: Optional[Path] = None
) -> None:
    """Remove image from config file.

    Args:
        image_path: Path to the image file.
        config_path: Path to config file (auto-detects if None).

    Raises:
        ValueError: If image not found.
        FileNotFoundError: If config file not found.
    """
    # Load config
    config = load_config(config_path)
    avatar_dir = Path(config['avatar']['directory']).expanduser()

    # Find and remove image
    images = config.get('avatar', {}).get('images', [])
    new_images = []
    found = False

    for img in images:
        existing_path = Path(img['path'])
        if not existing_path.is_absolute():
            existing_path = avatar_dir / existing_path

        if existing_path.resolve() == image_path.resolve():
            found = True
            logger.info(f'Removed image: {img["path"]}')
        else:
            new_images.append(img)

    if not found:
        raise ValueError(f'Image not found in registry: {image_path}')

    config['avatar']['images'] = new_images

    # Save
    save_config(config, config_path)


def list_images(
    tag_filter: Optional[str] = None,
    config_path: Optional[Path] = None
) -> list[dict]:
    """List all registered images, optionally filtered by tag.

    Args:
        tag_filter: Optional tag to filter by (case-insensitive).
        config_path: Path to config file (auto-detects if None).

    Returns:
        List of image dictionaries with 'path' and 'tags' keys.
    """
    config = load_config(config_path)
    images = config.get('avatar', {}).get('images', [])

    if tag_filter:
        tag_lower = tag_filter.lower()
        images = [
            img for img in images
            if any(tag.lower() == tag_lower for tag in img.get('tags', []))
        ]

    return images


# ============================================================================
# Runtime Filter Control
# ============================================================================

def apply_filters(
    pid: int,
    include_tags: Optional[list[str]] = None,
    exclude_tags: Optional[list[str]] = None,
    require_all: bool = False,
    reset: bool = False
) -> None:
    """Apply runtime tag filters by writing to IPC file.

    Args:
        pid: Process ID of running PyAgentVox instance.
        include_tags: Tags to include (show only images with these tags).
        exclude_tags: Tags to exclude (hide images with these tags).
        require_all: If True, require ALL include tags; if False, require ANY.
        reset: If True, clear all filters (ignores other arguments).
    """
    filter_file = Path(tempfile.gettempdir()) / f'agent_avatar_filter_{pid}.txt'

    if reset:
        filter_file.write_text('reset', encoding='utf-8')
        logger.info('[FILTER] Reset all filters')
        return

    commands = []

    if include_tags:
        commands.append(f'include:{",".join(include_tags)}')
        logger.info(f'[FILTER] Include tags: {include_tags}')

    if exclude_tags:
        commands.append(f'exclude:{",".join(exclude_tags)}')
        logger.info(f'[FILTER] Exclude tags: {exclude_tags}')

    if require_all:
        commands.append('require_all:true')
        logger.info('[FILTER] Require all include tags')

    if commands:
        filter_file.write_text('\n'.join(commands), encoding='utf-8')


def read_current_filters(pid: int) -> dict[str, list[str] | bool]:
    """Read current runtime tag filters from IPC file.

    Args:
        pid: Process ID of running PyAgentVox instance.

    Returns:
        Dictionary with 'include', 'exclude', and 'require_all' keys.
        Empty lists and False if no filter file exists.
    """
    filter_file = Path(tempfile.gettempdir()) / f'agent_avatar_filter_{pid}.txt'

    result: dict[str, list[str] | bool] = {
        'include': [],
        'exclude': [],
        'require_all': False,
    }

    if not filter_file.exists():
        return result

    content = filter_file.read_text(encoding='utf-8').strip()

    if content == 'reset':
        return result

    for line in content.splitlines():
        line = line.strip()
        if line.startswith('include:'):
            result['include'] = [t.strip() for t in line[8:].split(',') if t.strip()]
        elif line.startswith('exclude:'):
            result['exclude'] = [t.strip() for t in line[8:].split(',') if t.strip()]
        elif line.startswith('require_all:'):
            result['require_all'] = line[12:].strip().lower() == 'true'

    return result


# ============================================================================
# Tag Query
# ============================================================================

def _categorize_tag(tag: str) -> str:
    """Categorize a tag into Emotions, Outfits, or Other.

    Args:
        tag: The tag string to categorize.

    Returns:
        Category name: 'emotions', 'outfits', or 'other'.
    """
    tag_lower = tag.lower()
    if tag_lower in VALID_EMOTIONS:
        return 'emotions'
    if tag_lower in KNOWN_OUTFIT_TAGS:
        return 'outfits'
    return 'other'


def list_tags(config_path: Path | None = None) -> dict[str, dict[str, int]]:
    """List all unique tags with counts, organized by category.

    Scans all registered images and counts tag frequency, then categorizes
    each tag into Emotions, Outfits, or Other.

    Args:
        config_path: Path to config file (auto-detects if None).

    Returns:
        Dictionary with category keys ('emotions', 'outfits', 'other'),
        each mapping to a dict of {tag: count} sorted by count descending.
    """
    config = load_config(config_path)
    images = config.get('avatar', {}).get('images', [])

    # Count all tags across all images
    tag_counts: dict[str, int] = {}
    for img in images:
        for tag in img.get('tags', []):
            tag_lower = tag.lower()
            tag_counts[tag_lower] = tag_counts.get(tag_lower, 0) + 1

    # Categorize tags
    categories: dict[str, dict[str, int]] = {
        'emotions': {},
        'outfits': {},
        'other': {},
    }

    for tag, count in tag_counts.items():
        category = _categorize_tag(tag)
        categories[category][tag] = count

    # Sort each category by count descending
    for category in categories:
        categories[category] = dict(
            sorted(categories[category].items(), key=lambda x: x[1], reverse=True)
        )

    return categories


def print_tag_summary(config_path: Path | None = None) -> None:
    """Print formatted tag summary to stdout.

    Shows all unique tags sorted by frequency, organized by category
    (Emotions, Outfits, Other) with counts.

    Args:
        config_path: Path to config file (auto-detects if None).
    """
    config = load_config(config_path)
    images = config.get('avatar', {}).get('images', [])
    categories = list_tags(config_path)

    total_images = len(images)
    total_tags = sum(len(tags) for tags in categories.values())

    print('\n=== AVATAR TAGS ===\n')

    for label, key in [('Emotions', 'emotions'), ('Outfits', 'outfits'), ('Other', 'other')]:
        tags = categories[key]
        if not tags:
            continue

        # Count images that have at least one tag in this category
        category_image_count = 0
        for img in images:
            img_tags = {t.lower() for t in img.get('tags', [])}
            if img_tags & set(tags.keys()):
                category_image_count += 1

        tag_count = len(tags)
        header = f'{label} ({tag_count} tags, {category_image_count} images):'
        print(header)

        # Format tags as comma-separated list with counts
        tag_parts = [f'  {tag} ({count})' for tag, count in tags.items()]
        print('\n'.join(tag_parts))
        print()

    print(f'Total: {total_tags} unique tags across {total_images} images')
    print()


# ============================================================================
# CLI Entry Point
# ============================================================================

def main() -> None:
    """CLI entry point for avatar tag management."""
    parser = argparse.ArgumentParser(
        description='Manage PyAgentVox avatar images with tags',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Scan for unregistered images:
    python -m pyagentvox.avatar_tags scan

  Register a new image:
    python -m pyagentvox.avatar_tags add path/to/cheerful.png --tags cheerful,dress,wave

  Update image tags:
    python -m pyagentvox.avatar_tags update path/to/cheerful.png --tags cheerful,dress,peace-sign

  Remove image:
    python -m pyagentvox.avatar_tags remove path/to/old-image.png

  List all images:
    python -m pyagentvox.avatar_tags list

  List images with specific tag:
    python -m pyagentvox.avatar_tags list --tag cheerful

  Show all tags with counts:
    python -m pyagentvox.avatar_tags tags

  Show current filters for running instance:
    python -m pyagentvox.avatar_tags current --pid 12345

  Apply runtime filters (requires running PyAgentVox PID):
    python -m pyagentvox.avatar_tags filter --pid 12345 --include casual,summer
    python -m pyagentvox.avatar_tags filter --pid 12345 --exclude formal
    python -m pyagentvox.avatar_tags filter --pid 12345 --reset
        """
    )

    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--config', type=str, help='Path to pyagentvox.yaml')

    subparsers = parser.add_subparsers(dest='command', required=True)

    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan for unregistered images')
    scan_parser.add_argument('--dir', type=str, help='Avatar directory to scan')

    # Add command
    add_parser = subparsers.add_parser('add', help='Register new image')
    add_parser.add_argument('path', type=str, help='Path to image file')
    add_parser.add_argument('--tags', type=str, required=True,
                           help='Comma-separated tags (must include emotion tag)')

    # Update command
    update_parser = subparsers.add_parser('update', help='Update image tags')
    update_parser.add_argument('path', type=str, help='Path to image file')
    update_parser.add_argument('--tags', type=str, required=True,
                              help='Comma-separated tags (must include emotion tag)')

    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove image from registry')
    remove_parser.add_argument('path', type=str, help='Path to image file')

    # List command
    list_parser = subparsers.add_parser('list', help='List registered images')
    list_parser.add_argument('--tag', type=str, help='Filter by tag')

    # Filter command
    filter_parser = subparsers.add_parser('filter', help='Apply runtime tag filters')
    filter_parser.add_argument('--pid', type=int, required=True,
                              help='Process ID of running PyAgentVox instance')
    filter_parser.add_argument('--include', type=str,
                              help='Comma-separated tags to include')
    filter_parser.add_argument('--exclude', type=str,
                              help='Comma-separated tags to exclude')
    filter_parser.add_argument('--require-all', action='store_true',
                              help='Require ALL include tags (default: ANY)')
    filter_parser.add_argument('--reset', action='store_true',
                              help='Reset all filters')

    # Tags command
    subparsers.add_parser('tags', help='Show all tags with counts by category')

    # Current filters command
    current_parser = subparsers.add_parser('current', help='Show current filter state')
    current_parser.add_argument('--pid', type=int, required=True,
                                help='Process ID of running PyAgentVox instance')

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(message)s',
    )

    config_path = Path(args.config) if args.config else None

    try:
        # Execute command
        if args.command == 'scan':
            avatar_dir = Path(args.dir).expanduser() if args.dir else None
            unregistered = scan_unregistered_images(avatar_dir, config_path)

            if unregistered:
                print(f'\n📷 Found {len(unregistered)} unregistered images:\n')
                for img_path in unregistered:
                    print(f'  {img_path}')
                print('\nRegister with: python -m pyagentvox.avatar_tags add <path> --tags <tags>\n')
            else:
                print('\n✅ All images are registered!\n')

        elif args.command == 'add':
            tags = [t.strip() for t in args.tags.split(',')]
            add_image_to_config(Path(args.path), tags, config_path)
            print(f'✅ Registered: {args.path}')
            print(f'   Tags: {tags}')

        elif args.command == 'update':
            tags = [t.strip() for t in args.tags.split(',')]
            update_image_tags(Path(args.path), tags, config_path)
            print(f'✅ Updated: {args.path}')
            print(f'   Tags: {tags}')

        elif args.command == 'remove':
            remove_image_from_config(Path(args.path), config_path)
            print(f'✅ Removed: {args.path}')

        elif args.command == 'list':
            images = list_images(args.tag, config_path)

            if images:
                tag_filter_str = f' with tag "{args.tag}"' if args.tag else ''
                print(f'\n📋 Registered images{tag_filter_str}:\n')
                for img in images:
                    print(f'  {img["path"]}')
                    print(f'    Tags: {", ".join(img["tags"])}')
                    print()
            else:
                print('\n❌ No images found\n')

        elif args.command == 'filter':
            include = [t.strip() for t in args.include.split(',')] if args.include else None
            exclude = [t.strip() for t in args.exclude.split(',')] if args.exclude else None

            apply_filters(
                args.pid,
                include_tags=include,
                exclude_tags=exclude,
                require_all=args.require_all,
                reset=args.reset
            )

            if args.reset:
                print('✅ Reset all filters')
            else:
                print('✅ Applied filters:')
                if include:
                    print(f'   Include: {include}')
                if exclude:
                    print(f'   Exclude: {exclude}')
                if args.require_all:
                    print('   Require all include tags: YES')

        elif args.command == 'tags':
            print_tag_summary(config_path)

        elif args.command == 'current':
            filters = read_current_filters(args.pid)
            include = filters.get('include', [])
            exclude = filters.get('exclude', [])
            require_all = filters.get('require_all', False)

            if not include and not exclude:
                print('\n📋 No active filters (showing all images)\n')
            else:
                print('\n📋 Current avatar filters:\n')
                if include:
                    mode = 'ALL' if require_all else 'ANY'
                    print(f'  Include ({mode}): {", ".join(include)}')
                if exclude:
                    print(f'  Exclude: {", ".join(exclude)}')
                print()

    except Exception as e:
        print(f'\n❌ Error: {e}\n', file=sys.stderr)
        if args.debug:
            raise
        sys.exit(1)


if __name__ == '__main__':
    main()
