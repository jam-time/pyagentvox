"""TTS monitor for Claude Code conversations.

This module watches Claude Code conversation JSONL files and automatically sends
assistant responses to PyAgentVox for text-to-speech playback. Runs as a
separate subprocess launched by PyAgentVox main process.

Usage:
    # Auto-detect TTS input file
    python -m pyagentvox.tts_monitor

    # Specify input file
    python -m pyagentvox.tts_monitor --input-file /tmp/agent_input_12345.txt

Author:
    Jake Meador <jameador13@gmail.com>
"""

import argparse
import glob
import json
import logging
import re
import sys
import tempfile
import time
from pathlib import Path

__author__ = 'Jake Meador <jameador13@gmail.com>'
__all__ = ['remove_emojis', 'clean_for_tts', 'main']

logger = logging.getLogger('pyagentvox.tts_monitor')


def remove_emojis(text: str) -> str:
    """Remove emojis and unicode symbols from text."""
    emoji_pattern = re.compile(
        '['
        '\U0001F1E0-\U0001F1FF'
        '\U0001F300-\U0001F5FF'
        '\U0001F600-\U0001F64F'
        '\U0001F680-\U0001F6FF'
        '\U0001F700-\U0001F77F'
        '\U0001F780-\U0001F7FF'
        '\U0001F800-\U0001F8FF'
        '\U0001F900-\U0001F9FF'
        '\U0001FA00-\U0001FA6F'
        '\U0001FA70-\U0001FAFF'
        '\U00002600-\U000026FF'
        '\U00002700-\U000027BF'
        '\U0000FE00-\U0000FE0F'
        '\U0001F000-\U0001F02F'
        '\U0001F0A0-\U0001F0FF'
        '\U00002300-\U000023FF'
        '\U00002B50'
        '\U0000231A-\U0000231B'
        '\U000025AA-\U000025AB'
        '\U000025B6'
        '\U000025C0'
        '\U000025FB-\U000025FE'
        '\U00002934-\U00002935'
        '\U00002B05-\U00002B07'
        '\U00002B1B-\U00002B1C'
        '\U00003030'
        '\U0000303D'
        '\U00003297'
        '\U00003299'
        '\U0000203C'
        '\U00002049'
        '\U00002122'
        '\U00002139'
        '\U00002194-\U00002199'
        '\U000021A9-\U000021AA'
        ']+',
        flags=re.UNICODE
    )
    return emoji_pattern.sub('', text).strip()


def clean_for_tts(text: str) -> str:
    """Clean text for TTS - remove verbose content but keep important context.

    Smart filtering:
    - Paths: Keep filename only (C:\\path\\to\\file.py -> file.py)
    - URLs: Remove completely
    - Code: Remove code blocks and inline code
    - Markdown: Strip formatting but keep content
    - Lists: Remove bullets/numbers but keep text
    """
    # Remove code blocks (triple backticks)
    text = re.sub(r'```[\s\S]*?```', '', text)

    # Remove inline code (single backticks)
    text = re.sub(r'`[^`]+`', '', text)

    # Remove HTTP/HTTPS URLs completely
    text = re.sub(r'https?://[^\s<>"\')]+', '', text)
    text = re.sub(r'www\.[^\s<>"\')]+', '', text)

    # Windows paths: Replace with just filename
    # Match: C:\path\to\file.ext -> file.ext
    # More specific: must have drive letter, colon, backslash, and multiple path components
    text = re.sub(
        r'\b[A-Z]:\\(?:[^\\/:*?"<>|\s]+\\)+([^\\/:*?"<>|\s]+)',
        r'\1',
        text
    )

    # Unix paths: Replace with just filename
    # Match: /path/to/file.ext -> file.ext
    # More specific: must start with /, have at least 2 components, end with extension
    text = re.sub(
        r'\B/(?:[^/\s]+/)+([^/\s]+\.\w+)\b',
        r'\1',
        text
    )

    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # NOTE: Emotion tags [cheerful], [excited], etc. are preserved - PyAgentVox handles them

    # Remove markdown headers (# ## ###) but keep the text
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)

    # Convert markdown links [text](url) to just text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

    # Remove bullet points but keep text
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)

    # Remove numbered list markers but keep text
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)

    # Collapse multiple spaces/tabs to single space
    text = re.sub(r'[ \t]+', ' ', text)

    # Collapse multiple newlines to single newline
    text = re.sub(r'\n\n+', '\n', text)

    # Remove emojis (they don't speak well)
    text = remove_emojis(text)

    return text.strip()


