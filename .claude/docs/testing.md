# Python Testing Guide - PyAgentVox

Testing patterns and best practices for PyAgentVox using pytest.

## Test Organization

### File Structure
- Place tests in `tests/` directory
- Name test files `test_*.py`
- Group tests into classes: `class TestClassName:`
- Include module docstring explaining what's being tested

### Test Naming
Use descriptive test names that explain what's being tested:
- `test_send_text_without_focus_stealing()`
- `test_empty_text_handling()`
- `test_special_characters_handling()`

**Bad names:** `test_1()`, `test_text()`

## Fixtures

### Pytest Fixtures
Use `@pytest.fixture` for reusable test setup

**Pattern:** Create temp files with `tempfile.NamedTemporaryFile`

### Fixture Cleanup
Yield in fixtures, cleanup after yield block

## Mocking

### Mock External Dependencies
Use `unittest.mock.patch` for external dependencies

**Pattern:** Mock Windows APIs (win32gui, win32api) for cross-platform testing

### Mock Setup
Configure mocks with `.return_value` for sync or `.return_value = awaitable` for async

**Pattern:** Mock window handles, return values for GetForegroundWindow, etc.

## Assertions

### Descriptive Assertions
Use descriptive assertion messages: `assert result, 'VoiceInjector failed to send text'`

**Pytest assertions** are already descriptive, but add messages for complex cases

### Common Assertions
- `assert value == expected`
- `assert value is True` (not `assert value == True`)
- `assert 'substring' in string`
- `assert len(collection) == expected_count`

### Mock Assertions
- `.assert_called()` - verify method was called
- `.assert_called_once()` - verify called exactly once
- `.assert_not_called()` - verify NOT called (important for focus stealing tests)
- `.assert_called_with(args)` - verify called with specific args

## PyAgentVox-Specific Patterns

### Windows API Mocking
Mock win32 modules for testing. Set return values for window handles.

**Key test:** Verify focus is NOT stolen by checking `SetForegroundWindow.assert_not_called()`

### Background Typing Test Scenario
1. Capture window with foreground flag
2. Switch focus to different window
3. Verify messages sent to original window (not current focus)

### File-Based Testing
Use `tempfile.NamedTemporaryFile` for file-based tests. Clean up after test.

### Temp File Cleanup
Always use `Path.unlink(missing_ok=True)` in cleanup to avoid errors if file doesn't exist

## Test Commands

```bash
pytest                          # Run all tests
pytest tests/test_injection.py  # Run specific test file
pytest -v                       # Verbose output
pytest --cov=pyagentvox        # With coverage report
pytest -k "test_background"    # Run tests matching pattern
```

## Best Practices

- Use fixtures for reusable test setup
- Mock external dependencies (APIs, Windows functions, etc.)
- Verify behavior with `.assert_*` methods on mocks
- Use descriptive test names and assertion messages
- Clean up temp files and resources after tests
- Test both success and failure cases
- Test edge cases (empty input, special characters, etc.)
