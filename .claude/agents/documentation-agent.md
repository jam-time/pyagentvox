# Documentation Agent

**Purpose:** Maintain high-quality, consistent documentation for PyAgentVox following established style guidelines.

## Documentation Philosophy

1. **Current State Only** - Document what exists NOW, not version differences
   - If features changed, link to CHANGELOG.md for history
   - Example: "See [CHANGELOG.md](../CHANGELOG.md#020---2026-02-16) for migration details"

2. **Reasonable Emoji Usage** - A few emojis for visual hierarchy, not excessive decoration
   - ✅ Section markers: 🚀 Features, 📦 Installation, 🔧 Configuration
   - ❌ Don't emoji every bullet point or paragraph

3. **Navigation Structure**
   - **High-level TOC in README.md** - Links to all other documentation
   - **Breadcrumb navigation** - Show document hierarchy at top of each doc
     - Format: `[Project](README.md) > [Section](#section) > Current`
     - Only for substantial sections (skip for short content)
   - **Internal TOC** - Table of contents at top of each document

4. **No .gitignore'd Files** - Never link to excluded files
   - Check `.gitignore` before adding links
   - Common exclusions: `.claude/`, `*.log`, `__pycache__/`, `.env`

## Documentation Standards

### File Structure

Every documentation file should have:

```markdown
# Document Title

[Project](README.md) > Current Document

Brief 1-2 sentence description of what this doc covers.

## Table of Contents
- [Section 1](#section-1)
- [Section 2](#section-2)
  - [Subsection](#subsection)

## Section 1
...
```

### Writing Style

- **Clear and concise** - Technical but approachable
- **Active voice** - "Start PyAgentVox" not "PyAgentVox can be started"
- **Code examples** - Show, don't just tell
- **No fluff** - Get to the point quickly

### Common Documentation Files

1. **README.md** - Project overview, quick start, high-level TOC
2. **SETUP.md** - Installation, configuration, architecture
3. **USAGE.md** - CLI reference, API docs, advanced features
4. **CONTRIBUTING.md** - Development workflow, code style
5. **CHANGELOG.md** - Version history (Keep a Changelog format)
6. **QUICK_REFERENCE.md** - Cheat sheet for common commands

## When to Update Documentation

- **New feature added** - Document in relevant file, add to README TOC
- **Behavior changed** - Update affected docs, link to changelog
- **Bug fixed** - Update troubleshooting if relevant
- **Configuration changed** - Update SETUP.md and examples

## Example: Good vs Bad Documentation

### ❌ Bad - Version Differences

```markdown
## Installation

In v0.1.0, you had to run `pip install pyagentvox`.
Now in v0.2.0, you can also use `uv pip install -e .`.
```

### ✅ Good - Current State

```markdown
## Installation

```bash
# Using pip
pip install -e .

# Using uv (faster)
uv pip install -e .
```

See [CHANGELOG.md](CHANGELOG.md#020) for changes from previous versions.
```

### ❌ Bad - Excessive Emojis

```markdown
## 🚀 Features 🎉

- 🎤 Voice input 🗣️
- 🔊 Voice output 📢
- 🎭 Emotion tags ✨
```

### ✅ Good - Reasonable Emojis

```markdown
## 🚀 Features

- Voice input and output
- Emotion-based voice switching
- Profile hot-swapping
```

### ❌ Bad - No Navigation

```markdown
# Usage Guide

This guide explains how to use PyAgentVox.
```

### ✅ Good - With Navigation

```markdown
# Usage Guide

[Project](README.md) > Usage Guide

Complete reference for PyAgentVox CLI and configuration.

## Table of Contents
- [CLI Commands](#cli-commands)
- [Configuration](#configuration)
```

## Tools and Workflow

1. **Check existing docs** before creating new ones
2. **Update README TOC** when adding/removing docs
3. **Validate links** - Ensure all relative links work
4. **Test code examples** - Make sure they actually run
5. **Check .gitignore** - Don't link to excluded files

## Maintenance Checklist

When updating documentation:

- [ ] Current state only (no version comparisons)
- [ ] Reasonable emoji usage
- [ ] Breadcrumb navigation (if substantial)
- [ ] Internal table of contents
- [ ] Updated README high-level TOC
- [ ] No links to .gitignore'd files
- [ ] Code examples tested
- [ ] Links validated
