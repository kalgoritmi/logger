import shutil
import unittest
from pathlib import Path

from utilities import get_existing_backups, get_last_rollover_seq


class TestBase:
    """Testcase base class provides common setUp and tearDown fixtures."""

    def setUp(self):
        """Set up test directory."""
        self.test_dir = Path("./test_logs")
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True)

    def tearDown(self):
        """Clean up test directory."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)


class TestUtilities(TestBase, unittest.TestCase):
    def test_no_backups(self):
        """Test utilities on no rolled over backups."""
        log_path = self.test_dir / "test.bin"
        log_path.touch()
        self.assertEqual(get_existing_backups(log_path), [])
        self.assertEqual(get_last_rollover_seq(log_path), -1)

    def test_single_backup(self):
        """Test utilities on single rollover backup."""
        log_path = self.test_dir / "test.bin"
        backup = self.test_dir / "test.0.bin"
        log_path.touch()
        backup.touch()
        self.assertEqual(len(get_existing_backups(log_path)), 1)
        self.assertEqual(get_last_rollover_seq(log_path), 0)

    def test_multiple_backups(self):
        """Test utilities on multiple rollover backups."""
        log_path = self.test_dir / "test.bin"
        for i in range(5):
            (self.test_dir / f"test.{i}.bin").touch()
        self.assertEqual(len(get_existing_backups(log_path)), 5)
        self.assertEqual(get_last_rollover_seq(log_path), 4)

    def test_sorted(self):
        """Test `get_existing_backups` sorted numerically, not just alphabetically."""
        log_path = self.test_dir / "test.bin"
        for i in [3, 0, 2, 1]:
            (self.test_dir / f"test.{i}.bin").touch()
        backups = get_existing_backups(log_path, sort=True)
        self.assertEqual(
            [b.name for b in backups],
            ["test.0.bin", "test.1.bin", "test.2.bin", "test.3.bin"],
        )

    def test_ignores_non_numeric(self):
        """Test `get_existing_backups`, picks only numeric sequences in backup names."""
        log_path = self.test_dir / "test.bin"
        (self.test_dir / "test.0.bin").touch()
        (self.test_dir / "test.a.bin").touch()
        (self.test_dir / "test.b.bin").touch()
        self.assertEqual(len(get_existing_backups(log_path)), 1)


if __name__ == "__main__":
    unittest.main()
