# Avatar Hover Features - Implementation Plan

## Overview

Add two interactive features to the avatar widget:
1. **Hover Lock** - Pause image cycling when mouse hovers over avatar
2. **Tag Editor** - Interactive tag editing with checklist UI

## Feature 1: Hover Lock

### Behavior

- **Mouse enters avatar** → Pause variant cycling, lock current image
- **Mouse leaves avatar** → Resume variant cycling
- **Works with control buttons** → Control buttons should still work normally

### Implementation

**In `avatar_widget.py`:**

```python
def __init__(self, ...):
    # ... existing init ...
    self._hover_locked = False
    self._was_cycling = False  # Track if we were cycling before hover

    # Bind hover events
    self.canvas.bind('<Enter>', self._on_mouse_enter)
    self.canvas.bind('<Leave>', self._on_mouse_leave)

def _on_mouse_enter(self, event):
    """Pause cycling when mouse enters avatar."""
    if self._cycle_task and not self._hover_locked:
        self._was_cycling = True
        self._hover_locked = True
        # Cancel cycle timer
        if hasattr(self, '_cycle_timer_id') and self._cycle_timer_id:
            self.root.after_cancel(self._cycle_timer_id)
            self._cycle_timer_id = None
        logger.debug('[AVATAR] Hover lock engaged')

def _on_mouse_leave(self, event):
    """Resume cycling when mouse leaves avatar."""
    if self._hover_locked:
        self._hover_locked = False
        # Resume cycling if it was active
        if self._was_cycling:
            self._schedule_next_cycle()
            self._was_cycling = False
        logger.debug('[AVATAR] Hover lock released')

def _schedule_next_cycle(self):
    """Schedule next variant cycle."""
    if self.cycle_interval > 0 and not self._hover_locked:
        self._cycle_timer_id = self.root.after(
            self.cycle_interval,
            self._cycle_variants
        )

def _cycle_variants(self):
    """Cycle to next variant (respect hover lock)."""
    if self._hover_locked:
        return  # Don't cycle while hovering

    # ... existing cycling logic ...

    # Schedule next cycle
    self._schedule_next_cycle()
```

**Edge Cases:**
- Control buttons appearing/disappearing shouldn't interfere
- Hover lock should work even if not actively cycling
- Emotion changes should still work during hover lock

## Feature 2: Tag Editor Button

### UI Design

**Button:**
- Small "🏷️" or "Tags" button in top-right corner of avatar
- Only visible when mouse hovers over avatar
- Positioned: `(avatar_width - 40, 10)` offset from canvas top-right
- Button size: 30x30 pixels
- Background: semi-transparent gray with border
- Hover effect: slightly lighter background

**Tag Editor Popup:**
```
┌─────────────────────────────────────┐
│ Edit Tags - filename.png            │
├─────────────────────────────────────┤
│ Description: [one-line description] │
├─────────────────────────────────────┤
│ Tags:                               │
│ ┌─────────────────────────────────┐ │
│ │ ☑ cheerful      ☑ dress        │ │
│ │ ☐ excited       ☑ wave         │ │
│ │ ☐ calm          ☐ peace-sign   │ │
│ │ ☑ casual        ☐ victory      │ │
│ │ ... (scrollable)                │ │
│ └─────────────────────────────────┘ │
├─────────────────────────────────────┤
│         [Cancel]  [Apply & Save]    │
└─────────────────────────────────────┘
```

### Implementation

**New class in `avatar_widget.py`:**

