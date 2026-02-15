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
    """Clean text for TTS - remove markdown, URLs, code blocks, HTML tags."""
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`[^`]+`', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'www\.\S+', '', text)
    text = re.sub(r'[A-Z]:\\[^\s<>"|]*', '', text)
    text = re.sub(r'/[\w/\-_.]+\.\w+', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    # NOTE: Emotion tags [cheerful] preserved - PyAgentVox handles them
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\n+', '\n', text)
    text = remove_emojis(text)
    return text.strip()


def main():
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
        logger.error(f'Claude projects directory not found: {projects_dir}')
        return 1

    project_dirs = [d for d in projects_dir.iterdir() if d.is_dir()]
    if not project_dirs:
        logger.error('No Claude projects found!')
        return 1

    # Use most recently modified project
    conv_dir = max(project_dirs, key=lambda p: p.stat().st_mtime)
    logger.info(f'Detected project: {conv_dir.name}')

    jsonl_files = sorted(conv_dir.glob('*.jsonl'), key=lambda p: p.stat().st_mtime, reverse=True)

    if not jsonl_files:
        logger.error(f'No conversation files found in {conv_dir.name}!')
        return 1

    conv_file = jsonl_files[0]
    logger.info(f'Watching: {conv_file.name}')

    # Get TTS file
    if not args.input_file:
        tts_files = glob.glob(str(Path(tempfile.gettempdir()) / 'agent_input_*.txt'))
        if not tts_files:
            logger.error('PyAgentVox not running!')
            return 1
        tts_file = Path(tts_files[0])
    else:
        tts_file = Path(args.input_file)
        if not tts_file.exists():
            logger.error(f'Provided input file does not exist: {tts_file}')
            return 1

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
            return 0
        except Exception as e:
            logger.error(f'Error: {e}')
            time.sleep(1)

    return 0  # Explicit success return (though loop is infinite)

if __name__ == '__main__':
    sys.exit(main())
