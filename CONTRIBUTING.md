# Contributing to PyAgentVox

Thank you for your interest in contributing to PyAgentVox! This document provides guidelines for contributing to the project.

## 🎯 Ways to Contribute

- **Bug Reports** - Report bugs via GitHub Issues
- **Feature Requests** - Suggest new features or improvements
- **Code Contributions** - Submit pull requests with bug fixes or new features
- **Documentation** - Improve documentation, add examples, fix typos
- **Voice Profiles** - Share optimized voice profile configurations
- **Testing** - Test on different systems and report compatibility issues

## 🐛 Reporting Bugs

When reporting bugs, please include:

1. **PyAgentVox version** - Check with `python -m pyagentvox --version` (if implemented)
2. **Python version** - Output of `python --version`
3. **Operating system** - Windows version
4. **Steps to reproduce** - Clear steps to reproduce the issue
5. **Expected behavior** - What you expected to happen
6. **Actual behavior** - What actually happened
7. **Error messages** - Full error output or log files
8. **Config file** - Your configuration (if relevant)

## 💡 Feature Requests

For feature requests, please describe:

1. **Use case** - What problem does this solve?
2. **Proposed solution** - How should it work?
3. **Alternatives** - Other solutions you've considered
4. **Impact** - Who benefits from this feature?

## 🔧 Development Setup

### Prerequisites

- Python 3.12+
- Windows OS (for full functionality)
- Git
- uv or pip

### Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/pyagentvox.git
cd pyagentvox

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .

# Install development dependencies (if added)
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run tests (when test suite is added)
pytest

# Run with coverage
pytest --cov=pyagentvox

# Run type checking
mypy pyagentvox
```

## 📝 Code Style

### Python Style Guide

- **Follow PEP 8** - Use PEP 8 style guide for Python code
- **Line length** - Maximum 100 characters
- **Imports** - Organize imports: stdlib, third-party, local
- **Type hints** - Use type hints for function signatures
- **Docstrings** - Use Google-style docstrings

### Example

```python
"""Module docstring describing purpose."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from third_party import module

from pyagentvox import config


def example_function(text: str, volume: Optional[int] = None) -> bool:
    """Do something with text at specified volume.

    Args:
        text: The text to process
        volume: Optional volume level (0-100)

    Returns:
        True if successful, False otherwise

    Raises:
        ValueError: If volume is out of range
    """
    if volume is not None and not 0 <= volume <= 100:
        raise ValueError(f'Volume must be 0-100, got {volume}')

    # Implementation here
    return True
```

### Code Formatting

- **Use black** for automatic code formatting (if adopted)
- **Use isort** for import sorting (if adopted)
- **Use pylint** for linting (if adopted)

### Naming Conventions

- **Functions/variables** - `snake_case`
- **Classes** - `PascalCase`
- **Constants** - `UPPER_SNAKE_CASE`
- **Private methods** - `_leading_underscore`
- **Modules** - `lowercase` or `snake_case`

## 🌿 Git Workflow

### Branching

- **main** - Stable release branch
- **develop** - Development branch (if using GitFlow)
- **feature/name** - Feature branches
- **bugfix/name** - Bug fix branches
- **hotfix/name** - Critical fixes for production

### Commit Messages

Follow conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation changes
- `style` - Code style changes (formatting, no logic change)
- `refactor` - Code refactoring
- `test` - Adding or updating tests
- `chore` - Maintenance tasks

**Examples:**
```
feat(voice): add support for custom TTS engines

fix(injector): prevent multiple keyboard inputs for same text

docs(readme): add installation instructions for macOS

refactor(config): simplify profile loading logic
```

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch** from `main`
3. **Make your changes** with clear commits
4. **Add tests** for new functionality
5. **Update documentation** if needed
6. **Submit a pull request** with:
   - Clear title and description
   - Reference to related issue (if any)
   - List of changes
   - Screenshots/videos for UI changes

## 🧪 Testing Guidelines

- **Write tests** for new features and bug fixes
- **Run existing tests** before submitting PR
- **Test on Windows** (primary platform)
- **Test with different voice profiles**
- **Test TTS-only mode**
- **Test with different microphone setups**

## 📚 Documentation Guidelines

- **Update README.md** for user-facing changes
- **Update SETUP.md** for setup process changes
- **Update USAGE.md** for new CLI options
- **Update AGENTS.md** for AI agent integration changes
- **Update CHANGELOG.md** for all changes
- **Add docstrings** for new functions/classes
- **Update type hints** when changing signatures

## 🎨 Voice Profile Contributions

When contributing voice profiles:

```yaml
profiles:
  your_profile_name:
    neutral:
      voice: "en-US-VoiceNameNeural"
      speed: "+10%"
      pitch: "+5Hz"
    cheerful:
      voice: "en-US-VoiceNameNeural"
      speed: "+15%"
      pitch: "+10Hz"
    # ... other emotions
```

Include:
- **Profile name** and description
- **Voice characteristics** (gender, accent, style)
- **Recommended use cases**
- **Testing notes** (what you tested, what works well)

## ⚡ Performance Guidelines

- **Cache lookups** - Don't search repeatedly
- **Async/await** - Use async for I/O operations
- **Avoid blocking** - Don't block the event loop
- **Temp file cleanup** - Clean up temp files
- **Resource management** - Use context managers

## 🔒 Security Guidelines

- **No credentials** - Never commit API keys or passwords
- **Sanitize input** - Validate and sanitize user input
- **Safe file operations** - Validate file paths
- **Secure temp files** - Use appropriate permissions

## 📋 Checklist Before Submitting PR

- [ ] Code follows PEP 8 style guide
- [ ] Type hints added for new functions
- [ ] Docstrings added for new functions/classes
- [ ] Tests added for new functionality
- [ ] All tests pass
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] No debugging code left in
- [ ] No commented-out code
- [ ] Commit messages follow conventional format

## 🤝 Code of Conduct

- **Be respectful** - Treat everyone with respect
- **Be collaborative** - Work together constructively
- **Be patient** - Help others learn and grow
- **Be inclusive** - Welcome diverse perspectives

## 💬 Questions?

- **GitHub Issues** - For bugs and feature requests
- **GitHub Discussions** - For questions and general discussion (if enabled)

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to PyAgentVox! 🎤✨
