"""Tests for avatar tags management functionality.

Tests image scanning, registration, tag updates, and filter control.

Author:
    Jake Meador <jameador13@gmail.com>
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from pyagentvox.avatar_tags import (
    add_image_to_config,
    apply_filters,
    list_images,
    load_config,
    remove_image_from_config,
    save_config,
    scan_unregistered_images,
    update_image_tags,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_config():
    """Create temporary config file with avatar section."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / 'pyagentvox.yaml'
        avatar_dir = Path(tmpdir) / 'avatars'
        avatar_dir.mkdir()

        config = {
            'avatar': {
                'directory': str(avatar_dir),
                'default_size': 300,
                'cycle_interval': 4000,
                'filters': {
                    'include_tags': [],
                    'exclude_tags': [],
                    'require_all_include': False,
                },
                'images': [],
            }
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)

        yield config_path, avatar_dir


# ============================================================================
# Config Loading/Saving Tests
# ============================================================================

def test_load_config(temp_config):
    """Test loading config from file."""
    config_path, _ = temp_config
    config = load_config(config_path)

    assert 'avatar' in config
    assert 'directory' in config['avatar']
    assert 'images' in config['avatar']


def test_save_config(temp_config):
    """Test saving config to file."""
    config_path, _ = temp_config
    config = load_config(config_path)

    # Modify config
    config['avatar']['default_size'] = 400

    # Save
    save_config(config, config_path)

    # Reload and verify
    reloaded = load_config(config_path)
    assert reloaded['avatar']['default_size'] == 400


def test_load_config_not_found():
    """Test loading config when file doesn't exist."""
    with pytest.raises(FileNotFoundError):
        load_config(Path('/nonexistent/config.yaml'))


# ============================================================================
# Image Scanning Tests
# ============================================================================

def test_scan_unregistered_images_empty_dir(temp_config):
    """Test scanning directory with no images."""
    config_path, avatar_dir = temp_config
    unregistered = scan_unregistered_images(avatar_dir, config_path)

    assert len(unregistered) == 0


def test_scan_unregistered_images_all_unregistered(temp_config):
    """Test scanning directory with unregistered images."""
    config_path, avatar_dir = temp_config

    # Create test images
    (avatar_dir / 'cheerful-1.png').touch()
    (avatar_dir / 'cheerful-2.png').touch()
    (avatar_dir / 'excited.png').touch()

    unregistered = scan_unregistered_images(avatar_dir, config_path)

    assert len(unregistered) == 3
    assert all(img.suffix == '.png' for img in unregistered)


def test_scan_unregistered_images_some_registered(temp_config):
    """Test scanning with some images already registered."""
    config_path, avatar_dir = temp_config

    # Create test images
    img1 = avatar_dir / 'cheerful-1.png'
    img2 = avatar_dir / 'cheerful-2.png'
    img3 = avatar_dir / 'excited.png'

    img1.touch()
    img2.touch()
    img3.touch()

    # Register one image
    config = load_config(config_path)
    config['avatar']['images'].append({
        'path': 'cheerful-1.png',
        'tags': ['cheerful', 'dress'],
    })
    save_config(config, config_path)

    # Scan
    unregistered = scan_unregistered_images(avatar_dir, config_path)

    assert len(unregistered) == 2
    assert img1 not in unregistered
    assert img2 in unregistered
    assert img3 in unregistered


def test_scan_unregistered_images_subdirectories(temp_config):
    """Test scanning with images in subdirectories."""
    config_path, avatar_dir = temp_config

    # Create subdirectories with images
    (avatar_dir / 'cheerful').mkdir()
    (avatar_dir / 'excited').mkdir()

    (avatar_dir / 'cheerful' / 'variant1.png').touch()
    (avatar_dir / 'cheerful' / 'variant2.png').touch()
    (avatar_dir / 'excited' / 'variant1.png').touch()

    unregistered = scan_unregistered_images(avatar_dir, config_path)

    assert len(unregistered) == 3


def test_scan_unregistered_images_multiple_formats(temp_config):
    """Test scanning with multiple image formats."""
    config_path, avatar_dir = temp_config

    (avatar_dir / 'image1.png').touch()
    (avatar_dir / 'image2.jpg').touch()
    (avatar_dir / 'image3.jpeg').touch()
    (avatar_dir / 'image4.webp').touch()
    (avatar_dir / 'not-image.txt').touch()  # Should be ignored

    unregistered = scan_unregistered_images(avatar_dir, config_path)

    assert len(unregistered) == 4
    assert all(img.suffix in ['.png', '.jpg', '.jpeg', '.webp'] for img in unregistered)


# ============================================================================
# Image Registration Tests
# ============================================================================

