import tempfile
import unittest
from pathlib import Path

from scripts.detect_changes import detect


class DetectChangesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "packages"
        for name in ("gnome-calendar", "nemo"):
            (self.root / name).mkdir(parents=True)

    def test_single_package(self):
        self.assertEqual(detect(["packages/nemo/patches/fix.patch"], self.root), ["nemo"])

    def test_multiple_packages(self):
        self.assertEqual(detect(["packages/nemo/package.yaml", "packages/gnome-calendar/patches/a.patch", "packages/nemo/x"], self.root), ["gnome-calendar", "nemo"])

    def test_deleted_package(self):
        self.assertEqual(detect(["packages/deleted/package.yaml"], self.root), [])

    def test_shared_script(self):
        self.assertEqual(detect(["scripts/build-package.sh"], self.root), ["gnome-calendar", "nemo"])

    def test_build_workflow(self):
        self.assertEqual(detect([".github/workflows/build.yml"], self.root), ["gnome-calendar", "nemo"])

    def test_publish_workflow(self):
        self.assertEqual(detect([".github/workflows/publish.yml"], self.root), ["gnome-calendar", "nemo"])

    def test_unrelated(self):
        self.assertEqual(detect(["README.md", ".github/dependabot.yml"], self.root), [])


if __name__ == "__main__":
    unittest.main()
