# Avatar Tags Skill

Query and filter Luna's avatar images by tag. See what tags are available, apply filters to control which images display, and check current filter state.

## Usage

```bash
/avatar-tags [command] [options]
```

## Commands

### List All Tags

Show all available tags organized by category with image counts:

```bash
/avatar-tags list
```

Output shows tags grouped into:
- **Emotions** - cheerful, excited, calm, etc.
- **Outfits** - dress, daisy-dukes, tank-top, etc.
- **Other** - glasses, standing, flirty, etc.

### Apply Filters

Control which avatar images are displayed:

```bash
# Show only images with specific tags
/avatar-tags filter --include casual,summer

# Hide images with specific tags
/avatar-tags filter --exclude formal,ball-gown

# Combine include and exclude
/avatar-tags filter --include dress --exclude formal

# Require ALL include tags (default: ANY)
/avatar-tags filter --include casual,dress --require-all

# Clear all filters
/avatar-tags filter --reset
```

### Show Current Filters

Check what filters are currently active:

```bash
/avatar-tags current
```

## Examples

```bash
# See what tags are available
/avatar-tags list

# Switch to casual summer outfit images
/avatar-tags filter --include daisy-dukes,casual

# Hide all formal outfits
/avatar-tags filter --exclude formal,ball-gown

# Check active filters
/avatar-tags current

# Clear filters to show everything
/avatar-tags filter --reset
```

## Requirements

- PyAgentVox must be running for filter commands (start with `/voice`)
- Tag listing works anytime (reads config file directly)

## Behind the Scenes

This skill calls `python -m pyagentvox.avatar_tags` with the appropriate subcommand. Filters are applied via IPC temp files that the running avatar widget monitors.