def test_add_image_to_config(temp_config):
    """Test adding new image to config."""
    config_path, avatar_dir = temp_config
    img_path = avatar_dir / 'cheerful.png'
    img_path.touch()

    add_image_to_config(img_path, ['cheerful', 'dress', 'wave'], config_path)

    config = load_config(config_path)
    assert len(config['avatar']['images']) == 1
    assert config['avatar']['images'][0]['path'] == 'cheerful.png'
    assert config['avatar']['images'][0]['tags'] == ['cheerful', 'dress', 'wave']


def test_add_image_missing_emotion_tag(temp_config):
    """Test that adding image without emotion tag raises error."""
    config_path, avatar_dir = temp_config
    img_path = avatar_dir / 'test.png'
    img_path.touch()

    with pytest.raises(ValueError, match='emotion or control tag'):
        add_image_to_config(img_path, ['dress', 'wave'], config_path)


def test_add_image_already_registered(temp_config):
    """Test that adding duplicate image raises error."""
    config_path, avatar_dir = temp_config
    img_path = avatar_dir / 'cheerful.png'
    img_path.touch()

    # Add once
    add_image_to_config(img_path, ['cheerful', 'dress'], config_path)

    # Try to add again
    with pytest.raises(ValueError, match='already registered'):
        add_image_to_config(img_path, ['cheerful', 'hoodie'], config_path)


def test_add_image_relative_path(temp_config):
    """Test that image path is made relative to avatar directory."""
    config_path, avatar_dir = temp_config
    img_path = avatar_dir / 'subdir' / 'cheerful.png'
    img_path.parent.mkdir()
    img_path.touch()

    add_image_to_config(img_path, ['cheerful', 'dress'], config_path)

    config = load_config(config_path)
    # Path should be relative
    assert config['avatar']['images'][0]['path'] == 'subdir/cheerful.png'


def test_add_image_absolute_path_outside_avatar_dir(temp_config):
    """Test adding image with absolute path outside avatar directory."""
    config_path, _ = temp_config

    with tempfile.TemporaryDirectory() as other_dir:
        img_path = Path(other_dir) / 'cheerful.png'
        img_path.touch()

        add_image_to_config(img_path, ['cheerful', 'dress'], config_path)

        config = load_config(config_path)
        # Path should be absolute since it's outside avatar dir
        assert Path(config['avatar']['images'][0]['path']).is_absolute()


# ============================================================================
# Image Update Tests
# ============================================================================

def test_update_image_tags(temp_config):
    """Test updating tags for existing image."""
    config_path, avatar_dir = temp_config
    img_path = avatar_dir / 'cheerful.png'
    img_path.touch()

    # Add image
    add_image_to_config(img_path, ['cheerful', 'dress'], config_path)

    # Update tags
    update_image_tags(img_path, ['cheerful', 'hoodie', 'coding'], config_path)

    config = load_config(config_path)
    assert config['avatar']['images'][0]['tags'] == ['cheerful', 'hoodie', 'coding']


def test_update_image_tags_missing_emotion(temp_config):
    """Test that updating with no emotion tag raises error."""
    config_path, avatar_dir = temp_config
    img_path = avatar_dir / 'cheerful.png'
    img_path.touch()

    add_image_to_config(img_path, ['cheerful', 'dress'], config_path)

    with pytest.raises(ValueError, match='emotion or control tag'):
        update_image_tags(img_path, ['dress', 'wave'], config_path)


def test_update_image_tags_not_found(temp_config):
    """Test updating tags for non-existent image."""
    config_path, avatar_dir = temp_config
    img_path = avatar_dir / 'nonexistent.png'

    with pytest.raises(ValueError, match='not found'):
        update_image_tags(img_path, ['cheerful', 'dress'], config_path)


# ============================================================================
# Image Removal Tests
# ============================================================================

def test_remove_image_from_config(temp_config):
    """Test removing image from config."""
    config_path, avatar_dir = temp_config
    img_path = avatar_dir / 'cheerful.png'
    img_path.touch()

    # Add image
    add_image_to_config(img_path, ['cheerful', 'dress'], config_path)

    # Remove
    remove_image_from_config(img_path, config_path)

    config = load_config(config_path)
    assert len(config['avatar']['images']) == 0


def test_remove_image_not_found(temp_config):
    """Test removing non-existent image."""
    config_path, avatar_dir = temp_config
    img_path = avatar_dir / 'nonexistent.png'

    with pytest.raises(ValueError, match='not found'):
        remove_image_from_config(img_path, config_path)


def test_remove_image_leaves_others(temp_config):
    """Test that removing one image doesn't affect others."""
    config_path, avatar_dir = temp_config

    img1 = avatar_dir / 'cheerful.png'
    img2 = avatar_dir / 'excited.png'
    img3 = avatar_dir / 'calm.png'

    img1.touch()
    img2.touch()
    img3.touch()

    # Add three images
    add_image_to_config(img1, ['cheerful', 'dress'], config_path)
    add_image_to_config(img2, ['excited', 'hoodie'], config_path)
    add_image_to_config(img3, ['calm', 'formal'], config_path)

    # Remove middle one
    remove_image_from_config(img2, config_path)

    config = load_config(config_path)
    assert len(config['avatar']['images']) == 2
    paths = [img['path'] for img in config['avatar']['images']]
    assert 'cheerful.png' in paths
    assert 'calm.png' in paths
    assert 'excited.png' not in paths