```python
class TagEditorDialog:
    """Dialog for editing image tags with checklist UI."""

    def __init__(self, parent, image_entry: ImageEntry, all_tags: set[str],
                 on_save_callback):
        """
        Args:
            parent: Parent tkinter window
            image_entry: Current image being edited
            all_tags: Set of all tags in the system
            on_save_callback: Called with updated tags when saved
        """
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f'Edit Tags - {image_entry.path}')
        self.dialog.geometry('400x500')
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.image_entry = image_entry
        self.all_tags = sorted(all_tags)
        self.on_save = on_save_callback
        self.tag_vars = {}  # tag -> BooleanVar

        self._create_widgets()

    def _create_widgets(self):
        """Create dialog widgets."""
        # Header with filename
        header = tk.Label(
            self.dialog,
            text=f'Editing: {self.image_entry.path}',
            font=('Arial', 10, 'bold'),
            pady=10
        )
        header.pack(fill='x')

        # Description (read-only for now)
        desc_frame = tk.Frame(self.dialog)
        desc_frame.pack(fill='x', padx=10)

        tk.Label(desc_frame, text='Description:', anchor='w').pack(fill='x')
        desc_text = tk.Text(desc_frame, height=2, wrap='word')
        desc_text.insert('1.0', self.image_entry.description)
        desc_text.config(state='disabled')  # Read-only
        desc_text.pack(fill='x')

        # Tags section
        tk.Label(
            self.dialog,
            text='Tags (check/uncheck):',
            font=('Arial', 9, 'bold'),
            pady=5
        ).pack(fill='x', padx=10)

        # Scrollable checklist
        scroll_frame = tk.Frame(self.dialog)
        scroll_frame.pack(fill='both', expand=True, padx=10, pady=5)

        canvas = tk.Canvas(scroll_frame)
        scrollbar = tk.Scrollbar(scroll_frame, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        # Create checkboxes for all tags
        current_tags = self.image_entry.tag_set

        # Separate by category for better organization
        emotion_tags = [t for t in self.all_tags if t in VALID_EMOTIONS]
        control_tags = [t for t in self.all_tags if t.startswith('control-')]
        other_tags = [t for t in self.all_tags
                     if t not in emotion_tags and t not in control_tags]

        # Emotion tags section
        if emotion_tags:
            tk.Label(
                scrollable_frame,
                text='Emotions:',
                font=('Arial', 8, 'bold')
            ).grid(row=0, column=0, columnspan=2, sticky='w', pady=(5, 2))

            for i, tag in enumerate(emotion_tags, start=1):
                var = tk.BooleanVar(value=tag in current_tags)
                self.tag_vars[tag] = var

                cb = tk.Checkbutton(
                    scrollable_frame,
                    text=tag,
                    variable=var,
                    anchor='w'
                )
                cb.grid(row=i, column=0, sticky='w', padx=(10, 5))

        # Other tags in 2 columns
        start_row = len(emotion_tags) + 2
        tk.Label(
            scrollable_frame,
            text='Other Tags:',
            font=('Arial', 8, 'bold')
        ).grid(row=start_row, column=0, columnspan=2, sticky='w', pady=(10, 2))

        for i, tag in enumerate(other_tags):
            var = tk.BooleanVar(value=tag in current_tags)
            self.tag_vars[tag] = var

            row = start_row + 1 + (i // 2)
            col = i % 2

            cb = tk.Checkbutton(
                scrollable_frame,
                text=tag,
                variable=var,
                anchor='w'
            )
            cb.grid(row=row, column=col, sticky='w', padx=(10, 5))

        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Buttons
        btn_frame = tk.Frame(self.dialog)
        btn_frame.pack(fill='x', padx=10, pady=10)

        tk.Button(
            btn_frame,
            text='Cancel',
            command=self.dialog.destroy,
            width=12
        ).pack(side='left', padx=5)

        tk.Button(
            btn_frame,
            text='Apply & Save',
            command=self._save_tags,
            width=12,
            bg='#4CAF50',
            fg='white'
        ).pack(side='right', padx=5)

    def _save_tags(self):
        """Save updated tags and close dialog."""
        # Collect checked tags
        new_tags = [tag for tag, var in self.tag_vars.items() if var.get()]

        # Validate: must have at least one emotion tag
        has_emotion = any(tag in VALID_EMOTIONS for tag in new_tags)
        has_control = any(tag in VALID_CONTROL_TAGS for tag in new_tags)

        if not has_emotion and not has_control:
            messagebox.showerror(
                'Invalid Tags',
                'Image must have at least one emotion tag or control tag!'
            )
            return

        # Call save callback
        self.on_save(new_tags)
        self.dialog.destroy()
```

**Add button to avatar widget:**

