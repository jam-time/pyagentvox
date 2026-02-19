"""Tests for avatar tag querying and filter state reading.

Tests the list_tags() function, tag categorization, print_tag_summary() output,
read_current_filters() IPC parsing, and the tags/current CLI subcommands.

Author:
    Jake Meador <jameador13@gmail.com>
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from pyagentvox.avatar_tags import (
    KNOWN_OUTFIT_TAGS,
    VALID_EMOTIONS,
    _categorize_tag,
    apply_filters,
    list_tags,
    print_tag_summary,
    read_current_filters,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_config_with_images():
    """Create temporary config file with tagged avatar images."""
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
                'images': [
                    {'path': 'cheerful-dress-1.png', 'tags': ['cheerful', 'dress', 'wave']},
                    {'path': 'cheerful-dress-2.png', 'tags': ['cheerful', 'dress', 'peace-sign']},
                    {'path': 'cheerful-casual.png', 'tags': ['cheerful', 'daisy-dukes', 'casual', 'summer']},
                    {'path': 'excited-dress.png', 'tags': ['excited', 'dress', 'victory']},
                    {'path': 'excited-casual.png', 'tags': ['excited', 'daisy-dukes', 'standing']},
                    {'path': 'calm-formal.png', 'tags': ['calm', 'dress', 'formal']},
                    {'path': 'focused-hoodie.png', 'tags': ['focused', 'hoodie', 'coding']},
                    {'path': 'warm-casual.png', 'tags': ['warm', 'tank-top', 'glasses', 'relaxed']},
                ],
            }
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)

        yield config_path, avatar_dir


@pytest.fixture
def temp_config_empty():
    """Create temporary config file with no images."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / 'pyagentvox.yaml'

        config = {
            'avatar': {
                'directory': str(Path(tmpdir) / 'avatars'),
                'default_size': 300,
                'images': [],
            }
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)

        yield config_path


# ============================================================================
# Tag Categorization Tests
# ============================================================================

class TestCategorizeTag:
    """Test the _categorize_tag helper function."""

    def test_emotion_tags_categorized_correctly(self) -> None:
        """All valid emotion tags should categorize as 'emotions'."""
        for emotion in VALID_EMOTIONS:
            assert _categorize_tag(emotion) == 'emotions', f'{emotion} should be categorized as emotions'

    def test_outfit_tags_categorized_correctly(self) -> None:
        """All known outfit tags should categorize as 'outfits'."""
        for outfit in KNOWN_OUTFIT_TAGS:
            assert _categorize_tag(outfit) == 'outfits', f'{outfit} should be categorized as outfits'

    def test_unknown_tags_categorized_as_other(self) -> None:
        """Tags not in emotions or outfits should be 'other'."""
        assert _categorize_tag('wave') == 'other'
        assert _categorize_tag('peace-sign') == 'other'
        assert _categorize_tag('coding') == 'other'
        assert _categorize_tag('standing') == 'other'
        assert _categorize_tag('victory') == 'other'

    def test_case_insensitive_categorization(self) -> None:
        """Tags should be categorized case-insensitively."""
        assert _categorize_tag('CHEERFUL') == 'emotions'
        assert _categorize_tag('Dress') == 'outfits'
        assert _categorize_tag('Wave') == 'other'


# ============================================================================
# list_tags() Tests
# ============================================================================

