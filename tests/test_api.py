import json
import tempfile
import unittest
from pathlib import Path

from cryptography.fernet import Fernet

from maildeck.api import MaildeckAPI
from maildeck.store import AccountStore


class FakeMailService:
    def list_messages(self, account_id, page=1, page_size=30, folder="INBOX"):
        return {"messages": [{"uid": "7", "subject": "Real inbox"}], "page": page,
                "pageSize": page_size, "hasMore": False, "total": 1, "folder": folder}

    def get_message(self, account_id, uid, folder="INBOX"):
        return {"uid": uid, "subject": "Real inbox", "body": "Hello", "attachments": []}

    def check_account(self, account_id):
        return {"ok": True, "message": "Подключение работает"}


class APITests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        store = AccountStore(Path(self.tempdir.name) / "db.sqlite", Fernet.generate_key())
        store.initialize()
        self.api = MaildeckAPI(store, FakeMailService())

    def tearDown(self):
        self.tempdir.cleanup()

    def call(self, method, path, body=None):
        payload = json.dumps(body).encode() if body is not None else b""
        return self.api.handle(method, path, {}, payload)

    @staticmethod
    def mailbox(local, domain):
        return f"{local}{chr(64)}{domain}"

    def test_bulk_import_returns_clear_format_error(self):
        address = self.mailbox("alpha", "outlook.com")
        status, _, body = self.call("POST", "/api/import", {
            "provider": "outlook",
            "content": f"{address}:password",
        })
        data = json.loads(body)
        self.assertEqual(status, 422)
        self.assertEqual(data["error"]["code"], "INVALID_IMPORT_FORMAT")
        self.assertIn("Строка 1", data["error"]["message"])

    def test_create_list_and_mailbox_flow(self):
        address = self.mailbox("alpha", "firsthidden.com")
        status, _, body = self.call("POST", "/api/accounts", {
            "provider": "firstmail",
            "email": address,
            "password": "Secret!1234",
        })
        self.assertEqual(status, 201)
        account_id = json.loads(body)["account"]["id"]

        status, _, body = self.call("GET", "/api/accounts", None)
        listed = json.loads(body)["accounts"]
        self.assertEqual(listed[0]["email"], address)
        self.assertNotIn("password", listed[0])

        status, _, body = self.call("GET", f"/api/accounts/{account_id}/messages", None)
        self.assertEqual(json.loads(body)["messages"][0]["subject"], "Real inbox")

        status, _, body = self.call("GET", f"/api/accounts/{account_id}/messages/7", None)
        self.assertEqual(json.loads(body)["body"], "Hello")

    def test_rejects_large_import(self):
        status, _, body = self.call("POST", "/api/import", {
            "provider": "firstmail",
            "content": "x" * (1024 * 1024 + 1),
        })
        self.assertEqual(status, 413)
        self.assertEqual(json.loads(body)["error"]["code"], "FILE_TOO_LARGE")


if __name__ == "__main__":
    unittest.main()
