"""Configuration system for PyAgentVox.

This module handles configuration loading, merging, and persistence for voice
settings. Supports JSON and YAML formats with profile-based overrides and
CLI-based modifications.

Usage:
    config, config_file = load_config(
        config_path='pyagentvox.yaml',
        profile='male_voices',
        overrides={'neutral.speed': '+20%'}
    )

Author:
    Jake Meador <jameador13@gmail.com>
"""

import contextlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

import yaml

__author__ = 'Jake Meador <jameador13@gmail.com>'
__all__ = [
    'merge_dicts',
    'find_config_file',
    'load_config_file',
    'save_config_file',
    'load_config',
    'parse_override_arg',
    'apply_key_path',
    'parse_set_string',
    'normalize_value',
    'resolve_voice_name',
    'modify_value',
    'parse_modify_string',
]

logger = logging.getLogger('pyagentvox')


def merge_dicts(base: dict, override: dict) -> dict:
    """Recursively merge two dictionaries."""
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value

    return result


def find_config_file(custom_path: Optional[str] = None) -> Optional[Path]:
    """Find config file in order: custom, CWD pyagentvox.{json,yaml}, package pyagentvox.yaml."""
    if custom_path:
        path = Path(custom_path)
        if not path.exists():
            raise FileNotFoundError(f'Config file not found: {custom_path}')
        return path

    cwd = Path.cwd()
    if (json_config := cwd / 'pyagentvox.json').exists():
        return json_config

    if (yaml_config := cwd / 'pyagentvox.yaml').exists():
        return yaml_config

    script_dir = Path(__file__).parent
    if (package_config := script_dir / 'pyagentvox.yaml').exists():
        return package_config

    return None


def load_config_file(path: Path) -> dict:
    """Load config file (JSON or YAML)."""
    content = path.read_text(encoding='utf-8')

    if path.suffix in ['.json', '.JSON']:
        return json.loads(content)

    if path.suffix in ['.yaml', '.yml', '.YAML', '.YML']:
        return yaml.safe_load(content)

    try:
        return yaml.safe_load(content)
    except yaml.YAMLError:
        return json.loads(content)


def save_config_file(path: Path, config: dict) -> None:
    """Save config file (JSON or YAML)."""
    if path.suffix in ['.json', '.JSON']:
        content = json.dumps(config, indent=2)
    else:
        content = yaml.dump(config, default_flow_style=False, sort_keys=False)

    path.write_text(content, encoding='utf-8')


def load_config(
    config_path: Optional[str] = None,
    profile: Optional[str] = None,
    overrides: Optional[dict] = None,
    save_overrides: bool = False
) -> tuple[dict, Optional[Path]]:
    """Load configuration with optional profile and overrides."""
    default_config = {
        'neutral': {'voice': 'en-US-MichelleNeural', 'speed': '+10%', 'pitch': '+10Hz'},
        'cheerful': {'voice': 'en-US-JennyNeural', 'speed': '+15%', 'pitch': '+8Hz'},
        'excited': {'voice': 'en-US-JennyNeural', 'speed': '+20%', 'pitch': '+10Hz'},
        'empathetic': {'voice': 'en-US-EmmaNeural', 'speed': '+5%', 'pitch': '+5Hz'},
        'warm': {'voice': 'en-US-EmmaNeural', 'speed': '+8%', 'pitch': '+18Hz'},
        'calm': {'voice': 'en-GB-SoniaNeural', 'speed': '+0%', 'pitch': '-2Hz'},
        'focused': {'voice': 'en-GB-SoniaNeural', 'speed': '+5%', 'pitch': '+0Hz'},
    }

    config_file = find_config_file(config_path)

    if config_file:
        logger.info(f'Loading config: {config_file}')
        config = merge_dicts(default_config, load_config_file(config_file))
    else:
        logger.info('No config file found, using defaults')
        config = default_config
        config_file = None

    if profile:
        if 'profiles' in config and profile in config['profiles']:
            logger.info(f'Loading profile: {profile}')
            profile_config = config['profiles'][profile]
            base_config = {k: v for k, v in config.items() if k != 'profiles'}
            config = merge_dicts(base_config, profile_config)
        else:
            logger.warning(f'Profile "{profile}" not found in config')

    if overrides:
        logger.debug(f'Applying overrides: {overrides}')
        config = merge_dicts(config, overrides)

        if save_overrides and config_file:
            logger.info(f'Saving overrides to: {config_file}')
            save_config_file(config_file, config)

    return config, config_file


def parse_override_arg(arg: str) -> tuple[str, Any]:
    """Parse config override argument (key.path=value)."""
    if '=' not in arg:
        raise ValueError(f'Invalid override format (expected key=value): {arg}')

    key_path, value = arg.split('=', 1)

    with contextlib.suppress(json.JSONDecodeError, ValueError):
        value = json.loads(value)

    return key_path, value


