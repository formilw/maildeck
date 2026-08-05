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


class StoreError(RuntimeError):
    pass


class AccountNotFound(StoreError):
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
                CREATE INDEX IF NOT EXISTS idx_accounts_provider_email
                    ON accounts(provider, email COLLATE NOCASE);
            """)
            connection.executescript("""
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
        }

    def upsert_accounts(self, accounts: list[dict]) -> dict[str, int]:
        created = 0
        updated = 0
        now = _now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            for account in accounts:
                existing = connection.execute(
                    "SELECT id FROM accounts WHERE provider = ? AND email = ? COLLATE NOCASE",
                    (account["provider"], account["email"]),
                ).fetchone()
                encrypted = self._encrypt(account)
                if existing:
                    connection.execute(
                        """UPDATE accounts
                           SET secrets_encrypted = ?, status = 'unknown', last_error = NULL,
                               last_checked_at = NULL, updated_at = ? WHERE id = ?""",
                        (encrypted, now, existing["id"]),
                    )
                    updated += 1
                else:
                    connection.execute(
                        """INSERT INTO accounts
                           (id, provider, email, secrets_encrypted, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (str(uuid.uuid4()), account["provider"], account["email"], encrypted, now, now),
                    )
                    created += 1
        return {"created": created, "updated": updated}

    def list_accounts(self, provider: str | None = None) -> list[dict]:
        query = "SELECT * FROM accounts"
        params: tuple = ()
        if provider:
            query += " WHERE provider = ?"
            params = (provider,)
        query += " ORDER BY provider, email COLLATE NOCASE"
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

    def delete_account(self, account_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        return cursor.rowcount > 0
