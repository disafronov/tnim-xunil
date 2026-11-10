import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.prune_apt import prune


class PruneAptTests(unittest.TestCase):
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
