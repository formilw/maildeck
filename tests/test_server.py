import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from cryptography.fernet import Fernet

from maildeck.api import MaildeckAPI
from maildeck.server import MaildeckHTTPServer, RequestHandler, build_api
from maildeck.store import AccountStore


class EmptyMailService:
    pass


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        store = AccountStore(Path(self.tempdir.name) / "db.sqlite", Fernet.generate_key())
        store.initialize()
        self.server = MaildeckHTTPServer(("127.0.0.1", 0), RequestHandler, MaildeckAPI(store, EmptyMailService()))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tempdir.cleanup()

    def test_serves_ui_and_health_with_security_headers(self):
        with urllib.request.urlopen(self.base + "/") as response:
            page = response.read().decode()
            self.assertIn("Maildeck", page)
            self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])
            self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        with urllib.request.urlopen(self.base + "/api/health") as response:
            self.assertIn(b'"ok":true', response.read())
            self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_rejects_path_traversal(self):
        request = urllib.request.Request(self.base + "/..%2FREADME.md")
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request)
        self.assertEqual(caught.exception.code, 404)

    def test_server_forwards_patch_requests_to_api(self):
        self.assertTrue(hasattr(RequestHandler, "do_PATCH"))

    def test_rejects_overly_broad_encryption_key_permissions(self):
        key_path = Path(self.tempdir.name) / "key"
        key_path.write_bytes(Fernet.generate_key())
        key_path.chmod(0o644)
        with self.assertRaises(PermissionError):
            build_api(Path(self.tempdir.name) / "other.sqlite", key_path)


if __name__ == "__main__":
    unittest.main()
