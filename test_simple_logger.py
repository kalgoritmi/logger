"""Unittest for BinaryLogger multithreading behavior."""

from collections import defaultdict
from pathlib import Path
from threading import Thread
import re
import unittest

from simple_logger import BinaryLogger
from utilities import get_existing_backups, get_last_rollover_seq
from test_utilities import TestBase

class TestMultithreading(TestBase, unittest.TestCase):
    """Test thread safety of BinaryLogger."""

    def test_concurrent_writes(self):
        """Test multiple threads writing to a single logger instance."""
        num_threads = 3
        writes_per_thread = 10
        path = self.test_dir / "events.bin"

        logger = BinaryLogger(path, max_file_size=5000)

        def worker_closure(_id: int):
            for i in range(writes_per_thread):
                message = f"Worker {_id} | Message {i}"
                logger.write(message)

        threads = []
        for i in range(num_threads):
            t = Thread(target=worker_closure, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        messages = list(logger.read())
        logger.close()

        expected = num_threads * writes_per_thread
        self.assertEqual(
            len(messages),
            expected,
            f"Expected {expected} messages, got {len(messages)}",
        )

        message_counter = defaultdict(list)
        worker_regex = re.compile(r"Worker (\d+) \| Message (\d+)")
        for msg in messages:
            matches = worker_regex.fullmatch(msg)
            self.assertIsNotNone(matches, f"Corrupted message: {msg}")

            worker_id = int(matches.group(1))
            message_counter[int(worker_id)].append(int(matches.group(2)))

        write_ids = list(range(writes_per_thread))
        for i in range(num_threads):
            message_count = len(message_counter[i])
            self.assertEqual(
                message_counter[i],
                write_ids,
                f"Incorrect message count {message_count} for worker #{i}",
            )

    def test_rollover_during_concurrent_writes(self):
        """Test file rollover works correctly with concurrent writes."""
        num_threads = 5
        writes_per_thread = 2
        path = self.test_dir / "rollover.bin"
        max_file_size = 100

        logger = BinaryLogger(path, max_file_size=max_file_size)

        chars_per_write: int = 50

        def worker():
            for _ in range(writes_per_thread):
                message = chars_per_write * "a"
                logger.write(message)

        threads = []
        for i in range(num_threads):
            t = Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        messages = list(logger.read(path))
        logger.close()

        expected = num_threads * writes_per_thread
        self.assertEqual(
            len(messages),
            expected,
            f"Expected {expected} messages after rollover, got {len(messages)}",
        )

        backup_count = get_last_rollover_seq(path) + 1
        expected_backup_count = int(chars_per_write * expected / max_file_size)
        self.assertEqual(
            backup_count,
            expected_backup_count,
            f"Expected {expected_backup_count} backup logs, got {backup_count}",
        )


class TestLoggerBasic(TestBase, unittest.TestCase):
    """Test single-threaded edge cases and basic functionality."""

    def test_basic_write_read(self):
        """Test basic write and read operations."""
        log_path = str(self.test_dir / "basic.bin")
        logger = BinaryLogger(log_path, max_file_size=1000)

        messages = ["Message 1", "Message 2", "Message 3"]
        for msg in messages:
            logger.write(msg)

        result = list(logger.read(log_path))
        logger.close()

        self.assertEqual(result, messages)

    def test_empty_log(self):
        """Test reading from empty log file."""
        path = self.test_dir / "empty.bin"
        logger = BinaryLogger(path, max_file_size=1000)

        result = list(logger.read(path))
        logger.close()

        self.assertEqual(result, [])

    def test_single_rollover(self):
        """Test single file rollover."""
        path = self.test_dir / "rollover.bin"
        max_size = 100

        logger = BinaryLogger(path, max_file_size=max_size)

        messages = []
        for i in range(20):
            msg = f"Message {i}" + "x" * 20
            messages.append(msg)
            logger.write(msg)
        logger.close()

        backup_path = Path(path).with_suffix(".0.bin")
        self.assertTrue(backup_path.exists(), "Backup file should exist after rollover")

        reader = BinaryLogger(path, max_file_size=max_size)
        result = list(reader.read(path))
        reader.close()

        self.assertEqual(result, messages)

    def test_multiple_rollovers(self):
        """Test multiple file rollovers."""
        path = self.test_dir / "multi_rollover.bin"
        max_size = 50

        logger = BinaryLogger(path, max_file_size=max_size)

        messages = []
        for i in range(50):
            msg = 10 * "m"
            messages.append(msg)
            logger.write(msg)
        logger.close()

        # Verify multiple backup files exist
        backup_files = get_existing_backups(logger.file_path)
        self.assertGreater(len(backup_files), 1, "Multiple backup files should exist")

        # Verify all messages preserved
        reader = BinaryLogger(path, max_file_size=max_size)
        result = list(reader.read(path))
        reader.close()

        self.assertEqual(result, messages)

    def test_empty_string(self):
        """Test writing empty strings."""
        path = self.test_dir / "empty_string.bin"
        logger = BinaryLogger(path, max_file_size=1000)

        messages = ["", "non-empty", "", "another"]
        for msg in messages:
            logger.write(msg)
        logger.close()

        reader = BinaryLogger(path, max_file_size=1000)
        result = list(reader.read(path))
        reader.close()

        self.assertEqual(result, messages)

    def test_context_manager(self):
        """Test context manager protocol."""
        path = self.test_dir / "context.bin"

        messages = ["Message 1", "Message 2"]
        with BinaryLogger(path, max_file_size=1000) as logger:
            for msg in messages:
                logger.write(msg)

        reader = BinaryLogger(path, max_file_size=1000)
        result = list(reader.read(path))
        reader.close()

        self.assertEqual(result, messages)

    def test_write_after_close(self):
        """Test writing after logger is closed raises error."""
        path = self.test_dir / "closed.bin"
        logger = BinaryLogger(path, max_file_size=1000)
        logger.close()

        with self.assertRaises(RuntimeError):
            logger.write("Should fail")

    def test_parent_directory_creation(self):
        """Test that parent directories are created automatically."""
        path = self.test_dir / "nested" / "test.bin"

        logger = BinaryLogger(path, max_file_size=1000)
        logger.write("Test message")
        logger.close()

        self.assertTrue(Path(path).exists())
        self.assertTrue(Path(path).parent.exists())

    def test_rollover_numbering(self):
        """Test backup file numbering is sequential."""
        log_path = self.test_dir / "numbering.bin"
        max_size = 50

        logger = BinaryLogger(log_path, max_file_size=max_size)

        for i in range(30):
            logger.write(f"Message {i}" + "a" * 20)

        backups = get_existing_backups(log_path, sort=True)

        self.assertGreater(len(backups), 0, "Should have backup files")
        for i, backup in enumerate(backups):
            stem_parts = backup.stem.split(".")
            backup_num = int(stem_parts[-1])
            self.assertEqual(backup_num, i, f"Backup should be numbered {i}")

    def test_special_characters(self):
        """Test messages with special characters."""
        path = self.test_dir / "special.bin"
        logger = BinaryLogger(path, max_file_size=1000)

        messages = [
            "Line\ntest",
            "Tab\ttest",
            "Null\x00test",
            'Quote"test',
            "Backslash\\test",
            "RecordSeparator\x1etest",
        ]

        for msg in messages:
            logger.write(msg)
        logger.close()

        reader = BinaryLogger(path, max_file_size=1000)
        result = list(reader.read(path))
        reader.close()

        self.assertEqual(result, messages)


if __name__ == "__main__":
    unittest.main()
