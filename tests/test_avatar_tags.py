"""Tests for avatar tag system functionality.

Tests tag filtering, tag similarity calculation, image registry loading,
and runtime filter control.

Author:
    Jake Meador <jameador13@gmail.com>
"""

import tempfile
from pathlib import Path

import pytest

from pyagentvox.avatar_widget import (
    ImageEntry,
    calculate_tag_similarity,
    filter_images_by_tags,
    load_image_registry,
)


# ============================================================================
# Tag Similarity Tests
# ============================================================================

def test_calculate_tag_similarity_identical():
    """Test tag similarity for identical tag sets."""
    tags1 = {'cheerful', 'dress', 'wave'}
    tags2 = {'cheerful', 'dress', 'wave'}
    assert calculate_tag_similarity(tags1, tags2) == 1.0


def test_calculate_tag_similarity_no_overlap():
    """Test tag similarity for completely different tag sets."""
    tags1 = {'cheerful', 'dress', 'wave'}
    tags2 = {'excited', 'hoodie', 'typing'}
    assert calculate_tag_similarity(tags1, tags2) == 0.0


def test_calculate_tag_similarity_partial():
    """Test tag similarity for partially overlapping tag sets."""
    tags1 = {'cheerful', 'dress', 'wave'}
    tags2 = {'cheerful', 'hoodie', 'peace-sign'}
    # Intersection: 1 (cheerful), Union: 5 (cheerful, dress, wave, hoodie, peace-sign)
    assert calculate_tag_similarity(tags1, tags2) == pytest.approx(0.2)


def test_calculate_tag_similarity_subset():
    """Test tag similarity when one set is a subset of another."""
    tags1 = {'cheerful', 'dress'}
    tags2 = {'cheerful', 'dress', 'wave', 'friendly'}
    # Intersection: 2, Union: 4
    assert calculate_tag_similarity(tags1, tags2) == 0.5


def test_calculate_tag_similarity_empty():
    """Test tag similarity for empty tag sets."""
    assert calculate_tag_similarity(set(), set()) == 1.0
    assert calculate_tag_similarity({'cheerful'}, set()) == 0.0
    assert calculate_tag_similarity(set(), {'cheerful'}) == 0.0


# ============================================================================
# Tag Filtering Tests
# ============================================================================

@pytest.fixture
def sample_images():
    """Create sample ImageEntry objects for testing."""
    return [
        ImageEntry(Path('cheerful-dress.png'), ['cheerful', 'cream-dress', 'wave']),
        ImageEntry(Path('cheerful-casual.png'), ['cheerful', 'daisy-dukes', 'casual', 'summer']),
        ImageEntry(Path('excited-dress.png'), ['excited', 'cream-dress', 'victory']),
        ImageEntry(Path('focused-hoodie.png'), ['focused', 'hoodie', 'coding', 'typing']),
        ImageEntry(Path('calm-formal.png'), ['calm', 'ball-gown', 'formal']),
        ImageEntry(Path('control-pleading.png'), ['empathetic', 'control', 'pleading']),
    ]


def test_filter_no_filters(sample_images):
    """Test filtering with no filters (should return all images)."""
    result = filter_images_by_tags(sample_images, [], [], False)
    assert len(result) == 6
    assert result == sample_images


def test_filter_include_single_tag(sample_images):
    """Test filtering with single include tag."""
    result = filter_images_by_tags(sample_images, ['cheerful'], [], False)
    assert len(result) == 2
    assert all('cheerful' in img.tags for img in result)


def test_filter_include_multiple_tags_any(sample_images):
    """Test filtering with multiple include tags (ANY match)."""
    result = filter_images_by_tags(sample_images, ['cheerful', 'excited'], [], False)
    assert len(result) == 3
    assert all(any(tag in img.tags for tag in ['cheerful', 'excited']) for img in result)


def test_filter_include_multiple_tags_all(sample_images):
    """Test filtering with multiple include tags (ALL required)."""
    result = filter_images_by_tags(
        sample_images,
        ['cheerful', 'casual'],
        [],
        require_all_include=True
    )
    assert len(result) == 1
    assert result[0].path.name == 'cheerful-casual.png'


def test_filter_exclude_single_tag(sample_images):
    """Test filtering with single exclude tag."""
    result = filter_images_by_tags(sample_images, [], ['control'], False)
    assert len(result) == 5
    assert all('control' not in img.tags for img in result)


def test_filter_exclude_multiple_tags(sample_images):
    """Test filtering with multiple exclude tags."""
    result = filter_images_by_tags(sample_images, [], ['formal', 'control'], False)
    assert len(result) == 4
    assert all(not any(tag in img.tags for tag in ['formal', 'control']) for img in result)


def test_filter_include_and_exclude(sample_images):
    """Test filtering with both include and exclude tags."""
    result = filter_images_by_tags(
        sample_images,
        ['cheerful'],
        ['daisy-dukes'],
        False
    )
    assert len(result) == 1
    assert result[0].path.name == 'cheerful-dress.png'


def test_filter_case_insensitive(sample_images):
    """Test that tag filtering is case-insensitive."""
    result = filter_images_by_tags(sample_images, ['CHEERFUL'], [], False)
    assert len(result) == 2

    result = filter_images_by_tags(sample_images, [], ['CONTROL'], False)
    assert len(result) == 5


def test_filter_no_matches():
    """Test filtering when no images match."""
    images = [
        ImageEntry(Path('cheerful.png'), ['cheerful', 'dress']),
        ImageEntry(Path('excited.png'), ['excited', 'hoodie']),
    ]
    result = filter_images_by_tags(images, ['calm'], [], False)
    assert len(result) == 0


# ============================================================================
# Image Registry Loading Tests
# ============================================================================

