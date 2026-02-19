"""Consolidate batch avatar tag results into pyagentvox.yaml config.

This script:
1. Reads all 4 batch result files
2. Merges them into a single image list
3. Updates pyagentvox.yaml with all registered images
4. Generates a summary report

Author:
    Jake Meador <jameador13@gmail.com>
"""

import sys
from pathlib import Path
from collections import Counter

import yaml


def load_batch_results(tasks_dir: Path) -> list[dict]:
    """Load and merge all batch result files.

    Args:
        tasks_dir: Path to image-tagging tasks directory

    Returns:
        List of all image entries from all batches
    """
    all_images = []

    for batch_num in range(1, 5):
        batch_file = tasks_dir / f'batch{batch_num}_results.txt'

        if not batch_file.exists():
            print(f'Warning: {batch_file} not found, skipping')
            continue

        print(f'Loading {batch_file.name}...')

        with open(batch_file, 'r', encoding='utf-8') as f:
            batch_data = yaml.safe_load(f)

        if 'images' in batch_data:
            batch_images = batch_data['images']
            print(f'  Found {len(batch_images)} images')
            all_images.extend(batch_images)
        else:
            print(f'  Warning: No images key found in {batch_file.name}')

    return all_images


def update_config(config_path: Path, images: list[dict]) -> None:
    """Update pyagentvox.yaml with image registry.

    Args:
        config_path: Path to pyagentvox.yaml
        images: List of image entries to add
    """
    print(f'\nUpdating {config_path}...')

    # Load existing config
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}

    # Ensure avatar section exists
    if 'avatar' not in config:
        config['avatar'] = {}

    # Replace images list
    config['avatar']['images'] = images

    # Write back
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, sort_keys=False, allow_unicode=True)

    print(f'Updated config with {len(images)} images')


def generate_summary(images: list[dict]) -> None:
    """Generate summary report of registered images.

    Args:
        images: List of all image entries
    """
    print('\n' + '=' * 70)
    print('AVATAR TAG SUMMARY')
    print('=' * 70)

    # Total count
    print(f'\nTotal images registered: {len(images)}')

    # Emotion tag distribution
    print('\nEmotion Tags:')
    emotion_tags = Counter()
    for img in images:
        for tag in img.get('tags', []):
            if tag in ['cheerful', 'excited', 'calm', 'focused', 'warm',
                      'empathetic', 'neutral', 'playful', 'surprised',
                      'curious', 'determined']:
                emotion_tags[tag] += 1

    for emotion, count in emotion_tags.most_common():
        print(f'  {emotion:12s}: {count:3d} images')

    # Outfit tag distribution (top 10)
    print('\nTop Outfit Tags:')
    outfit_tags = Counter()
    for img in images:
        for tag in img.get('tags', []):
            if tag in ['dress', 'daisy-dukes', 'hoodie', 'casual', 'formal',
                      'costume', 'tank-top', 'pajamas', 'apron']:
                outfit_tags[tag] += 1

    for outfit, count in outfit_tags.most_common(10):
        print(f'  {outfit:12s}: {count:3d} images')

    # Pose tag distribution (top 15)
    print('\nTop Pose Tags:')
    pose_tags = Counter()
    for img in images:
        for tag in img.get('tags', []):
            # Skip emotion and outfit tags
            if tag not in ['cheerful', 'excited', 'calm', 'focused', 'warm',
                          'empathetic', 'neutral', 'playful', 'surprised',
                          'curious', 'determined', 'dress', 'daisy-dukes',
                          'hoodie', 'casual', 'formal', 'costume', 'tank-top',
                          'pajamas', 'apron', 'summer', 'coding', 'celebration',
                          'coffee', 'laptop', 'beach', 'halloween', 'winter']:
                pose_tags[tag] += 1

    for pose, count in pose_tags.most_common(15):
        print(f'  {pose:16s}: {count:3d} images')

    print('\n' + '=' * 70)
    print('Avatar tag system fully configured!')
    print('=' * 70)


def main():
    """Main consolidation workflow."""
    # Paths
    tasks_dir = Path.home() / '.claude' / 'tasks' / 'image-tagging'
    config_path = Path('C:/projects/pyprojects/pyagentvox/pyagentvox.yaml')

    print('=' * 70)
    print('Avatar Tag Consolidation')
    print('=' * 70)

    # Load all batch results
    print('\nLoading batch results...')
    all_images = load_batch_results(tasks_dir)

    if not all_images:
        print('ERROR: No images found in batch results!')
        sys.exit(1)

    # Sort by path for consistency
    all_images.sort(key=lambda img: img['path'])

    # Update config
    update_config(config_path, all_images)

    # Generate summary
    generate_summary(all_images)

    print(f'\nConfig saved to: {config_path}')
    print('\nAll done! Avatar tag system ready to use!')


if __name__ == '__main__':
    main()
