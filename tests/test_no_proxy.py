import tempfile
import unittest
import sqlite3
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet

from maildeck.mail_client import MailService
from maildeck.store import AccountStore


class NoProxyBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.store = AccountStore(Path(self.tempdir.name) / "db.sqlite", Fernet.generate_key())
        self.store.initialize()

    def tearDown(self):
        self.tempdir.cleanup()

    @staticmethod
    def outlook_address():
        return f"a{chr(64)}outlook.com"

    def test_outlook_account_can_be_added_without_proxy_pool(self):
        self.store.upsert_accounts([{
            "provider": "outlook", "email": self.outlook_address(), "password": "p",
            "refresh_token": "r", "client_id": "c",
        }])
        account = self.store.get_account_with_secrets(self.store.list_accounts()[0]["id"])
        self.assertNotIn("proxy", account)
        self.assertNotIn("proxyAssigned", self.store.list_accounts()[0])

    def test_initialize_removes_legacy_proxy_tables(self):
        with sqlite3.connect(self.store.db_path) as connection:
            connection.execute("CREATE TABLE proxy_endpoints (id TEXT)")
            connection.execute("CREATE TABLE proxy_assignments (account_id TEXT)")
        self.store.initialize()
        with sqlite3.connect(self.store.db_path) as connection:
            names = {row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
        self.assertNotIn("proxy_endpoints", names)
        self.assertNotIn("proxy_assignments", names)

    def test_outlook_uses_direct_imap_connection(self):
        self.store.upsert_accounts([{
            "provider": "outlook", "email": self.outlook_address(), "password": "p",
            "refresh_token": "r", "client_id": "c",
        }])
        account = self.store.get_account_with_secrets(self.store.list_accounts()[0]["id"])
        service = MailService(self.store)
        with patch("maildeck.mail_client.imaplib.IMAP4_SSL") as direct, \
             patch.object(service, "_outlook_access_token", return_value="token"):
            direct.return_value.authenticate.return_value = ("OK", [])
            service._connect(account)
            direct.assert_called_once_with(
                host="outlook.office365.com", port=993,
                ssl_context=unittest.mock.ANY, timeout=service.timeout,
            )


if __name__ == "__main__":
    unittest.main()
