"""PyAgentVox - Two-way voice communication for AI agents."""

__author__ = 'Jake Meador <jameador13@gmail.com>'
__version__ = '0.1.0'

from .pyagentvox import PyAgentVox, main, run
from . import config

__all__ = ['PyAgentVox', 'main', 'run', 'config']
