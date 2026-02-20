# Python Patterns - PyAgentVox

Advanced patterns for async, error handling, resource management, and Python techniques.

## Error Handling

### Exception Types
Use specific exception types: `FileNotFoundError`, `ValueError`, `RuntimeError`, etc.

**Never use bare except** - it catches everything including `KeyboardInterrupt`

### Minimal Error Handling
Only handle errors that can be meaningfully recovered from. Don't wrap everything in try/except.

### Logging Errors
Log errors with appropriate levels and context. Use `logger.error()` with exception details.

### Exception Chaining
Use `from` to chain exceptions and preserve traceback: `raise ValueError(...) from e`

### Context Suppression
Use `contextlib.suppress(ExceptionType)` for expected exceptions you want to ignore

## Async/Await Patterns

### Async Function Definitions
Use `async def` for async functions. Call with `await`.

### Parallel Execution
Use `asyncio.gather()` for parallel async operations

**Pattern:** Generate in parallel, process sequentially when order matters

### Timeouts
Use `asyncio.wait_for(coroutine, timeout=seconds)` for timeouts

### Mixing Sync and Async
Run blocking code in threads using `threading.Thread` with `daemon=True`

**Pattern:** Speech recognition in thread, async tasks in event loop

## Resource Management

### Context Managers
Use context managers for resource cleanup: `with open(...) as f:`

**NamedTemporaryFile:** Use `delete=False` if you need to keep temp files

### Cleanup Functions
Register cleanup with `atexit.register(cleanup_func)`

**Pattern:** PyAgentVox cleanup - stop subprocesses, remove temp files, remove PID lock

### Custom Context Managers
Use `@contextmanager` decorator from `contextlib` for custom context managers

## Advanced Techniques

### Comprehensions and Generators
- **List comprehensions:** `[transform(x) for x in data if x.valid]`
- **Dict comprehensions:** `{k: process(v) for k, v in items.items()}`
- **Generator expressions:** Memory efficient, use when you don't need the full list
- **Generator functions:** Use `yield` for streaming data

### Dataclasses and Slots
- **Dataclasses:** Use `@dataclass` for simple data containers
- **Slots:** Use `__slots__` for memory efficiency on classes with many instances
- **Frozen:** Use `frozen=True` for immutable dataclasses

### Properties and Descriptors
Use `@property` for computed attributes and validation on setters

### Functools Advanced Usage
- **Caching:** `@functools.lru_cache(maxsize=128)` for expensive functions
- **Partial application:** `functools.partial(func, arg1=value)`
- **Single dispatch:** `@functools.singledispatch` for polymorphism based on type

## Common Patterns in PyAgentVox

### Parallel TTS Generation
Generate all emotion segments in parallel with `asyncio.gather()`, play sequentially

### Background Threads
Speech recognition runs in separate thread because it's blocking, async tasks in event loop

### PID File Locking
Check existing PID, validate with psutil, create new lock, register cleanup

### Subprocess Management
Launch with `subprocess.Popen`, track for cleanup, terminate in `atexit` handler

### Voice Injector
Capture window handle once with `--use-foreground`, send messages to that handle even when focus changes

## Best Practices

- Use context managers and atexit for reliable cleanup
- Chain exceptions with `from` to preserve tracebacks
- Use specific exception types, not bare except
- Run blocking code in threads from async context
- Use `asyncio.gather()` for parallel operations
- Cache expensive operations with `@lru_cache`
- Use dataclasses for simple data containers
- Prefer generators for large datasets
