import gzip
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from scripts.restore_apt import restore, records


class RestoreAptTests(unittest.TestCase):
    def test_empty_archive_is_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            def fetch(url):
                if url.endswith("Packages.gz"):
                    return gzip.compress(b"")
                raise HTTPError(url, 404, "No state marker", {}, None)
            with patch("scripts.restore_apt.fetch", side_effect=fetch):
                self.assertEqual(restore("https://example.org/repo/", Path(tmp)), "")
                self.assertEqual(list(Path(tmp).rglob("*.deb")), [])

    def test_download_failure_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("scripts.restore_apt.fetch", side_effect=OSError("network failed")):
                with self.assertRaises(OSError):
                    restore("https://example.org/repo/", Path(tmp))

    def test_missing_index_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("scripts.restore_apt.fetch", side_effect=HTTPError("url", 404, "Not Found", {}, None)):
                self.assertEqual(restore("https://example.org/repo/", Path(tmp)), "")

    def test_missing_binary_requests_source_rebuild(self):
        record = (
            "Package: gnome-calendar-data\nSource: gnome-calendar\n"
            "Filename: pool/missing.deb\nSize: 3\nSHA256: " + "0" * 64 + "\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp, "missing-sources")
            def fetch(url):
                if url.endswith("Packages.gz"):
                    return gzip.compress(record.encode())
                raise HTTPError(url, 404, "Not Found", {}, None)
            with patch("scripts.restore_apt.fetch", side_effect=fetch):
                self.assertEqual(restore("https://example.org/repo/", Path(tmp), output), "")
            self.assertEqual(output.read_text(), "gnome-calendar\n")

    def test_missing_binary_does_not_hide_other_http_errors(self):
        record = "Package: sample\nFilename: pool/sample.deb\nSize: 3\nSHA256: " + "0" * 64 + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            with patch("scripts.restore_apt.fetch", side_effect=[
                gzip.compress(record.encode()),
                HTTPError("url", 503, "Unavailable", {}, None),
            ]):
                with self.assertRaises(HTTPError):
                    restore("https://example.org/repo/", Path(tmp))

    def test_checksum_mismatch_is_fatal(self):
        record = "Package: sample\nFilename: pool/sample.deb\nSize: 3\nSHA256: " + "0" * 64 + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            with patch("scripts.restore_apt.fetch", side_effect=[gzip.compress(record.encode()), b"abc"]):
                with self.assertRaises(ValueError):
                    restore("https://example.org/repo/", Path(tmp))

    def test_restores_verified_package_and_commit(self):
        payload = b"package"
        record = (
            "Package: sample\nFilename: pool/sample.deb\n"
            f"Size: {len(payload)}\nSHA256: {hashlib.sha256(payload).hexdigest()}\n"
        )
        sha = "a" * 40
        with tempfile.TemporaryDirectory() as tmp:
            with patch("scripts.restore_apt.fetch", side_effect=[gzip.compress(record.encode()), payload, sha.encode()]):
                self.assertEqual(restore("https://example.org/repo/", Path(tmp)), sha)
                self.assertEqual((Path(tmp) / "pool/sample.deb").read_bytes(), payload)

    def test_rejects_traversal(self):
        record = "Filename: pool/../../oops.deb\nSize: 1\nSHA256: " + "0" * 64 + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            with patch("scripts.restore_apt.fetch", return_value=gzip.compress(record.encode())):
                with self.assertRaises(ValueError):
                    restore("https://example.org/repo/", Path(tmp))


if __name__ == "__main__":
    unittest.main()
