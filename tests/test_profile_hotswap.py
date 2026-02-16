"""Tests for profile hot-swapping functionality.

This module tests the runtime profile switching feature that allows users
to change voice profiles without restarting PyAgentVox.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from pyagentvox import config
from pyagentvox.pyagentvox import PyAgentVox


@pytest.fixture
def mock_tts_engine():
    """Mock TTS engine for testing."""
    engine = MagicMock()
    engine.is_ready.return_value = True
    engine.cleanup = MagicMock()
    engine.__class__.__name__ = 'MockTTSEngine'
    return engine


@pytest.fixture
def mock_config():
    """Mock configuration dictionary."""
    return {
        'neutral': {'voice': 'en-US-MichelleNeural', 'speed': '+10%', 'pitch': '+10Hz'},
        'cheerful': {'voice': 'en-US-JennyNeural', 'speed': '+15%', 'pitch': '+8Hz'},
        'excited': {'voice': 'en-US-JennyNeural', 'speed': '+20%', 'pitch': '+10Hz'},
        'empathetic': {'voice': 'en-US-EmmaNeural', 'speed': '+5%', 'pitch': '+5Hz'},
        'warm': {'voice': 'en-US-EmmaNeural', 'speed': '+8%', 'pitch': '+18Hz'},
        'calm': {'voice': 'en-GB-SoniaNeural', 'speed': '+0%', 'pitch': '-2Hz'},
        'focused': {'voice': 'en-GB-SoniaNeural', 'speed': '+5%', 'pitch': '+0Hz'},
        'tts': {'engine': 'edge'},
    }


@pytest.fixture
def mock_profile_config():
    """Mock configuration with profiles."""
    return {
        'neutral': {'voice': 'en-US-AvaNeural', 'speed': '+5%', 'pitch': '+5Hz'},
        'cheerful': {'voice': 'en-US-AriaNeural', 'speed': '+10%', 'pitch': '+5Hz'},
        'excited': {'voice': 'en-US-AriaNeural', 'speed': '+15%', 'pitch': '+8Hz'},
        'empathetic': {'voice': 'en-US-EmmaNeural', 'speed': '+5%', 'pitch': '+5Hz'},
        'warm': {'voice': 'en-US-EmmaNeural', 'speed': '+8%', 'pitch': '+18Hz'},
        'calm': {'voice': 'en-GB-LibbyNeural', 'speed': '+0%', 'pitch': '-2Hz'},
        'focused': {'voice': 'en-GB-LibbyNeural', 'speed': '+5%', 'pitch': '+0Hz'},
        'tts': {'engine': 'edge'},
    }


@pytest.mark.asyncio
async def test_watch_profile_control_detects_file(mock_tts_engine, mock_config):
    """Test that _watch_profile_control() detects control file changes."""
    with patch('pyagentvox.pyagentvox.create_engine', return_value=mock_tts_engine), \
         patch('pyagentvox.pyagentvox.pygame'), \
         patch('pyagentvox.pyagentvox.sr'), \
         patch.object(PyAgentVox, '_start_voice_injector'), \
         patch.object(PyAgentVox, '_start_tts_monitor'), \
         patch('pyagentvox.pyagentvox.instruction'):

        agent = PyAgentVox(config_dict=mock_config)
        agent.tts_queue = asyncio.Queue()

        # Create control file
        control_file = Path(tempfile.gettempdir()) / f'agent_profile_{os.getpid()}.txt'

        # Mock _reload_profile to track calls
        reload_called = asyncio.Event()
        original_reload = agent._reload_profile

        async def mock_reload(profile_name):
            reload_called.set()
            # Don't actually reload, just track the call

        agent._reload_profile = mock_reload

        # Start watching in background
        watch_task = asyncio.create_task(agent._watch_profile_control())

        try:
            # Wait a bit for watcher to start
            await asyncio.sleep(0.1)

            # Write profile name to control file
            control_file.write_text('jenny', encoding='utf-8')

            # Wait for reload to be called (with timeout)
            try:
                await asyncio.wait_for(reload_called.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                pytest.fail('Profile reload was not triggered within timeout')

        finally:
            # Cleanup
            agent.running = False
            watch_task.cancel()
            try:
                await watch_task
            except asyncio.CancelledError:
                pass

            if control_file.exists():
                control_file.unlink()


@pytest.mark.asyncio
async def test_reload_profile_calls_config_load(mock_tts_engine, mock_config, mock_profile_config):
    """Test that _reload_profile() calls config.load_config() with profile parameter."""
    with patch('pyagentvox.pyagentvox.create_engine', return_value=mock_tts_engine), \
         patch('pyagentvox.pyagentvox.pygame'), \
         patch('pyagentvox.pyagentvox.sr'), \
         patch.object(PyAgentVox, '_start_voice_injector'), \
         patch.object(PyAgentVox, '_start_tts_monitor'), \
         patch('pyagentvox.pyagentvox.instruction'), \
         patch('pyagentvox.pyagentvox.config.load_config', return_value=(mock_profile_config, None)) as mock_load:

        agent = PyAgentVox(config_dict=mock_config)
        agent.config_file = Path('pyagentvox.yaml')

        # Reload with profile
        await agent._reload_profile('jenny')

        # Verify load_config was called with profile parameter
        mock_load.assert_called_once()
        call_args = mock_load.call_args
        assert call_args[1]['profile'] == 'jenny'
        assert call_args[1]['config_path'] == 'pyagentvox.yaml'


@pytest.mark.asyncio
async def test_reload_profile_cleans_up_old_engine(mock_tts_engine, mock_config, mock_profile_config):
    """Test that _reload_profile() cleans up old TTS engine before creating new one."""
    new_engine = MagicMock()
    new_engine.is_ready.return_value = True
    new_engine.cleanup = MagicMock()

    with patch('pyagentvox.pyagentvox.create_engine') as mock_create, \
         patch('pyagentvox.pyagentvox.pygame'), \
         patch('pyagentvox.pyagentvox.sr'), \
         patch.object(PyAgentVox, '_start_voice_injector'), \
         patch.object(PyAgentVox, '_start_tts_monitor'), \
         patch('pyagentvox.pyagentvox.instruction'), \
         patch('pyagentvox.pyagentvox.config.load_config', return_value=(mock_profile_config, None)):

        # First call returns original engine, second returns new engine
        mock_create.side_effect = [mock_tts_engine, new_engine]

        agent = PyAgentVox(config_dict=mock_config)

        # Verify initial engine was created
        assert agent.tts_engine == mock_tts_engine

        # Reload profile
        await agent._reload_profile('jenny')

        # Verify old engine was cleaned up
        mock_tts_engine.cleanup.assert_called_once()

        # Verify new engine was created
        assert agent.tts_engine == new_engine


@pytest.mark.asyncio
async def test_reload_profile_waits_for_queue_drain(mock_tts_engine, mock_config, mock_profile_config):
    """Test that _reload_profile() waits for TTS queue to empty."""
    with patch('pyagentvox.pyagentvox.create_engine', return_value=mock_tts_engine), \
         patch('pyagentvox.pyagentvox.pygame'), \
         patch('pyagentvox.pyagentvox.sr'), \
         patch.object(PyAgentVox, '_start_voice_injector'), \
         patch.object(PyAgentVox, '_start_tts_monitor'), \
         patch('pyagentvox.pyagentvox.instruction'), \
         patch('pyagentvox.pyagentvox.config.load_config', return_value=(mock_profile_config, None)):

        agent = PyAgentVox(config_dict=mock_config)
        agent.tts_queue = asyncio.Queue()

        # Add items to queue
        await agent.tts_queue.put('test1')
        await agent.tts_queue.put('test2')

        # Track when items are marked done
        items_processed = 0

        async def process_queue():
            nonlocal items_processed
            while items_processed < 2:
                await asyncio.sleep(0.1)
                if agent.tts_queue.qsize() > 0:
                    agent.tts_queue.get_nowait()
                    agent.tts_queue.task_done()
                    items_processed += 1

        # Start processing queue
        process_task = asyncio.create_task(process_queue())

        try:
            # This should wait for queue to drain
            await agent._reload_profile('jenny')

            # Verify queue is empty
            assert agent.tts_queue.qsize() == 0

        finally:
            process_task.cancel()
            try:
                await process_task
            except asyncio.CancelledError:
                pass


@pytest.mark.asyncio
async def test_reload_profile_handles_invalid_profile(mock_tts_engine, mock_config):
    """Test that _reload_profile() handles invalid profile gracefully."""
    with patch('pyagentvox.pyagentvox.create_engine', return_value=mock_tts_engine), \
         patch('pyagentvox.pyagentvox.pygame'), \
         patch('pyagentvox.pyagentvox.sr'), \
         patch.object(PyAgentVox, '_start_voice_injector'), \
         patch.object(PyAgentVox, '_start_tts_monitor'), \
         patch('pyagentvox.pyagentvox.instruction'), \
         patch('pyagentvox.pyagentvox.config.load_config', return_value=(mock_config, None)):

        agent = PyAgentVox(config_dict=mock_config)
        original_engine = agent.tts_engine

        # Reload with invalid profile (config.load_config will just return base config)
        await agent._reload_profile('nonexistent')

        # Should not crash, and should have a TTS engine
        assert agent.tts_engine is not None


@pytest.mark.asyncio
async def test_reload_profile_handles_engine_init_failure(mock_tts_engine, mock_config, mock_profile_config):
    """Test that _reload_profile() falls back to Edge TTS on engine init failure."""
    fallback_engine = MagicMock()
    fallback_engine.is_ready.return_value = True
    fallback_engine.cleanup = MagicMock()

    with patch('pyagentvox.pyagentvox.create_engine') as mock_create, \
         patch('pyagentvox.pyagentvox.pygame'), \
         patch('pyagentvox.pyagentvox.sr'), \
         patch.object(PyAgentVox, '_start_voice_injector'), \
         patch.object(PyAgentVox, '_start_tts_monitor'), \
         patch('pyagentvox.pyagentvox.instruction'), \
         patch('pyagentvox.pyagentvox.config.load_config', return_value=(mock_profile_config, None)):

        # First call succeeds (initial), second fails, third succeeds (fallback to edge)
        mock_create.side_effect = [mock_tts_engine, RuntimeError('Engine init failed'), fallback_engine]

        agent = PyAgentVox(config_dict=mock_config)

        # Reload profile (should trigger engine init failure then fallback)
        await agent._reload_profile('jenny')

        # Verify fallback engine was created
        assert agent.tts_engine == fallback_engine

        # Verify create_engine was called 3 times (init, failed reload, fallback)
        assert mock_create.call_count == 3


@pytest.mark.asyncio
async def test_watch_profile_control_auto_deletes_file(mock_tts_engine, mock_config):
    """Test that _watch_profile_control() deletes control file after processing."""
    with patch('pyagentvox.pyagentvox.create_engine', return_value=mock_tts_engine), \
         patch('pyagentvox.pyagentvox.pygame'), \
         patch('pyagentvox.pyagentvox.sr'), \
         patch.object(PyAgentVox, '_start_voice_injector'), \
         patch.object(PyAgentVox, '_start_tts_monitor'), \
         patch('pyagentvox.pyagentvox.instruction'):

        agent = PyAgentVox(config_dict=mock_config)
        agent.tts_queue = asyncio.Queue()

        # Create control file
        control_file = Path(tempfile.gettempdir()) / f'agent_profile_{os.getpid()}.txt'

        # Mock _reload_profile
        file_deleted = asyncio.Event()

        async def mock_reload(profile_name):
            # Wait a bit, then check if file gets deleted
            await asyncio.sleep(0.1)
            if not control_file.exists():
                file_deleted.set()

        agent._reload_profile = mock_reload

        # Start watching
        watch_task = asyncio.create_task(agent._watch_profile_control())

        try:
            # Wait for watcher to start
            await asyncio.sleep(0.1)

            # Write profile name
            control_file.write_text('jenny', encoding='utf-8')

            # Wait for file to be deleted
            try:
                await asyncio.wait_for(file_deleted.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                # Check manually
                await asyncio.sleep(0.5)
                assert not control_file.exists(), 'Control file was not deleted'

        finally:
            agent.running = False
            watch_task.cancel()
            try:
                await watch_task
            except asyncio.CancelledError:
                pass

            if control_file.exists():
                control_file.unlink()


def test_run_includes_profile_watcher():
    """Test that run() method includes _watch_profile_control() in asyncio.gather()."""
    # Read the pyagentvox.py file and check that gather includes profile watcher
    pyagentvox_file = Path(__file__).parent.parent / 'pyagentvox' / 'pyagentvox.py'
    content = pyagentvox_file.read_text()

    # Look for the asyncio.gather call in run() method
    assert '_watch_profile_control()' in content, 'Profile control watcher not found in code'

    # Check that it's in asyncio.gather
    gather_section = content[content.find('await asyncio.gather'):content.find('await asyncio.gather') + 200]
    assert '_watch_profile_control()' in gather_section, 'Profile watcher not in asyncio.gather()'
