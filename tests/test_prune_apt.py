import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.prune_apt import prune, fields, compare


class PruneAptTests(unittest.TestCase):
    def test_reads_actual_dpkg_deb_field_values(self):
        with patch("scripts.prune_apt.subprocess.check_output", side_effect=[
            "gnome-calendar\n", "46.1-1mint2+zara\n", "amd64\n"
        ]) as command:
            self.assertEqual(fields(Path("calendar.deb")), ("gnome-calendar", "46.1-1mint2+zara", "amd64"))
            self.assertEqual(command.call_count, 3)
            self.assertEqual(command.call_args_list[1].args[0], [
                "dpkg-deb", "--field", "calendar.deb", "Version"
            ])

    def test_rejects_invalid_package_metadata(self):
        with patch("scripts.prune_apt.subprocess.check_output", return_value=""):
            with self.assertRaises(ValueError):
                fields(Path("calendar.deb"))

    def test_invalid_version_comparison_is_fatal(self):
        with self.assertRaises(subprocess.CalledProcessError):
            compare("Version: 1.0", "Version: 2.0")

    def test_retains_two_newest_versions_per_package_and_architecture(self):
        with tempfile.TemporaryDirectory() as tmp:
            pool = Path(tmp)
            versions = {
                "a1.deb": ("calendar", "1.0", "amd64"),
                "a2.deb": ("calendar", "1.2", "amd64"),
                "a3.deb": ("calendar", "1.10", "amd64"),
                "b1.deb": ("calendar", "1.0", "arm64"),
                "c1.deb": ("other", "1.0", "amd64"),
            }
            for filename in versions:
                (pool / filename).write_bytes(b"x")
            with patch("scripts.prune_apt.fields", side_effect=lambda p: versions[p.name]):
                prune(pool)
            self.assertEqual(
                {p.name for p in pool.glob("*.deb")},
                {"a2.deb", "a3.deb", "b1.deb", "c1.deb"},
            )

    def test_duplicate_binary_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            pool = Path(tmp)
            for name in ("a.deb", "b.deb"):
                (pool / name).write_bytes(b"x")
            with patch("scripts.prune_apt.fields", return_value=("calendar", "1.0", "amd64")):
                with self.assertRaises(ValueError):
                    prune(pool)


if __name__ == "__main__":
    unittest.main()
