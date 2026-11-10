import gzip
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from scripts.restore_apt import restore, records, verify_index


class RestoreAptTests(unittest.TestCase):
    def test_empty_archive_is_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            def fetch(url):
                if url.endswith("InRelease"):
                    return b"signed"
                if url.endswith("Packages.gz"):
                    return gzip.compress(b"")
                raise HTTPError(url, 404, "No state marker", {}, None)
            with patch("scripts.restore_apt.fetch", side_effect=fetch), patch("scripts.restore_apt.verify_index"):
                self.assertEqual(restore("https://example.org/repo/", Path(tmp), public_key=Path("key.asc")), "")
                self.assertEqual(list(Path(tmp).rglob("*.deb")), [])

    def test_download_failure_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("scripts.restore_apt.fetch", side_effect=OSError("network failed")):
                with self.assertRaises(OSError):
                    restore("https://example.org/repo/", Path(tmp), public_key=Path("key.asc"))

    def test_missing_index_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("scripts.restore_apt.fetch", side_effect=HTTPError("url", 404, "Not Found", {}, None)):
                self.assertEqual(restore("https://example.org/repo/", Path(tmp), public_key=Path("key.asc")), "")

    def test_missing_binary_requests_source_rebuild(self):
        record = (
            "Package: gnome-calendar-data\nSource: gnome-calendar\n"
            "Filename: pool/missing.deb\nSize: 3\nSHA256: " + "0" * 64 + "\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp, "missing-sources")
            def fetch(url):
                if url.endswith("InRelease"):
                    return b"signed"
                if url.endswith("Packages.gz"):
                    return gzip.compress(record.encode())
                raise HTTPError(url, 404, "Not Found", {}, None)
            with patch("scripts.restore_apt.fetch", side_effect=fetch), patch("scripts.restore_apt.verify_index"):
                self.assertEqual(restore("https://example.org/repo/", Path(tmp), output, Path("key.asc")), "")
            self.assertEqual(output.read_text(), "gnome-calendar\n")

    def test_missing_binary_does_not_hide_other_http_errors(self):
        record = "Package: sample\nFilename: pool/sample.deb\nSize: 3\nSHA256: " + "0" * 64 + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            with patch("scripts.restore_apt.verify_index"), patch("scripts.restore_apt.fetch", side_effect=[
                gzip.compress(record.encode()), b"signed",
                HTTPError("url", 503, "Unavailable", {}, None),
            ]):
                with self.assertRaises(HTTPError):
                    restore("https://example.org/repo/", Path(tmp), public_key=Path("key.asc"))

    def test_existing_archive_requires_public_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("scripts.restore_apt.fetch", return_value=gzip.compress(b"")):
                with self.assertRaisesRegex(ValueError, "Public signing key required"):
                    restore("https://example.org/repo/", Path(tmp))

    def test_missing_signature_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("scripts.restore_apt.fetch", side_effect=[
                gzip.compress(b""), HTTPError("url", 404, "Not Found", {}, None),
            ]):
                with self.assertRaises(HTTPError):
                    restore("https://example.org/repo/", Path(tmp), public_key=Path("key.asc"))

    def test_invalid_signature_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("scripts.restore_apt.fetch", side_effect=[gzip.compress(b""), b"invalid"]), patch(
                "scripts.restore_apt.verify_index", side_effect=ValueError("Invalid signature")
            ):
                with self.assertRaisesRegex(ValueError, "Invalid signature"):
                    restore("https://example.org/repo/", Path(tmp), public_key=Path("key.asc"))

    def test_signed_index_checksum_validation(self):
        index = gzip.compress(b"package list")
        digest = hashlib.sha256(index).hexdigest()
        release = f"SHA256:\n {digest} {len(index)} Packages.gz\n".encode()

        def verified_release(command, **kwargs):
            output = Path(command[command.index("--output") + 1])
            output.write_bytes(release)

        with patch("scripts.restore_apt.subprocess.run", side_effect=verified_release) as run:
            verify_index(index, b"opaque signed data", Path("key.asc"))
            self.assertIn("--output", run.call_args.args[0])
            with self.assertRaisesRegex(ValueError, "does not match"):
                verify_index(b"tampered", b"opaque signed data", Path("key.asc"))

    def test_signed_release_uses_verified_output_not_armored_input(self):
        index = gzip.compress(b"package list")
        digest = hashlib.sha256(index).hexdigest()
        release = f"SHA256:\n {digest} {len(index)} Packages.gz\n".encode()

        def verified_release(command, **kwargs):
            Path(command[command.index("--output") + 1]).write_bytes(release)

        with patch("scripts.restore_apt.subprocess.run", side_effect=verified_release):
            verify_index(index, b"not a parseable clearsigned message", Path("key.asc"))

    def test_transient_http_error_retries(self):
        with patch("scripts.restore_apt.urllib.request.urlopen", side_effect=[
            HTTPError("url", 503, "Unavailable", {}, None),
            unittest.mock.MagicMock(__enter__=unittest.mock.Mock(return_value=unittest.mock.Mock(status=200, read=lambda: b"ok"))),
        ]) as urlopen, patch("scripts.restore_apt.time.sleep") as sleep:
            from scripts.restore_apt import fetch
            self.assertEqual(fetch("https://example.org/repo/Packages.gz"), b"ok")
            self.assertEqual(urlopen.call_count, 2)
            sleep.assert_called_once_with(1)

    def test_non_retryable_http_error_is_immediate(self):
        with patch("scripts.restore_apt.urllib.request.urlopen", side_effect=HTTPError("url", 404, "Not Found", {}, None)) as urlopen, patch("scripts.restore_apt.time.sleep") as sleep:
            from scripts.restore_apt import fetch
            with self.assertRaises(HTTPError):
                fetch("https://example.org/repo/Packages.gz")
            urlopen.assert_called_once()
            sleep.assert_not_called()

    def test_transient_http_error_exhausts_retries(self):
        with patch("scripts.restore_apt.urllib.request.urlopen", side_effect=HTTPError("url", 503, "Unavailable", {}, None)) as urlopen, patch("scripts.restore_apt.time.sleep") as sleep:
            from scripts.restore_apt import fetch
            with self.assertRaises(HTTPError):
                fetch("https://example.org/repo/Packages.gz")
            self.assertEqual(urlopen.call_count, 3)
            self.assertEqual(sleep.call_args_list, [unittest.mock.call(1), unittest.mock.call(2)])

    def test_checksum_mismatch_is_fatal(self):
        record = "Package: sample\nFilename: pool/sample.deb\nSize: 3\nSHA256: " + "0" * 64 + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            with patch("scripts.restore_apt.verify_index"), patch("scripts.restore_apt.fetch", side_effect=[gzip.compress(record.encode()), b"signed", b"abc"]):
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
            with patch("scripts.restore_apt.verify_index"), patch("scripts.restore_apt.fetch", side_effect=[gzip.compress(record.encode()), b"signed", payload, sha.encode()]) as fetch_mock:
                self.assertEqual(restore("https://example.org/repo/", Path(tmp), public_key=Path("key.asc")), sha)
                self.assertEqual(fetch_mock.call_args_list[-1], unittest.mock.call("https://example.org/repo/published-commit"))
                self.assertEqual((Path(tmp) / "pool/sample.deb").read_bytes(), payload)

    def test_rejects_traversal(self):
        record = "Filename: pool/../../oops.deb\nSize: 1\nSHA256: " + "0" * 64 + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            with patch("scripts.restore_apt.verify_index"), patch("scripts.restore_apt.fetch", side_effect=[gzip.compress(record.encode()), b"signed"]):
                with self.assertRaises(ValueError):
                    restore("https://example.org/repo/", Path(tmp))


if __name__ == "__main__":
    unittest.main()