class TestListTags:
    """Test the list_tags function."""

    def test_returns_three_categories(self, temp_config_with_images) -> None:
        """Result should always have emotions, outfits, and other keys."""
        config_path, _ = temp_config_with_images
        result = list_tags(config_path)

        assert 'emotions' in result
        assert 'outfits' in result
        assert 'other' in result

    def test_emotion_tags_counted(self, temp_config_with_images) -> None:
        """Emotion tags should appear in the emotions category with correct counts."""
        config_path, _ = temp_config_with_images
        result = list_tags(config_path)

        emotions = result['emotions']
        assert emotions['cheerful'] == 3
        assert emotions['excited'] == 2
        assert emotions['calm'] == 1
        assert emotions['focused'] == 1
        assert emotions['warm'] == 1

    def test_outfit_tags_counted(self, temp_config_with_images) -> None:
        """Outfit tags should appear in the outfits category with correct counts."""
        config_path, _ = temp_config_with_images
        result = list_tags(config_path)

        outfits = result['outfits']
        assert outfits['dress'] == 4
        assert outfits['daisy-dukes'] == 2
        assert outfits['hoodie'] == 1
        assert outfits['tank-top'] == 1

    def test_other_tags_counted(self, temp_config_with_images) -> None:
        """Custom tags should appear in the other category with correct counts."""
        config_path, _ = temp_config_with_images
        result = list_tags(config_path)

        other = result['other']
        # These tags are not in VALID_EMOTIONS or KNOWN_OUTFIT_TAGS
        assert other['wave'] == 1
        assert other['peace-sign'] == 1
        assert other['victory'] == 1
        assert other['standing'] == 1
        assert other['coding'] == 1
        assert other['summer'] == 1
        assert other['relaxed'] == 1
        # 'formal' and 'casual' are in KNOWN_OUTFIT_TAGS, so NOT in 'other'
        assert 'formal' not in other
        assert 'casual' not in other

    def test_outfit_subcategory_includes_casual_glasses_formal(self, temp_config_with_images) -> None:
        """Tags like casual, glasses, and formal should be in outfits, not other."""
        config_path, _ = temp_config_with_images
        result = list_tags(config_path)

        outfits = result['outfits']
        # 'casual', 'glasses', and 'formal' are all in KNOWN_OUTFIT_TAGS
        assert outfits['casual'] == 1
        assert outfits['glasses'] == 1
        assert outfits['formal'] == 1

    def test_sorted_by_count_descending(self, temp_config_with_images) -> None:
        """Tags within each category should be sorted by count descending."""
        config_path, _ = temp_config_with_images
        result = list_tags(config_path)

        for category_tags in result.values():
            counts = list(category_tags.values())
            assert counts == sorted(counts, reverse=True), f'Tags not sorted by count descending'

    def test_empty_config_returns_empty_categories(self, temp_config_empty) -> None:
        """Empty image list should return empty categories."""
        result = list_tags(temp_config_empty)

        assert result['emotions'] == {}
        assert result['outfits'] == {}
        assert result['other'] == {}

    def test_tags_are_lowercased(self) -> None:
        """Tags should be normalized to lowercase in output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'pyagentvox.yaml'
            config = {
                'avatar': {
                    'directory': str(Path(tmpdir) / 'avatars'),
                    'images': [
                        {'path': 'test.png', 'tags': ['Cheerful', 'DRESS', 'Wave']},
                    ],
                }
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f)

            result = list_tags(config_path)

            assert 'cheerful' in result['emotions']
            assert 'dress' in result['outfits']
            assert 'wave' in result['other']


# ============================================================================
# print_tag_summary() Tests
# ============================================================================

class TestPrintTagSummary:
    """Test the print_tag_summary function output."""

    def test_header_present(self, temp_config_with_images, capsys) -> None:
        """Output should contain the AVATAR TAGS header."""
        config_path, _ = temp_config_with_images
        print_tag_summary(config_path)
        output = capsys.readouterr().out

        assert '=== AVATAR TAGS ===' in output

    def test_category_headers_present(self, temp_config_with_images, capsys) -> None:
        """Output should contain category headers with tag and image counts."""
        config_path, _ = temp_config_with_images
        print_tag_summary(config_path)
        output = capsys.readouterr().out

        assert 'Emotions (' in output
        assert 'Outfits (' in output
        assert 'Other (' in output

    def test_total_line_present(self, temp_config_with_images, capsys) -> None:
        """Output should contain total summary line."""
        config_path, _ = temp_config_with_images
        print_tag_summary(config_path)
        output = capsys.readouterr().out

        assert 'Total:' in output
        assert 'unique tags across' in output
        assert '8 images' in output

    def test_tag_counts_in_output(self, temp_config_with_images, capsys) -> None:
        """Tag counts should appear in parentheses."""
        config_path, _ = temp_config_with_images
        print_tag_summary(config_path)
        output = capsys.readouterr().out

        assert 'cheerful (3)' in output
        assert 'dress (4)' in output

    def test_empty_config_output(self, temp_config_empty, capsys) -> None:
        """Empty config should still show header and total of 0."""
        print_tag_summary(temp_config_empty)
        output = capsys.readouterr().out

        assert '=== AVATAR TAGS ===' in output
        assert 'Total: 0 unique tags across 0 images' in output

    def test_skips_empty_categories(self, capsys) -> None:
        """Categories with no tags should not appear in output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'pyagentvox.yaml'
            config = {
                'avatar': {
                    'directory': str(Path(tmpdir) / 'avatars'),
                    'images': [
                        {'path': 'test.png', 'tags': ['cheerful', 'wave']},
                    ],
                }
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f)

            print_tag_summary(config_path)
            output = capsys.readouterr().out

            assert 'Emotions (' in output
            assert 'Other (' in output
            # No outfit tags registered, so Outfits header should not appear
            assert 'Outfits (' not in output


# ============================================================================
# read_current_filters() Tests
# ============================================================================

