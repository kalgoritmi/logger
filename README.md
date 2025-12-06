# Binary Logger

A thread-safe binary file logger with automatic rollover functionality.

## Implementation

- **Binary format** with 4 byte length prefixed encoding
- **Automatic rollover** when max file size is reached
- **Thread safe** write operations using RLock
- **Context manager** resource acquisition and cleanup
- **Sequential backup files** (events.0.bin, events.1.bin, ...)

### Local Python

```bash
# Run demo
python simple_logger.py

# Run tests
python -m unittest discover -v
```

### Docker (Multi-Stage Build)

The Dockerfile uses multi-stage builds with three targets: `base`, `test`, and `run`.

```bash
# Build and run tests (tests run during build)
docker build --target test -t logger:test .
# Run tests from test image
docker run logger:test

# Build production image
docker build --target run -t logger:latest .
# Run demo from production image
docker run logger:latest
```

**Build stages:**

- `base`: Common dependencies and source files
- `test`: Runs all tests during build (fails build if tests fail)
- `run`: Production image for running the logger

## Usage Examples

```python
from simple_logger import BinaryLogger

logger = BinaryLogger("./logs/events.bin", max_file_size=1000)

logger.write("User login: user123")
logger.write("Action performed: file_upload")

for message in logger.read("./logs/events.bin"):
    print(message)

logger.close()
```

or

```python
from simple_logger import BinaryLogger

with BinaryLogger("./logs/events.bin", max_file_size=1000) as logger:
    logger.write("User login: user123")
    logger.write("Action performed: file_upload")

    for message in logger.read("./logs/events.bin"):
        print(message)
```

## API

### `BinaryLogger(file_path, max_file_size)`

**Parameters:**

- `file_path` (str | Path): Path to the log file
- `max_file_size` (int): Maximum file size in bytes before rollover

**Methods:**

- `write(payload: str)`: Write a string to the log
- `read(file_path: str | None) -> Iterator[str]`: Read messages from log files
- `close()`: Close the logger and release resources

**Context Manager:**

```python
with BinaryLogger("./logs/tmp.bin", 1000) as logger:
    logger.write("User login: user123")
```

## Architecture

- **LogState**: Manages file handles, rollover state, and thread synchronization
- **BinaryLogger**: Public API for writing and reading log messages
- **Binary Format**: `[4 byte length][UTF8 payload]`

## Testing

**Test Coverage:**

- Basic write/read operations
- File rollover (single and multiple)
- Thread safety (concurrent writes)
- Edge cases (empty strings, special characters, unicode)
- Error handling (write after close)
- Context manager protocol

**Test Suites:**

- `test_simple_logger.py`: Core functionality and edge cases

## Requirements

- Python 3.11+, tested on GIL versions
- No external dependencies (std lib)