def main() -> None:
    """Run TTS monitor to watch Claude conversation files and send responses to PyAgentVox."""
    parser = argparse.ArgumentParser(description='TTS Monitor - Luna Voice Output')
    parser.add_argument('--input-file', type=str, help='PyAgentVox input file path')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(message)s')

    logger.info('=' * 50)
    logger.info('  TTS MONITOR - Luna Voice Output')
    logger.info('=' * 50)

    # Find most recently active project directory
    projects_dir = Path.home() / '.claude' / 'projects'
    if not projects_dir.exists():
        raise FileNotFoundError(f'Claude projects directory not found: {projects_dir}')

    project_dirs = [d for d in projects_dir.iterdir() if d.is_dir()]
    if not project_dirs:
        raise FileNotFoundError('No Claude projects found!')

    # Use most recently modified project
    conv_dir = max(project_dirs, key=lambda p: p.stat().st_mtime)
    logger.info(f'Detected project: {conv_dir.name}')

    jsonl_files = sorted(conv_dir.glob('*.jsonl'), key=lambda p: p.stat().st_mtime, reverse=True)

    if not jsonl_files:
        raise FileNotFoundError(f'No conversation files found in {conv_dir.name}!')

    conv_file = jsonl_files[0]
    logger.info(f'Watching: {conv_file.name}')

    # Get TTS file
    if not args.input_file:
        tts_files = glob.glob(str(Path(tempfile.gettempdir()) / 'agent_input_*.txt'))
        if not tts_files:
            raise FileNotFoundError('PyAgentVox not running! No input files found.')
        tts_file = Path(tts_files[0])
    else:
        tts_file = Path(args.input_file)
        if not tts_file.exists():
            raise FileNotFoundError(f'Provided input file does not exist: {tts_file}')

    logger.info(f'TTS Output: {tts_file.name}')
    logger.info('')
    logger.info('Ready! Monitoring for responses...')
    logger.info('-' * 50)

    last_pos = conv_file.stat().st_size
    last_text = ''

    while True:
        try:
            size = conv_file.stat().st_size

            if size <= last_pos:
                time.sleep(0.3)
                continue

            with open(conv_file, 'r', encoding='utf-8') as f:
                f.seek(last_pos)
                new_lines = f.read()
                last_pos = f.tell()  # Use actual position after read

            for line in new_lines.strip().split('\n'):
                if not line:
                    continue

                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                message_obj = msg.get('message', {})
                if message_obj.get('role') != 'assistant':
                    continue

                texts = []
                for block in message_obj.get('content', []):
                    if isinstance(block, dict) and block.get('type') == 'text':
                        texts.append(block.get('text', ''))

                if not texts:
                    continue

                response = '\n\n'.join(texts)  # Preserve paragraph breaks between blocks
                if not response or response == last_text:
                    continue

                clean_response = clean_for_tts(response)
                if not clean_response:
                    last_text = response
                    continue

                try:
                    tts_file.write_text(clean_response, encoding='utf-8')
                    preview = clean_response[:60] + '...' if len(clean_response) > 60 else clean_response
                    logger.info(f'[SPEAKING] {preview}')
                    last_text = response
                except Exception as e:
                    logger.error(f'Failed to write TTS file: {e}')
                    continue

            time.sleep(0.3)

        except KeyboardInterrupt:
            logger.info('\n\nStopped!')
            return
        except Exception as e:
            logger.error(f'Error: {e}')
            time.sleep(1)

if __name__ == '__main__':
    sys.exit(main())