```python
class AvatarWidget:
    def __init__(self, ...):
        # ... existing init ...
        self._tag_button = None
        self._tag_button_id = None

    def _on_mouse_enter(self, event):
        """Show tag editor button when hovering."""
        # ... hover lock code ...
        self._show_tag_button()

    def _on_mouse_leave(self, event):
        """Hide tag editor button when leaving."""
        # ... hover unlock code ...
        self._hide_tag_button()

    def _show_tag_button(self):
        """Display tag editor button."""
        if self._tag_button_id:
            return  # Already visible

        # Position in top-right corner
        x = self.canvas.winfo_width() - 40
        y = 10

        # Create button
        self._tag_button_id = self.canvas.create_rectangle(
            x, y, x + 30, y + 30,
            fill='#CCCCCC',
            outline='#666666',
            width=2,
            tags='tag_button'
        )

        text_id = self.canvas.create_text(
            x + 15, y + 15,
            text='🏷️',
            font=('Arial', 12),
            tags='tag_button'
        )

        # Bind click
        self.canvas.tag_bind('tag_button', '<Button-1>', self._open_tag_editor)

    def _hide_tag_button(self):
        """Hide tag editor button."""
        if self._tag_button_id:
            self.canvas.delete('tag_button')
            self._tag_button_id = None

    def _open_tag_editor(self, event=None):
        """Open tag editor dialog."""
        if not self.current_avatar_path:
            return

        # Find current image entry
        current_entry = None
        for img in self.registered_images:
            if img.path == self.current_avatar_path.name:
                current_entry = img
                break

        if not current_entry:
            logger.warning(f'Current image {self.current_avatar_path} not in registry')
            return

        # Get all tags from all images
        all_tags = set()
        for img in self.registered_images:
            all_tags.update(img.tags)

        # Open dialog
        TagEditorDialog(
            self.root,
            current_entry,
            all_tags,
            lambda new_tags: self._save_image_tags(current_entry, new_tags)
        )

    def _save_image_tags(self, image_entry: ImageEntry, new_tags: list[str]):
        """Save updated tags to config file."""
        logger.info(f'[TAGS] Updating {image_entry.path}: {new_tags}')

        # Update in-memory
        image_entry.tags = new_tags

        # Update config file
        try:
            from pyagentvox.avatar_tags import update_image_tags
            update_image_tags(
                self.avatar_dir / image_entry.path,
                new_tags,
                self.config_path
            )
            logger.info('[TAGS] Saved to config')
        except Exception as e:
            logger.error(f'[TAGS] Failed to save: {e}')
            messagebox.showerror('Save Error', f'Failed to save tags: {e}')
```

## Testing Checklist

### Hover Lock
- [ ] Mouse enters avatar → cycling pauses
- [ ] Mouse leaves avatar → cycling resumes
- [ ] Hover lock works when not cycling
- [ ] Control buttons still appear on hover
- [ ] Control button clicks work during hover lock
- [ ] Emotion changes work during hover lock

### Tag Editor
- [ ] Tag button appears on hover (top-right)
- [ ] Tag button disappears on mouse leave
- [ ] Click opens tag editor dialog
- [ ] Dialog shows current image path and description
- [ ] All system tags appear in checklist
- [ ] Current tags are checked
- [ ] Can check/uncheck tags
- [ ] Validation: requires emotion or control tag
- [ ] Apply saves to config file
- [ ] Cancel closes without saving
- [ ] Changes reflected immediately in avatar widget

## Files to Modify

1. **`pyagentvox/avatar_widget.py`**
   - Add hover lock with mouse enter/leave handlers
   - Add tag editor button display/hide logic
   - Add `TagEditorDialog` class
   - Add config save integration

2. **`tests/test_avatar_widget.py`**
   - Test hover lock behavior
   - Test tag button visibility
   - Mock tag editor dialog

## Edge Cases

- **Hover lock during emotion change**: Allow emotion changes even when hover locked
- **Tag editor on unregistered image**: Show warning, don't open dialog
- **No emotion tags selected**: Show validation error
- **Config file write errors**: Show error dialog, keep dialog open
- **Very long tag lists**: Scrollable checklist handles this
- **Tag button position**: Adjust if canvas size changes

## Future Enhancements

- Edit description in tag editor (not just tags)
- Add new custom tags directly from editor
- Bulk tag editing (select multiple images)
- Tag categories with colors
- Search/filter tags in checklist