# ============================================================================
# Image Listing Tests
# ============================================================================

def test_list_images_empty(temp_config):
    """Test listing images when none are registered."""
    config_path, _ = temp_config
    images = list_images(config_path=config_path)

    assert len(images) == 0


def test_list_images_all(temp_config):
    """Test listing all registered images."""
    config_path, avatar_dir = temp_config

    # Add multiple images
    for i, emotion in enumerate(['cheerful', 'excited', 'calm'], 1):
        img_path = avatar_dir / f'{emotion}.png'
        img_path.touch()
        add_image_to_config(img_path, [emotion, 'dress'], config_path)

    images = list_images(config_path=config_path)

    assert len(images) == 3


def test_list_images_filtered_by_tag(temp_config):
    """Test listing images filtered by specific tag."""
    config_path, avatar_dir = temp_config

    # Add images with different tags
    img1 = avatar_dir / 'cheerful-dress.png'
    img2 = avatar_dir / 'cheerful-hoodie.png'
    img3 = avatar_dir / 'excited-dress.png'

    img1.touch()
    img2.touch()
    img3.touch()

    add_image_to_config(img1, ['cheerful', 'dress'], config_path)
    add_image_to_config(img2, ['cheerful', 'hoodie'], config_path)
    add_image_to_config(img3, ['excited', 'dress'], config_path)

    # List only cheerful images
    images = list_images(tag_filter='cheerful', config_path=config_path)

    assert len(images) == 2
    assert all('cheerful' in img['tags'] for img in images)


def test_list_images_case_insensitive_filter(temp_config):
    """Test that tag filtering is case-insensitive."""
    config_path, avatar_dir = temp_config

    img_path = avatar_dir / 'cheerful.png'
    img_path.touch()
    add_image_to_config(img_path, ['cheerful', 'dress'], config_path)

    images = list_images(tag_filter='CHEERFUL', config_path=config_path)

    assert len(images) == 1


# ============================================================================
# Runtime Filter Tests
# ============================================================================

def test_apply_filters_include():
    """Test applying include filters via IPC file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Mock PID
        pid = 12345

        apply_filters(pid, include_tags=['casual', 'summer'])

        filter_file = Path(tmpdir).parent / f'agent_avatar_filter_{pid}.txt'

        # Note: The actual file is written to system temp, so we can't easily test
        # the file contents without mocking tempfile.gettempdir()
        # This test verifies the function runs without error


def test_apply_filters_exclude():
    """Test applying exclude filters via IPC file."""
    pid = 12345
    apply_filters(pid, exclude_tags=['formal', 'control'])


def test_apply_filters_reset():
    """Test resetting all filters via IPC file."""
    pid = 12345
    apply_filters(pid, reset=True)


def test_apply_filters_combined():
    """Test applying combined filters via IPC file."""
    pid = 12345
    apply_filters(
        pid,
        include_tags=['cheerful'],
        exclude_tags=['formal'],
        require_all=True
    )


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_workflow(temp_config):
    """Test complete workflow: scan, add, update, list, remove."""
    config_path, avatar_dir = temp_config

    # Create test images
    img1 = avatar_dir / 'cheerful.png'
    img2 = avatar_dir / 'excited.png'
    img1.touch()
    img2.touch()

    # 1. Scan for unregistered
    unregistered = scan_unregistered_images(avatar_dir, config_path)
    assert len(unregistered) == 2

    # 2. Register images
    add_image_to_config(img1, ['cheerful', 'dress', 'wave'], config_path)
    add_image_to_config(img2, ['excited', 'hoodie', 'typing'], config_path)

    # 3. Verify scan shows no unregistered
    unregistered = scan_unregistered_images(avatar_dir, config_path)
    assert len(unregistered) == 0

    # 4. List all images
    images = list_images(config_path=config_path)
    assert len(images) == 2

    # 5. List filtered by tag
    cheerful_images = list_images(tag_filter='cheerful', config_path=config_path)
    assert len(cheerful_images) == 1

    # 6. Update tags
    update_image_tags(img1, ['cheerful', 'dress', 'peace-sign'], config_path)

    # 7. Verify update
    images = list_images(config_path=config_path)
    cheerful_img = next(img for img in images if 'cheerful.png' in img['path'])
    assert 'peace-sign' in cheerful_img['tags']
    assert 'wave' not in cheerful_img['tags']

    # 8. Remove one image
    remove_image_from_config(img2, config_path)

    # 9. Verify removal
    images = list_images(config_path=config_path)
    assert len(images) == 1
    assert 'cheerful.png' in images[0]['path']