def test_load_image_registry_empty():
    """Test loading empty image registry."""
    with tempfile.TemporaryDirectory() as tmpdir:
        avatar_dir = Path(tmpdir)
        registry = load_image_registry(avatar_dir, [])
        assert len(registry) == 0


def test_load_image_registry_relative_paths():
    """Test loading registry with relative paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        avatar_dir = Path(tmpdir)

        # Create test images
        (avatar_dir / 'subdir').mkdir()
        (avatar_dir / 'test1.png').touch()
        (avatar_dir / 'subdir' / 'test2.png').touch()

        registry_config = [
            {'path': 'test1.png', 'tags': ['cheerful', 'dress']},
            {'path': 'subdir/test2.png', 'tags': ['excited', 'hoodie']},
        ]

        registry = load_image_registry(avatar_dir, registry_config)

        assert len(registry) == 2
        assert all(img.path.is_absolute() for img in registry)
        assert registry[0].tags == ['cheerful', 'dress']
        assert registry[1].tags == ['excited', 'hoodie']


def test_load_image_registry_absolute_paths():
    """Test loading registry with absolute paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        avatar_dir = Path(tmpdir)
        img_path = avatar_dir / 'test.png'
        img_path.touch()

        registry_config = [
            {'path': str(img_path), 'tags': ['cheerful', 'dress']},
        ]

        registry = load_image_registry(avatar_dir, registry_config)

        assert len(registry) == 1
        assert registry[0].path.is_absolute()
        assert registry[0].path == img_path


def test_load_image_registry_missing_emotion_tag():
    """Test that images without emotion tags are skipped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        avatar_dir = Path(tmpdir)

        registry_config = [
            {'path': 'valid.png', 'tags': ['cheerful', 'dress']},
            {'path': 'invalid.png', 'tags': ['dress', 'wave']},  # No emotion tag
            {'path': 'valid2.png', 'tags': ['excited', 'hoodie']},
        ]

        registry = load_image_registry(avatar_dir, registry_config)

        assert len(registry) == 2
        assert registry[0].tags == ['cheerful', 'dress']
        assert registry[1].tags == ['excited', 'hoodie']


def test_load_image_registry_invalid_entries():
    """Test that invalid registry entries are skipped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        avatar_dir = Path(tmpdir)

        registry_config = [
            {'path': 'valid.png', 'tags': ['cheerful', 'dress']},
            {'path': 'missing-tags.png'},  # Missing tags field
            {'tags': ['excited', 'hoodie']},  # Missing path field
            'invalid-entry',  # Not a dict
            {'path': 'valid2.png', 'tags': ['calm', 'formal']},
        ]

        registry = load_image_registry(avatar_dir, registry_config)

        assert len(registry) == 2
        assert registry[0].tags == ['cheerful', 'dress']
        assert registry[1].tags == ['calm', 'formal']


# ============================================================================
# ImageEntry Tests
# ============================================================================

def test_image_entry_creation():
    """Test ImageEntry creation and properties."""
    img = ImageEntry(Path('test.png'), ['cheerful', 'dress', 'wave'])

    assert img.path == Path('test.png')
    assert img.tags == ['cheerful', 'dress', 'wave']
    assert img.tag_set == {'cheerful', 'dress', 'wave'}


def test_image_entry_tag_set_lowercase():
    """Test that tag_set returns lowercase tags."""
    img = ImageEntry(Path('test.png'), ['Cheerful', 'DRESS', 'Wave'])

    assert img.tag_set == {'cheerful', 'dress', 'wave'}


def test_image_entry_string_path():
    """Test ImageEntry with string path (should convert to Path)."""
    img = ImageEntry('test.png', ['cheerful', 'dress'])

    assert isinstance(img.path, Path)
    assert img.path == Path('test.png')


# ============================================================================
# Integration Tests
# ============================================================================

def test_filter_workflow_integration(sample_images):
    """Test complete filtering workflow."""
    # Start with all images
    assert len(sample_images) == 6

    # Apply include filter for casual summer images
    result = filter_images_by_tags(sample_images, ['casual', 'summer'], [], False)
    assert len(result) == 1
    assert result[0].path.name == 'cheerful-casual.png'

    # Exclude formal images
    result = filter_images_by_tags(sample_images, [], ['formal'], False)
    assert len(result) == 5

    # Include cheerful, exclude casual
    result = filter_images_by_tags(sample_images, ['cheerful'], ['casual'], False)
    assert len(result) == 1
    assert result[0].path.name == 'cheerful-dress.png'

    # Require multiple tags (ALL)
    result = filter_images_by_tags(
        sample_images,
        ['focused', 'coding'],
        [],
        require_all_include=True
    )
    assert len(result) == 1
    assert result[0].path.name == 'focused-hoodie.png'


def test_tag_similarity_for_flip_decision(sample_images):
    """Test tag similarity calculation for flip animation decision."""
    # Same outfit, different pose - should NOT flip (similarity > 0.5)
    img1 = sample_images[0]  # cheerful-dress
    img2 = ImageEntry(Path('cheerful-dress-2.png'), ['cheerful', 'cream-dress', 'peace-sign'])
    similarity = calculate_tag_similarity(img1.tag_set, img2.tag_set)
    assert similarity >= 0.5  # Don't flip

    # Different outfit - should flip (similarity < 0.5)
    img3 = sample_images[1]  # cheerful-casual
    similarity = calculate_tag_similarity(img1.tag_set, img3.tag_set)
    assert similarity < 0.5  # Flip!

    # Completely different emotion and outfit - should definitely flip
    img4 = sample_images[3]  # focused-hoodie
    similarity = calculate_tag_similarity(img1.tag_set, img4.tag_set)
    assert similarity < 0.3  # Strong flip
