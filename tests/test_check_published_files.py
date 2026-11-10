import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from scripts.check_published_files import check


class PublishedFilesTests(unittest.TestCase):
    def test_valid_required_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = root / "key.asc"
            html = root / "index.html"
            key.write_bytes(b"key")
            html.write_bytes(b"html")
            files = {
                "Release": b"release",
                "Release.gpg": b"signature",
                "InRelease": b"clearsigned",
                "tnim-xunil.asc": b"key",
                "index.html": b"html",
            }
            def fetch(url):
                return files[url.rsplit("/", 1)[-1]]
            def run(command, **kwargs):
                if "--output" in command:
                    output = Path(command[command.index("--output") + 1])
                    if output.name == "signed-content":
                        output.write_bytes(b"release")
                return None
            with patch("scripts.check_published_files.fetch", side_effect=fetch), patch(
                "scripts.check_published_files.subprocess.run", side_effect=run
            ) as command:
                self.assertTrue(check("https://example.org/repo/", key, html))
                self.assertEqual(command.call_count, 3)

    def test_missing_required_file_requests_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            key = Path(tmp, "key.asc")
            html = Path(tmp, "index.html")
            key.write_bytes(b"key")
            html.write_bytes(b"html")
            def fetch(url):
                if url.endswith("/Release.gpg"):
                    raise HTTPError(url, 404, "Not Found", {}, None)
                return b"other"
            with patch("scripts.check_published_files.fetch", side_effect=fetch):
                self.assertFalse(check("https://example.org/repo/", key, html))

    def test_changed_html_requests_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            key = Path(tmp, "key.asc")
            html = Path(tmp, "index.html")
            key.write_bytes(b"key")
            html.write_bytes(b"new")
            files = {"Release": b"release", "Release.gpg": b"sig", "InRelease": b"signed",
                     "tnim-xunil.asc": b"key", "index.html": b"old"}
            with patch("scripts.check_published_files.fetch", side_effect=lambda url: files[url.rsplit("/", 1)[-1]]):
                self.assertFalse(check("https://example.org/repo/", key, html))


if __name__ == "__main__":
    unittest.main()
