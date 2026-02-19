"""Batch background removal for Luna avatar images.

Processes a slice of sorted images using rembg, enabling parallel batch execution.
Each batch operates on a non-overlapping index range, making it safe to run multiple
instances simultaneously.

Usage:
    # Process all images sequentially
    python remove_backgrounds_batch.py

    # Process images 0-74 (first batch)
    python remove_backgrounds_batch.py --start-index 0 --count 75 --batch-id batch1

    # Process images 75-149 (second batch)
    python remove_backgrounds_batch.py --start-index 75 --count 75 --batch-id batch2

    # Process images 150-224 (third batch)
    python remove_backgrounds_batch.py --start-index 150 --count 75 --batch-id batch3

Author: Jake
"""

import argparse
import sys
import time
from pathlib import Path

from PIL import Image
from rembg import remove

__all__ = ['discover_images', 'process_image', 'run_batch']

AVATAR_DIR = Path.home() / '.claude' / 'luna'
SUPPORTED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp'}


def discover_images(avatar_dir: Path) -> list[Path]:
    """Find all image files in the avatar directory, sorted by name.

    Performs a recursive search for supported image formats and returns
    them in a stable sorted order so that index-based slicing produces
    consistent, non-overlapping batches across parallel runs.

    Args:
        avatar_dir: Root directory to search for images.

    Returns:
        Sorted list of image file paths.
    """
    images: list[Path] = []
    for path in avatar_dir.rglob('*'):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            images.append(path)
    return sorted(images)


def process_image(image_path: Path) -> bool:
    """Remove background from a single image and save as PNG.

    Reads the image, removes its background via rembg, and writes the
    result as a PNG with transparency. If the original file was not a
    PNG, the original is deleted after successful conversion.

    Args:
        image_path: Path to the image file to process.

    Returns:
        True if background removal succeeded, False otherwise.
    """
    try:
        with open(image_path, 'rb') as f:
            input_data = f.read()

        output_data = remove(input_data)

        output_path = image_path.with_suffix('.png')
        with open(output_path, 'wb') as f:
            f.write(output_data)

        # Clean up original if it was converted from a non-PNG format
        if image_path.suffix.lower() != '.png':
            image_path.unlink()

        return True

    except Exception as e:
        print(f'  ERROR: {e}', flush=True)
        return False


def run_batch(
    avatar_dir: Path,
    start_index: int = 0,
    count: int | None = None,
    batch_id: str = 'default',
) -> tuple[int, int, int]:
    """Process a batch of images with background removal.

    Discovers all images, slices to the requested range, and processes
    each one. Progress is printed to stdout for monitoring.

    Args:
        avatar_dir: Root directory containing avatar images.
        start_index: Zero-based index of the first image to process.
        count: Number of images to process. None means all remaining.
        batch_id: Identifier for this batch, used in log output.

    Returns:
        Tuple of (success_count, failure_count, skipped_count).
    """
    all_images = discover_images(avatar_dir)
    total_discovered = len(all_images)

    if total_discovered == 0:
        print(f'[{batch_id}] No images found in {avatar_dir}', flush=True)
        return 0, 0, 0

    # Clamp start_index to valid range
    if start_index >= total_discovered:
        print(
            f'[{batch_id}] Start index {start_index} exceeds total image count {total_discovered}. Nothing to process.',
            flush=True,
        )
        return 0, 0, 0

    # Slice the batch
    end_index = total_discovered if count is None else min(start_index + count, total_discovered)
    batch_images = all_images[start_index:end_index]
    batch_size = len(batch_images)

    print(f'[{batch_id}] Background Removal Batch', flush=True)
    print(f'[{batch_id}] {"=" * 56}', flush=True)
    print(f'[{batch_id}] Total images discovered: {total_discovered}', flush=True)
    print(f'[{batch_id}] Processing range: [{start_index}, {end_index}) ({batch_size} images)', flush=True)
    print(f'[{batch_id}] {"=" * 56}', flush=True)

    success_count = 0
    failure_count = 0
    batch_start_time = time.monotonic()

    for i, image_path in enumerate(batch_images):
        global_index = start_index + i
        relative_path = image_path.relative_to(avatar_dir)
        print(f'[{batch_id}] [{i + 1}/{batch_size}] (#{global_index}) {relative_path} ... ', end='', flush=True)

        image_start_time = time.monotonic()
        if process_image(image_path):
            elapsed = time.monotonic() - image_start_time
            print(f'OK ({elapsed:.1f}s)', flush=True)
            success_count += 1
        else:
            failure_count += 1

    total_elapsed = time.monotonic() - batch_start_time
    skipped_count = batch_size - success_count - failure_count

    # Summary
    print(f'[{batch_id}] {"=" * 56}', flush=True)
    print(f'[{batch_id}] Batch complete in {total_elapsed:.1f}s', flush=True)
    print(f'[{batch_id}]   Succeeded: {success_count}', flush=True)
    if failure_count > 0:
        print(f'[{batch_id}]   Failed:    {failure_count}', flush=True)
    if skipped_count > 0:
        print(f'[{batch_id}]   Skipped:   {skipped_count}', flush=True)
    print(f'[{batch_id}] {"=" * 56}', flush=True)

    return success_count, failure_count, skipped_count


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list to parse. None uses sys.argv.

    Returns:
        Parsed argument namespace.
    """
    parser = argparse.ArgumentParser(
        description='Batch background removal for Luna avatar images.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Examples:\n'
            '  python remove_backgrounds_batch.py\n'
            '  python remove_backgrounds_batch.py --start-index 0 --count 75 --batch-id batch1\n'
            '  python remove_backgrounds_batch.py --start-index 75 --count 75 --batch-id batch2\n'
            '  python remove_backgrounds_batch.py --start-index 150 --count 75 --batch-id batch3'
        ),
    )
    parser.add_argument(
        '--start-index',
        type=int,
        default=0,
        help='Zero-based index of the first image to process (default: 0)',
    )
    parser.add_argument(
        '--count',
        type=int,
        default=None,
        help='Number of images to process (default: all remaining from start-index)',
    )
    parser.add_argument(
        '--batch-id',
        type=str,
        default='default',
        help='Identifier for this batch, shown in log output (default: "default")',
    )
    parser.add_argument(
        '--avatar-dir',
        type=Path,
        default=AVATAR_DIR,
        help=f'Directory containing avatar images (default: {AVATAR_DIR})',
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point for batch background removal.

    Args:
        argv: Argument list to parse. None uses sys.argv.

    Returns:
        Exit code: 0 if all succeeded, 1 if any failures occurred.
    """
    args = parse_args(argv)

    if not args.avatar_dir.exists():
        print(f'Avatar directory not found: {args.avatar_dir}', flush=True)
        return 1

    if args.start_index < 0:
        print(f'Start index must be non-negative, got {args.start_index}', flush=True)
        return 1

    if args.count is not None and args.count <= 0:
        print(f'Count must be positive, got {args.count}', flush=True)
        return 1

    success, failures, _ = run_batch(
        avatar_dir=args.avatar_dir,
        start_index=args.start_index,
        count=args.count,
        batch_id=args.batch_id,
    )

    if failures > 0:
        return 1
    if success == 0:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