def apply_key_path(config: dict, key_path: str, value: Any) -> dict:
    """Apply value to nested key path."""
    keys = key_path.split('.')
    current = config

    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]

    current[keys[-1]] = value
    return config


def parse_set_string(set_string: str) -> dict[str, Any]:
    """Parse space-separated key=value pairs with shorthand support."""
    overrides = {}
    pairs = set_string.split()

    for pair in pairs:
        if '=' not in pair:
            continue

        key_path, value = pair.split('=', 1)

        with contextlib.suppress(json.JSONDecodeError, ValueError):
            value = json.loads(value)

        if key_path in ['speed', 'pitch', 'voice']:
            standard_emotions = ['neutral', 'cheerful', 'excited', 'empathetic', 'warm', 'calm', 'focused']
            for emotion in standard_emotions:
                if emotion not in overrides:
                    overrides[emotion] = {}

                if key_path == 'voice':
                    overrides[emotion]['voice'] = resolve_voice_name(value)
                else:
                    overrides[emotion][key_path] = normalize_value(key_path, value)
        else:
            overrides = apply_key_path(overrides, key_path, value)

    return overrides


def normalize_value(key: str, value: Any) -> str:
    """Normalize config value to correct format (add % or Hz suffix)."""
    if key == 'speed':
        if isinstance(value, (int, float)):
            return f'+{value}%' if value >= 0 else f'{value}%'
        if isinstance(value, str):
            if '%' not in value:
                prefix = value if value.startswith(('+', '-')) else f'+{value}'
                return f'{prefix}%'
            return value

    if key == 'pitch':
        if isinstance(value, (int, float)):
            return f'+{value}Hz' if value >= 0 else f'{value}Hz'
        if isinstance(value, str):
            if 'Hz' not in value and 'st' not in value:
                prefix = value if value.startswith(('+', '-')) else f'+{value}'
                return f'{prefix}Hz'
            return value

    return str(value)


def resolve_voice_name(voice: str) -> str:
    """Resolve voice shorthand to full voice ID."""
    voice_map = {
        'michelle': 'en-US-MichelleNeural',
        'jenny': 'en-US-JennyNeural',
        'emma': 'en-US-EmmaNeural',
        'aria': 'en-US-AriaNeural',
        'ava': 'en-US-AvaNeural',
        'sonia': 'en-GB-SoniaNeural',
        'libby': 'en-GB-LibbyNeural',
        'maisie': 'en-GB-MaisieNeural',
        'guy': 'en-US-GuyNeural',
        'davis': 'en-US-DavisNeural',
        'tony': 'en-US-TonyNeural',
        'jason': 'en-US-JasonNeural',
        'ryan': 'en-GB-RyanNeural',
        'thomas': 'en-GB-ThomasNeural',
    }
    return voice_map.get(voice.lower(), voice)


def modify_value(current: str, modifier: Any) -> str:
    """Modify config value by adding modifier."""
    match = re.match(r'([+-]?)(\d+(?:\.\d+)?)(.*)', str(current))
    if not match:
        return str(current)

    sign, number, unit = match.groups()
    current_num = float(number) * (-1 if sign == '-' else 1)

    if isinstance(modifier, str):
        if mod_match := re.match(r'([+-]?)(\d+(?:\.\d+)?)', modifier):
            mod_sign, mod_number = mod_match.groups()
            modifier = float(mod_number) * (-1 if mod_sign == '-' else 1)
    else:
        modifier = float(modifier)

    result = current_num + modifier
    return f'+{int(result)}{unit}' if result >= 0 else f'{int(result)}{unit}'


def parse_modify_string(set_string: str, config: dict) -> dict[str, Any]:
    """Parse space-separated key=modifier pairs and apply modifications."""
    overrides = {}
    pairs = set_string.split()

    for pair in pairs:
        if '=' not in pair:
            continue

        key_path, modifier = pair.split('=', 1)

        with contextlib.suppress(json.JSONDecodeError, ValueError):
            modifier = json.loads(modifier)

        if key_path in ['speed', 'pitch']:
            standard_emotions = ['neutral', 'cheerful', 'excited', 'empathetic', 'warm', 'calm', 'focused']

            for emotion in standard_emotions:
                if emotion in config and key_path in config[emotion]:
                    if emotion not in overrides:
                        overrides[emotion] = {}
                    overrides[emotion][key_path] = modify_value(config[emotion][key_path], modifier)
        else:
            keys = key_path.split('.')
            current_val = config

            with contextlib.suppress(KeyError, TypeError):
                for key in keys:
                    current_val = current_val[key]
                overrides = apply_key_path(overrides, key_path, modify_value(current_val, modifier))

    return overrides
