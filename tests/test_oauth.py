import io
import json
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs

from cryptography.fernet import Fernet

from maildeck.mail_client import MailboxError, MailService
from maildeck.store import AccountNotFound, AccountStore


class OutlookTokenTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.key = Fernet.generate_key()
        self.store = AccountStore(Path(self.tempdir.name) / "db.sqlite", self.key)
        self.store.initialize()
        self.credentials = {
            "provider": "outlook", "email": "oauth-test@example.invalid",
            "password": "fixture-password", "client_id": "fixture-client",
            "refresh_token": "fixture-refresh-original",
        }
        folder = self.store.create_folder("outlook", "Fixture folder")
        self.store.upsert_accounts([self.credentials], folder_id=folder["id"])
        self.account_id = self.store.list_accounts()[0]["id"]
        self.store.update_account_organization(self.account_id, pinned=True)
        self.account = self.store.get_account_with_secrets(self.account_id)
        self.service = MailService(self.store)

    @staticmethod
    def response(**overrides):
        return io.BytesIO(json.dumps({
            "access_token": "fixture-access", "expires_in": 3600,
            "refresh_token": "fixture-refresh-rotated", **overrides,
        }).encode())

    def test_rotation_survives_new_service_and_preserves_encrypted_credentials_and_organization(self):
        before = self.store.get_public_account(self.account_id)
        with patch("maildeck.mail_client.urllib.request.urlopen", return_value=self.response()):
            self.assertEqual(self.service._outlook_access_token(self.account), "fixture-access")
        fresh_store = AccountStore(self.store.db_path, self.key)
        saved = fresh_store.get_account_with_secrets(self.account_id)
        self.assertEqual(saved["refresh_token"], "fixture-refresh-rotated")
        for field in ("password", "client_id"):
            self.assertEqual(saved[field], self.credentials[field])
        self.assertEqual(
            {key: value for key, value in fresh_store.get_public_account(self.account_id).items()
             if key != "updatedAt"},
            {key: value for key, value in before.items() if key != "updatedAt"},
        )
        with closing(sqlite3.connect(self.store.db_path)) as connection:
            encrypted = connection.execute("SELECT secrets_encrypted FROM accounts").fetchone()[0]
        self.assertEqual(json.loads(Fernet(self.key).decrypt(encrypted))["refresh_token"],
                         "fixture-refresh-rotated")
        for path in self.store.db_path.parent.glob("db.sqlite*"):
            raw = path.read_bytes()
            for secret in ("fixture-password", "fixture-client", "fixture-refresh-rotated"):
                self.assertNotIn(secret.encode(), raw)
        self.assertNotIn("refresh_token", json.dumps(fresh_store.list_accounts()))
        with patch("maildeck.mail_client.urllib.request.urlopen", return_value=self.response()) as request:
            MailService(fresh_store)._outlook_access_token(self.account)
        self.assertEqual(parse_qs(request.call_args.args[0].data.decode())["refresh_token"],
                         ["fixture-refresh-rotated"])

    def test_missing_blank_or_invalid_rotation_keeps_existing_token(self):
        for value in ("missing", None, "", " \t", 123):
            with self.subTest(value=value):
                data = {"access_token": "fixture-access", "expires_in": 3600}
                if value != "missing":
                    data["refresh_token"] = value
                with patch("maildeck.mail_client.urllib.request.urlopen",
                           return_value=io.BytesIO(json.dumps(data).encode())):
                    self.assertEqual(MailService(self.store)._outlook_access_token(self.account),
                                     "fixture-access")
                self.assertEqual(self.store.get_account_with_secrets(self.account_id)["refresh_token"],
                                 self.credentials["refresh_token"])

    def test_stale_dictionary_uses_latest_token_after_cache_expiry(self):
        with patch("maildeck.mail_client.urllib.request.urlopen", return_value=self.response()):
            self.service._outlook_access_token(self.account)
        self.service._oauth_cache.clear()
        with patch("maildeck.mail_client.urllib.request.urlopen",
                   return_value=self.response(refresh_token="fixture-refresh-newest")) as request:
            self.service._outlook_access_token(self.account)
        self.assertEqual(parse_qs(request.call_args.args[0].data.decode())["refresh_token"],
                         ["fixture-refresh-rotated"])
        self.assertEqual(self.store.get_account_with_secrets(self.account_id)["refresh_token"],
                         "fixture-refresh-newest")

    def test_same_service_serializes_refresh_and_rechecks_cache(self):
        entered = threading.Event()
        release = threading.Event()
        second_started = threading.Event()

        def exchange(*args, **kwargs):
            # The network exchange must remain inside the serialization boundary.
            self.assertTrue(self.service._oauth_lock.locked())
            entered.set()
            self.assertTrue(release.wait(5))
            return self.response()

        def second_refresh():
            second_started.set()
            return self.service._outlook_access_token(dict(self.account))

        with patch("maildeck.mail_client.urllib.request.urlopen", side_effect=exchange) as request:
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(self.service._outlook_access_token, self.account)
                try:
                    self.assertTrue(entered.wait(5))
                    second = pool.submit(second_refresh)
                    self.assertTrue(second_started.wait(5))
                finally:
                    release.set()
                self.assertEqual(first.result(5), "fixture-access")
                self.assertEqual(second.result(5), "fixture-access")
        self.assertEqual(request.call_count, 1)
        self.assertEqual(self.store.get_account_with_secrets(self.account_id)["refresh_token"],
                         "fixture-refresh-rotated")

    def test_inflight_response_cannot_overwrite_reimported_credentials(self):
        for field in ("password", "client_id", "refresh_token"):
            with self.subTest(field=field):
                self.store.upsert_accounts([self.credentials])
                replacement = {**self.credentials, field: "fixture-reimported"}

                def exchange(*args, **kwargs):
                    self.store.upsert_accounts([replacement])
                    return self.response()

                with patch("maildeck.mail_client.urllib.request.urlopen", side_effect=exchange):
                    with self.assertRaises(MailboxError):
                        self.service._outlook_access_token(self.account)
                saved = self.store.get_account_with_secrets(self.account_id)
                for secret in ("password", "client_id", "refresh_token"):
                    self.assertEqual(saved[secret], replacement[secret])
                self.assertNotIn(self.account_id, self.service._oauth_cache)

    def test_late_response_cannot_revert_rotation_from_another_service(self):
        def exchange(*args, **kwargs):
            with patch("maildeck.mail_client.urllib.request.urlopen",
                       return_value=self.response(refresh_token="fixture-newer-rotation")):
                MailService(self.store)._outlook_access_token(self.account)
            return self.response(refresh_token="fixture-late-rotation")

        with patch("maildeck.mail_client.urllib.request.urlopen", side_effect=exchange):
            with self.assertRaises(MailboxError):
                self.service._outlook_access_token(self.account)
        self.assertEqual(self.store.get_account_with_secrets(self.account_id)["refresh_token"],
                         "fixture-newer-rotation")
        self.assertNotIn(self.account_id, self.service._oauth_cache)

    def test_persistence_failure_does_not_publish_cached_access_token(self):
        with patch("maildeck.mail_client.urllib.request.urlopen", return_value=self.response()), \
             patch.object(self.store, "rotate_outlook_refresh_token",
                          side_effect=sqlite3.OperationalError("fixture write failure")):
            with self.assertRaises(sqlite3.OperationalError):
                self.service._outlook_access_token(self.account)
        self.assertEqual(self.store.get_account_with_secrets(self.account_id)["refresh_token"],
                         self.credentials["refresh_token"])
        self.assertNotIn(self.account_id, self.service._oauth_cache)

    def test_inflight_response_cannot_recreate_deleted_account(self):
        def exchange(*args, **kwargs):
            self.store.delete_account(self.account_id)
            return self.response()

        with patch("maildeck.mail_client.urllib.request.urlopen", side_effect=exchange):
            with self.assertRaises(AccountNotFound):
                self.service._outlook_access_token(self.account)
        self.assertEqual(self.store.list_accounts(), [])
        self.assertNotIn(self.account_id, self.service._oauth_cache)

    def test_invalid_access_token_does_not_persist_rotation(self):
        with patch("maildeck.mail_client.urllib.request.urlopen",
                   return_value=self.response(access_token="")):
            with self.assertRaises(MailboxError):
                self.service._outlook_access_token(self.account)
        self.assertEqual(self.store.get_account_with_secrets(self.account_id)["refresh_token"],
                         self.credentials["refresh_token"])


if __name__ == "__main__":
    unittest.main()
