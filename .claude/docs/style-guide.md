# Python Style Guide - PyAgentVox

Core Python coding standards for PyAgentVox, based on PEP 8 and kiro standards.

## Quick Reference

- **Line length:** 120 chars max
- **Quotes:** Single quotes always (except docstrings)
- **Type hints:** Required with `|` for unions
- **F-strings:** Use with single quotes
- **Docstrings:** Google-style
- **Imports:** stdlib → third-party → local

## Code Style

### Line Length & Indentation
- Maximum 120 characters per line
- 4 spaces (never tabs)
- Use hanging indents for long function calls

### Quote Style
**CRITICAL:** Always use single quotes for strings (except docstrings use triple double quotes)

### Whitespace
- Space around operators: `x = 1 + 2`
- No space around keyword args: `func(arg=value)`
- No space before colon: `items[start:end]`
- Space after comma: `[1, 2, 3]`

### Blank Lines
- 2 blank lines between top-level functions and classes
- 1 blank line between methods in a class

## Naming Conventions

- **Variables/functions:** `snake_case`
- **Classes:** `PascalCase`
- **Constants:** `UPPER_SNAKE_CASE`
- **Private members:** `_leading_underscore`
- **Modules:** `lowercase` or `snake_case`

## Type Hints

Always use type hints for function signatures. Use modern Python 3.10+ syntax with `|` for unions.

**Preferred union syntax:** `str | None` (not `Optional[str]`)

**Collection types:** Use lowercase generics
- `list[str]` not `List[str]`
- `dict[str, Any]` not `Dict[str, Any]`
- `tuple[int, str]` not `Tuple[int, str]`

**Always specify return types** including `None`

## Docstrings

Use Google-style docstrings for all public functions, classes, and methods.

### Module Docstrings
Every module needs:
- Description with key features
- Usage examples
- Author attribution

### Function Docstrings
Include sections as needed:
- **Args:** Parameter descriptions
- **Returns:** Return value description
- **Raises:** Exception descriptions

### One-Line Docstrings
Acceptable for simple functions

## Module Structure

Organize modules in this order:
1. Module docstring with author
2. Imports (stdlib → third-party → local)
3. Module-level constants
4. Logger initialization
5. Module-level private functions
6. Public functions
7. Classes
8. Main/entry point (if applicable)

### `__all__` Exports
Define `__all__` to explicitly specify public API

## Import Organization

Three groups separated by blank lines:
1. Standard library imports
2. Third-party imports
3. Local application imports (relative)

**Best practices:**
- Import modules, not everything with `*`
- Use relative imports within package: `from . import config`
- Handle platform-specific imports gracefully

**Conditional imports:** Use try/except with helpful error messages for optional dependencies

## String Formatting

**REQUIRED:** Always use f-strings with single quotes for string interpolation

**Multi-line f-strings:** Use parentheses for continuation

**Path operations:** Prefer `Path` over string concatenation

## File Operations

**Use pathlib.Path** instead of `os.path`

**Always specify encoding:** Use `encoding='utf-8'` for all file operations

**Existence checks:** Use `.exists()`, `.is_file()`, `.is_dir()` methods

## Logging

**Use module-level logger:** `logger = logging.getLogger('pyagentvox')`

**Log levels:**
- **DEBUG:** Detailed diagnostic info
- **INFO:** General informational messages
- **WARNING:** Warnings (but continue)
- **ERROR:** Errors (but continue)
- **CRITICAL:** Serious errors (usually exit after)

**Avoid print statements:** Use logging instead (except for CLI output)

## Summary Checklist

- [ ] Line length ≤ 120 characters
- [ ] Single quotes for strings (except docstrings)
- [ ] F-strings with single quotes for formatting
- [ ] Type hints on all function signatures using `|` for unions
- [ ] Google-style docstrings with Args/Returns/Raises
- [ ] Module docstring with usage example and author
- [ ] Imports organized: stdlib → third-party → local
- [ ] `__all__` defined for public modules
- [ ] Use `pathlib.Path` instead of `os.path`
- [ ] Use logging instead of print (except CLI output)
