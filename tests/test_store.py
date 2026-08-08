import sqlite3
import tempfile
import unittest
from pathlib import Path

from cryptography.fernet import Fernet

from maildeck.store import AccountStore, StoreError


class AccountStoreTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "maildeck.sqlite"
        self.store = AccountStore(self.db_path, Fernet.generate_key())
        self.store.initialize()

    def tearDown(self):
        self.tempdir.cleanup()

    @staticmethod
    def mailbox(local, domain):
        return f"{local}{chr(64)}{domain}"

    def test_upsert_lists_public_fields_and_decrypts_only_for_mail_client(self):
        outcome = self.store.upsert_accounts([{
            "provider": "firstmail",
            "email": self.mailbox("alpha", "firsthidden.com"),
            "password": "Secret!1234",
            "refresh_token": None,
            "client_id": None,
        }])
        self.assertEqual(outcome, {"created": 1, "updated": 0})
        account = self.store.list_accounts("firstmail")[0]
        self.assertNotIn("password", account)
        self.assertNotIn("refresh_token", account)
        secrets = self.store.get_account_with_secrets(account["id"])
        self.assertEqual(secrets["password"], "Secret!1234")

    def test_credentials_are_not_plaintext_in_database(self):
        self.store.upsert_accounts([{
            "provider": "outlook",
            "email": self.mailbox("alpha", "outlook.com"),
            "password": "Password1",
            "refresh_token": "refresh-secret-token",
            "client_id": "client-id",
        }])
        raw = self.db_path.read_bytes()
        self.assertNotIn(b"Password1", raw)
        self.assertNotIn(b"refresh-secret-token", raw)

    def test_second_import_updates_existing_account(self):
        original = {
            "provider": "firstmail", "email": self.mailbox("alpha", "firsthidden.com"),
            "password": "Old!1234", "refresh_token": None, "client_id": None,
        }
        updated = {**original, "password": "New!5678"}
        self.store.upsert_accounts([original])
        outcome = self.store.upsert_accounts([updated])
        self.assertEqual(outcome, {"created": 0, "updated": 1})
        account_id = self.store.list_accounts("firstmail")[0]["id"]
        self.assertEqual(self.store.get_account_with_secrets(account_id)["password"], "New!5678")

    def test_status_update_does_not_expose_internal_error_details(self):
        self.store.upsert_accounts([{
            "provider": "firstmail", "email": self.mailbox("alpha", "firsthidden.com"),
            "password": "Secret!1234", "refresh_token": None, "client_id": None,
        }])
        account_id = self.store.list_accounts()[0]["id"]
        self.store.update_status(account_id, "error", "AUTHENTICATIONFAILED private details")
        account = self.store.list_accounts()[0]
        self.assertEqual(account["status"], "error")
        self.assertEqual(account["lastError"], "Не удалось войти в почту")

    def test_accounts_can_be_grouped_and_pinned(self):
        folder = self.store.create_folder("firstmail", "Рабочие")
        self.store.upsert_accounts([{
            "provider": "firstmail", "email": self.mailbox("alpha", "firsthidden.com"),
            "password": "Secret!1234", "refresh_token": None, "client_id": None,
        }], folder_id=folder["id"])
        account = self.store.list_accounts()[0]

        self.assertEqual(account["folderId"], folder["id"])
        self.assertFalse(account["pinned"])

        updated = self.store.update_account_organization(account["id"], pinned=True, folder_id=None)
        self.assertTrue(updated["pinned"])
        self.assertIsNone(updated["folderId"])

    def test_folder_provider_must_match_account_provider(self):
        folder = self.store.create_folder("outlook", "Outlook only")
        with self.assertRaises(StoreError):
            self.store.upsert_accounts([{
                "provider": "firstmail", "email": self.mailbox("alpha", "firsthidden.com"),
                "password": "Secret!1234", "refresh_token": None, "client_id": None,
            }], folder_id=folder["id"])

    def test_deleting_folder_keeps_accounts_unfiled(self):
        folder = self.store.create_folder("firstmail", "Temporary")
        self.store.upsert_accounts([{
            "provider": "firstmail", "email": self.mailbox("alpha", "firsthidden.com"),
            "password": "Secret!1234", "refresh_token": None, "client_id": None,
        }], folder_id=folder["id"])

        self.assertTrue(self.store.delete_folder(folder["id"]))
        self.assertIsNone(self.store.list_accounts()[0]["folderId"])

    def test_batch_delete_is_atomic_and_reports_deleted_count(self):
        for local in ("alpha", "beta", "gamma"):
            self.store.upsert_accounts([{
                "provider": "firstmail", "email": self.mailbox(local, "firsthidden.com"),
                "password": "Secret!1234", "refresh_token": None, "client_id": None,
            }])
        accounts = self.store.list_accounts()

        deleted = self.store.delete_accounts([accounts[0]["id"], accounts[2]["id"]])

        self.assertEqual(deleted, 2)
        self.assertEqual([item["email"] for item in self.store.list_accounts()], [accounts[1]["email"]])


if __name__ == "__main__":
    unittest.main()
