from io import BufferedIOBase
from pathlib import Path
from threading import RLock
from typing import Iterator

from utilities import get_existing_backups, get_last_rollover_seq


class LogState:
    """Manages file state and operations for a logger."""

    def __init__(self, file_path: Path | str, max_file_size: int, mode: str = "ab+"):
        """
        Initialize log state, this is used to manage rollovers and current file handle.

        Args:
            file_path, Path | str: Path to the log file, if `str`, convert to Path
            max_file_size, int: Maximum file size before rollover
            mode, str: File open mode, default is append and read in binary mode

        Raises:
            IOError: If the current file cannot be opened
        """
        self.file_path = file_path if isinstance(file_path, Path) else Path(file_path)

        self.max_file_size = max_file_size

        self.mode = mode
        self.is_closed = False

        self.lock = RLock()
        self.next_rollover_seq = max(get_last_rollover_seq(self.file_path)+1, 0)

        self.file_path.parent.mkdir(
            parents=True, exist_ok=True
        )  # ensure parent dirs exist

        self.file_handle = open(self.file_path, mode=self.mode)

    def close(self):
        """Close the file handle."""
        with self.lock:
            if not self.is_closed:
                self.file_handle.close()
                self.is_closed = True

    def rollover(self):
        """Rollover the log file when max size is reached."""
        with self.lock:
            self.close()

            try:
                if self.file_path.exists():
                    backup_path = self.file_path.with_suffix(
                        f".{self.next_rollover_seq}{self.file_path.suffix}"
                    )
                    self.file_path.rename(backup_path)
                    self.next_rollover_seq += 1

                self.file_handle = open(self.file_path, mode=self.mode)
                self.is_closed = False

            except (OSError, IOError):
                self.is_closed = True
                raise


class BinaryLogger:
    """
    Simple binary file logger with automatic rollover when max file size is reached.

    Implements the context manager protocol, and is thread safe.
    """

    def __init__(self, file_path: Path | str, max_file_size: int):
        """
        Initialize the logger.

        Args:
            file_path: Path to the log file
            max_file_size: Maximum file size in bytes before rollover

        Raises:
            IOError: If the file cannot be opened, thrown by `LogState`
        """
        if max_file_size <= 0:
            raise ValueError("Max file size must be positive")

        self.file_path = (
            Path(file_path) if isinstance(file_path, Path) else Path(file_path)
        )
        self.__file_state = LogState(self.file_path, max_file_size)
        self.length_bytesize = 4  # prefix length byte size

    def close(self):
        """Close the logger and release file handle."""
        self.__file_state.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures logger is closed."""
        self.close()
        return False

    def __del__(self):
        """Cleanup on deletion."""
        self.close()

    def __serialize(self, payload: str) -> bytes:
        """Serialize logger state to a string."""
        binary_payload = payload.encode("utf-8", errors="replace")
        binary_payload = (
            len(binary_payload).to_bytes(self.length_bytesize, "big") + binary_payload
        )
        return binary_payload

    def __deserialize(self, file_handle: BufferedIOBase) -> Iterator[str]:
        """Deserialize logger state from a string."""
        while True:
            length_bytes = file_handle.read(self.length_bytesize)

            if len(length_bytes) == 0:
                break  # EOF

            if len(length_bytes) < self.length_bytesize:
                raise IOError("Corrupted log file: incomplete length prefix")

            length = int.from_bytes(length_bytes, "big")
            payload_buffer = file_handle.read(length)

            if len(payload_buffer) != length:
                raise IOError("Corrupted log file: incomplete payload")

            yield payload_buffer.decode("utf-8", errors="replace")

    def write(self, payload: str):
        """
        Write a string payload to the log file.

        Args:
            payload: String to write to the log

        Raises:
            RuntimeError: If logger is closed
            IOError: If write operation fails
        """
        bytes_payload = self.__serialize(payload)
        with self.__file_state.lock:
            if self.__file_state.is_closed:
                raise RuntimeError("Logger is closed and cannot write logs")

            try:
                self.__file_state.file_handle.write(bytes_payload)
                self.__file_state.file_handle.flush()

                current_size = self.__file_state.file_handle.tell()
                if current_size >= self.__file_state.max_file_size:
                    self.__file_state.rollover()

            except (OSError, IOError):
                self.__file_state.is_closed = True
                raise

    def read(
        self, file_path: Path | str | None = None, mode: str = "rb"
    ) -> Iterator[str]:
        """
        Read and iterate through payload instances from the given file,
        including its rollover backup files.

        Args:
            file_path, Path | str | None: Path to the file to read from, if `str` convert to `Path`,
                if `None` read current instance's file and backups
            mode, str: File open mode, default is read in binary mode

        Yields:
            String payloads from the log file(s)

        Raises:
            IOError: If payload data is corrupted (incomplete length prefix or payload),
                backup files that cannot be opened (missing, permissions) are silently skipped.
                This allows partial recovery when some backup files are unavailable.
        """
        if file_path is None:
            file_path = self.file_path

        path = file_path if isinstance(file_path, Path) else Path(file_path)
        existing_backups = get_existing_backups(path, sort=True)

        for backup_path in existing_backups + [path]:
            try:
                with open(backup_path, mode=mode) as file_handle:
                    yield from self.__deserialize(file_handle)
            except (OSError, IOError):
                continue  # skip non readable/corrupted files


def demo():
    """Logger demo, single threaded, common logger instance."""

    events = 10 * [
        "User login: user123",
        "Action performed: file_upload",
        "Data processed: 1024 bytes",
        "User logout: user123",
    ]

    logger = BinaryLogger("./logs/events.bin", 1000)
    for event in events:
        logger.write(event)

    iterator = logger.read("./logs/events.bin")

    print("Rewinding logged events: ", *enumerate(iterator), sep="\n")

    logger.close()


if __name__ == "__main__":
    demo()
