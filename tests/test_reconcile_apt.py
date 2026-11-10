import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.reconcile_apt import binary_source, maintained_sources, reconcile


class ReconcileAptTests(unittest.TestCase):
    def test_source_field_with_version(self):
        with patch("scripts.reconcile_apt.subprocess.check_output", return_value="calendar (1.0)\n"):
            self.assertEqual(binary_source(Path("binary.deb")), "calendar")

    def test_binary_name_fallback_when_source_field_absent(self):
        with patch("scripts.reconcile_apt.subprocess.check_output", side_effect=["", "calendar-data\n"]):
            self.assertEqual(binary_source(Path("binary.deb")), "calendar-data")

    def test_removes_all_versions_and_binary_names_for_retired_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pool = root / "pool"
            pool.mkdir()
            packages = root / "packages"
            (packages / "kept").mkdir(parents=True)
            (packages / "kept" / "package.yaml").write_text("source:\n  package: kept\n")
            sources = {
                "old-a.deb": "retired",
                "old-b.deb": "retired",
                "old-data.deb": "retired",
                "kept.deb": "kept",
            }
            for name in sources:
                (pool / name).write_bytes(b"deb")
            with patch("scripts.reconcile_apt.binary_source", side_effect=lambda p: sources[p.name]):
                removed = reconcile(pool, packages)
            self.assertEqual({p.name for p in removed}, {"old-a.deb", "old-b.deb", "old-data.deb"})
            self.assertEqual({p.name for p in pool.iterdir()}, {"kept.deb"})

    def test_rename_keeps_binaries_when_source_is_still_maintained(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pool = root / "pool"
            pool.mkdir()
            (pool / "old-name.deb").write_bytes(b"deb")
            packages = root / "packages"
            (packages / "new-directory").mkdir(parents=True)
            (packages / "new-directory" / "package.yaml").write_text("source:\n  package: same-source\n")
            with patch("scripts.reconcile_apt.binary_source", return_value="same-source"):
                self.assertEqual(reconcile(pool, packages), [])
            self.assertTrue((pool / "old-name.deb").exists())

    def test_removed_manifest_retires_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pool = root / "pool"
            pool.mkdir()
            (pool / "old.deb").write_bytes(b"deb")
            with patch("scripts.reconcile_apt.binary_source", return_value="old"):
                self.assertEqual(len(reconcile(pool, root / "packages")), 1)

    def test_duplicate_source_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("one", "two"):
                folder = root / name
                folder.mkdir()
                (folder / "package.yaml").write_text("source:\n  package: same\n")
            with self.assertRaisesRegex(ValueError, "Duplicate maintained source"):
                maintained_sources(root)


if __name__ == "__main__":
    unittest.main()
