from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


PUBLIC_STATUS_ERRORS = {
    "auth": "Не удалось войти в почту",
    "network": "Сервер почты временно недоступен",
    "oauth": "Не удалось обновить доступ Outlook",
    "unknown": "Не удалось открыть почту",
}
_UNSET = object()


class StoreError(RuntimeError):
    pass


class AccountNotFound(StoreError):
    pass


class FolderNotFound(StoreError):
    pass


class FolderProviderMismatch(StoreError):
    pass


class FolderNameConflict(StoreError):
    pass


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class AccountStore:
    def __init__(self, db_path: str | Path, encryption_key: bytes | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode("ascii")
        self.cipher = Fernet(encryption_key)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA busy_timeout = 15000")
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL CHECK (provider IN ('outlook', 'firstmail')),
                    email TEXT NOT NULL COLLATE NOCASE,
                    secrets_encrypted BLOB NOT NULL,
                    status TEXT NOT NULL DEFAULT 'unknown',
                    last_error TEXT,
                    last_checked_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(provider, email)
                );
                CREATE TABLE IF NOT EXISTS folders (
                    id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL CHECK (provider IN ('outlook', 'firstmail')),
                    name TEXT NOT NULL COLLATE NOCASE,
                    pinned INTEGER NOT NULL DEFAULT 0 CHECK (pinned IN (0, 1)),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(provider, name)
                );
            """)
            account_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(accounts)").fetchall()
            }
            if "folder_id" not in account_columns:
                connection.execute(
                    "ALTER TABLE accounts ADD COLUMN folder_id TEXT REFERENCES folders(id) ON DELETE SET NULL"
                )
            if "pinned" not in account_columns:
                connection.execute(
                    "ALTER TABLE accounts ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0 CHECK (pinned IN (0, 1))"
                )
            connection.executescript("""
                CREATE INDEX IF NOT EXISTS idx_accounts_provider_email
                    ON accounts(provider, email COLLATE NOCASE);
                CREATE INDEX IF NOT EXISTS idx_accounts_organization
                    ON accounts(provider, pinned DESC, folder_id, email COLLATE NOCASE);
                CREATE INDEX IF NOT EXISTS idx_folders_provider_order
                    ON folders(provider, pinned DESC, name COLLATE NOCASE);
                DROP TABLE IF EXISTS proxy_assignments;
                DROP TABLE IF EXISTS proxy_endpoints;
            """)

    def _encrypt(self, account: dict) -> bytes:
        payload = json.dumps({
            "password": account["password"],
            "refresh_token": account.get("refresh_token"),
            "client_id": account.get("client_id"),
        }, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return self.cipher.encrypt(payload)

    def _decrypt(self, encrypted: bytes) -> dict:
        try:
            return json.loads(self.cipher.decrypt(encrypted).decode("utf-8"))
        except (InvalidToken, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StoreError("credentials could not be decrypted") from exc

    @staticmethod
    def _public(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "provider": row["provider"],
            "email": row["email"],
            "status": row["status"],
            "lastError": row["last_error"],
            "lastCheckedAt": row["last_checked_at"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "folderId": row["folder_id"],
            "pinned": bool(row["pinned"]),
        }

    @staticmethod
    def _public_folder(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "provider": row["provider"],
            "name": row["name"],
            "pinned": bool(row["pinned"]),
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    @staticmethod
    def _normalized_folder_name(name: str) -> str:
        normalized = " ".join(name.strip().split()) if isinstance(name, str) else ""
        if not normalized or len(normalized) > 60:
            raise StoreError("invalid folder name")
        return normalized

    @staticmethod
    def _assert_provider(provider: str) -> None:
        if provider not in {"outlook", "firstmail"}:
            raise StoreError("invalid provider")

    @staticmethod
    def _assert_folder(
        connection: sqlite3.Connection, folder_id: str | None, provider: str
    ) -> None:
        if folder_id is None:
            return
        row = connection.execute(
            "SELECT provider FROM folders WHERE id = ?", (folder_id,)
        ).fetchone()
        if not row:
            raise FolderNotFound(folder_id)
        if row["provider"] != provider:
            raise FolderProviderMismatch(folder_id)

    def upsert_accounts(self, accounts: list[dict], folder_id: str | None = None) -> dict[str, int]:
        created = 0
        updated = 0
        now = _now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            providers = {account["provider"] for account in accounts}
            for provider in providers:
                self._assert_provider(provider)
                self._assert_folder(connection, folder_id, provider)
            for account in accounts:
                existing = connection.execute(
                    "SELECT id FROM accounts WHERE provider = ? AND email = ? COLLATE NOCASE",
                    (account["provider"], account["email"]),
                ).fetchone()
                encrypted = self._encrypt(account)
                if existing:
                    connection.execute(
                        """UPDATE accounts
                           SET secrets_encrypted = ?, folder_id = ?, status = 'unknown', last_error = NULL,
                               last_checked_at = NULL, updated_at = ? WHERE id = ?""",
                        (encrypted, folder_id, now, existing["id"]),
                    )
                    updated += 1
                else:
                    connection.execute(
                        """INSERT INTO accounts
                           (id, provider, email, secrets_encrypted, folder_id, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            str(uuid.uuid4()), account["provider"], account["email"], encrypted,
                            folder_id, now, now,
                        ),
                    )
                    created += 1
        return {"created": created, "updated": updated}

    def list_accounts(self, provider: str | None = None) -> list[dict]:
        query = "SELECT * FROM accounts"
        params: tuple = ()
        if provider:
            query += " WHERE provider = ?"
            params = (provider,)
        query += " ORDER BY provider, pinned DESC, email COLLATE NOCASE"
        with self._connect() as connection:
            return [self._public(row) for row in connection.execute(query, params).fetchall()]

    def get_public_account(self, account_id: str) -> dict:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        if not row:
            raise AccountNotFound(account_id)
        return self._public(row)

    def get_account_with_secrets(self, account_id: str) -> dict:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        if not row:
            raise AccountNotFound(account_id)
        result = self._public(row)
        result.update(self._decrypt(row["secrets_encrypted"]))
        return result

    def update_account_organization(
        self,
        account_id: str,
        *,
        pinned: bool | None = None,
        folder_id: str | None | object = _UNSET,
    ) -> dict:
        updates: list[str] = []
        params: list[object] = []
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT provider FROM accounts WHERE id = ?", (account_id,)
            ).fetchone()
            if not row:
                raise AccountNotFound(account_id)
            if pinned is not None:
                updates.append("pinned = ?")
                params.append(int(pinned))
            if folder_id is not _UNSET:
                self._assert_folder(connection, folder_id, row["provider"])
                updates.append("folder_id = ?")
                params.append(folder_id)
            if updates:
                updates.append("updated_at = ?")
                params.append(_now())
                params.append(account_id)
                connection.execute(
                    f"UPDATE accounts SET {', '.join(updates)} WHERE id = ?", params
                )
            updated = connection.execute(
                "SELECT * FROM accounts WHERE id = ?", (account_id,)
            ).fetchone()
        return self._public(updated)

    def list_folders(self, provider: str | None = None) -> list[dict]:
        query = "SELECT * FROM folders"
        params: tuple = ()
        if provider:
            query += " WHERE provider = ?"
            params = (provider,)
        query += " ORDER BY provider, pinned DESC, name COLLATE NOCASE"
        with self._connect() as connection:
            return [
                self._public_folder(row)
                for row in connection.execute(query, params).fetchall()
            ]

    def create_folder(self, provider: str, name: str) -> dict:
        self._assert_provider(provider)
        normalized = self._normalized_folder_name(name)
        now = _now()
        folder_id = str(uuid.uuid4())
        try:
            with self._connect() as connection:
                connection.execute(
                    """INSERT INTO folders (id, provider, name, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (folder_id, provider, normalized, now, now),
                )
        except sqlite3.IntegrityError as exc:
            raise FolderNameConflict(normalized) from exc
        return next(folder for folder in self.list_folders() if folder["id"] == folder_id)

    def update_folder(
        self, folder_id: str, *, name: str | None = None, pinned: bool | None = None
    ) -> dict:
        updates: list[str] = []
        params: list[object] = []
        if name is not None:
            updates.append("name = ?")
            params.append(self._normalized_folder_name(name))
        if pinned is not None:
            updates.append("pinned = ?")
            params.append(int(pinned))
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                exists = connection.execute(
                    "SELECT id FROM folders WHERE id = ?", (folder_id,)
                ).fetchone()
                if not exists:
                    raise FolderNotFound(folder_id)
                if updates:
                    updates.append("updated_at = ?")
                    params.append(_now())
                    params.append(folder_id)
                    connection.execute(
                        f"UPDATE folders SET {', '.join(updates)} WHERE id = ?", params
                    )
                row = connection.execute(
                    "SELECT * FROM folders WHERE id = ?", (folder_id,)
                ).fetchone()
        except sqlite3.IntegrityError as exc:
            raise FolderNameConflict(name or "") from exc
        return self._public_folder(row)

    def delete_folder(self, folder_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
        return cursor.rowcount > 0

    def update_status(self, account_id: str, status: str, error_kind: str | None = None) -> None:
        if status not in {"unknown", "connected", "error"}:
            status = "error"
        public_error = None
        if status == "error":
            kind = error_kind if error_kind in PUBLIC_STATUS_ERRORS else "auth"
            public_error = PUBLIC_STATUS_ERRORS[kind]
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE accounts SET status = ?, last_error = ?, last_checked_at = ?, updated_at = ?
                   WHERE id = ?""",
                (status, public_error, _now(), _now(), account_id),
            )
            if cursor.rowcount == 0:
                raise AccountNotFound(account_id)

    def delete_accounts(self, account_ids: list[str]) -> int:
        unique_ids = list(dict.fromkeys(account_ids))
        if not unique_ids:
            return 0
        if len(unique_ids) > 5_000:
            raise StoreError("too many accounts")
        placeholders = ",".join("?" for _ in unique_ids)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                f"DELETE FROM accounts WHERE id IN ({placeholders})", unique_ids
            )
        return cursor.rowcount

    def delete_account(self, account_id: str) -> bool:
        return self.delete_accounts([account_id]) > 0