class TestReadCurrentFilters:
    """Test reading current filter state from IPC file."""

    def test_no_filter_file_returns_defaults(self) -> None:
        """Missing filter file should return empty defaults."""
        result = read_current_filters(pid=99999999)

        assert result['include'] == []
        assert result['exclude'] == []
        assert result['require_all'] is False

    def test_read_include_filters(self) -> None:
        """Should parse include tags from filter file."""
        pid = 88888888
        try:
            apply_filters(pid, include_tags=['casual', 'summer'])
            result = read_current_filters(pid)

            assert result['include'] == ['casual', 'summer']
            assert result['exclude'] == []
            assert result['require_all'] is False
        finally:
            # Clean up IPC file
            filter_file = Path(tempfile.gettempdir()) / f'agent_avatar_filter_{pid}.txt'
            filter_file.unlink(missing_ok=True)

    def test_read_exclude_filters(self) -> None:
        """Should parse exclude tags from filter file."""
        pid = 77777777
        try:
            apply_filters(pid, exclude_tags=['formal', 'ball-gown'])
            result = read_current_filters(pid)

            assert result['include'] == []
            assert result['exclude'] == ['formal', 'ball-gown']
        finally:
            filter_file = Path(tempfile.gettempdir()) / f'agent_avatar_filter_{pid}.txt'
            filter_file.unlink(missing_ok=True)

    def test_read_combined_filters(self) -> None:
        """Should parse combined include, exclude, and require_all."""
        pid = 66666666
        try:
            apply_filters(
                pid,
                include_tags=['cheerful', 'dress'],
                exclude_tags=['formal'],
                require_all=True,
            )
            result = read_current_filters(pid)

            assert result['include'] == ['cheerful', 'dress']
            assert result['exclude'] == ['formal']
            assert result['require_all'] is True
        finally:
            filter_file = Path(tempfile.gettempdir()) / f'agent_avatar_filter_{pid}.txt'
            filter_file.unlink(missing_ok=True)

    def test_read_after_reset_returns_defaults(self) -> None:
        """After reset, reading should return empty defaults."""
        pid = 55555555
        try:
            # First apply filters
            apply_filters(pid, include_tags=['cheerful'])
            # Then reset
            apply_filters(pid, reset=True)

            result = read_current_filters(pid)

            assert result['include'] == []
            assert result['exclude'] == []
            assert result['require_all'] is False
        finally:
            filter_file = Path(tempfile.gettempdir()) / f'agent_avatar_filter_{pid}.txt'
            filter_file.unlink(missing_ok=True)


# ============================================================================
# CLI Subcommand Tests
# ============================================================================

class TestCLITagsCommand:
    """Test the 'tags' CLI subcommand."""

    def test_tags_command_calls_print_tag_summary(self, temp_config_with_images) -> None:
        """The 'tags' command should call print_tag_summary."""
        config_path, _ = temp_config_with_images

        with patch('pyagentvox.avatar_tags.print_tag_summary') as mock_summary:
            from pyagentvox.avatar_tags import main
            with patch('sys.argv', ['avatar_tags', '--config', str(config_path), 'tags']):
                main()
            mock_summary.assert_called_once_with(config_path)

    def test_tags_command_produces_output(self, temp_config_with_images, capsys) -> None:
        """The 'tags' command should produce formatted output."""
        config_path, _ = temp_config_with_images

        from pyagentvox.avatar_tags import main
        with patch('sys.argv', ['avatar_tags', '--config', str(config_path), 'tags']):
            main()

        output = capsys.readouterr().out
        assert '=== AVATAR TAGS ===' in output


class TestCLICurrentCommand:
    """Test the 'current' CLI subcommand."""

    def test_current_command_no_filters(self, capsys) -> None:
        """The 'current' command with no active filters shows default message."""
        from pyagentvox.avatar_tags import main
        with patch('sys.argv', ['avatar_tags', 'current', '--pid', '99999999']):
            main()

        output = capsys.readouterr().out
        assert 'No active filters' in output

    def test_current_command_with_filters(self, capsys) -> None:
        """The 'current' command shows active filters when present."""
        pid = 44444444
        try:
            apply_filters(pid, include_tags=['casual', 'summer'])

            from pyagentvox.avatar_tags import main
            with patch('sys.argv', ['avatar_tags', 'current', '--pid', str(pid)]):
                main()

            output = capsys.readouterr().out
            assert 'Current avatar filters' in output
            assert 'casual' in output
            assert 'summer' in output
        finally:
            filter_file = Path(tempfile.gettempdir()) / f'agent_avatar_filter_{pid}.txt'
            filter_file.unlink(missing_ok=True)
