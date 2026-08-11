from __future__ import annotations

import json
import re
from urllib.parse import parse_qs, urlsplit

from .mail_client import MailboxError
from .parsers import ImportFormatError, MAX_IMPORT_BYTES, parse_accounts, parse_single_account
from .store import (
    AccountNotFound,
    AccountStore,
    FolderNameConflict,
    FolderNotFound,
    FolderProviderMismatch,
    StoreError,
)


ACCOUNT_ID_RE = r"[0-9a-fA-F-]{36}"
PROVIDERS = {"outlook", "firstmail"}
_UNSET = object()


def _json(status: int, payload: dict) -> tuple[int, dict[str, str], bytes]:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return status, {"Content-Type": "application/json; charset=utf-8"}, body


def _error(status: int, code: str, message: str, details: dict | None = None):
    payload = {"error": {"code": code, "message": message}}
    if details:
        payload["error"]["details"] = details
    return _json(status, payload)


class MaildeckAPI:
    def __init__(self, store: AccountStore, mail_service):
        self.store = store
        self.mail_service = mail_service

    def _payload(self, body: bytes) -> dict:
        if len(body) > MAX_IMPORT_BYTES + 128_000:
            raise OverflowError
        try:
            data = json.loads(body or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ImportFormatError("некорректный JSON") from exc
        if not isinstance(data, dict):
            raise ImportFormatError("ожидается JSON-объект")
        return data

    @staticmethod
    def _folder_id(payload: dict):
        folder_id = payload.get("folderId", None)
        if folder_id is not None and (
            not isinstance(folder_id, str) or not re.fullmatch(ACCOUNT_ID_RE, folder_id)
        ):
            raise StoreError("invalid folder id")
        return folder_id

    @staticmethod
    def _boolean(payload: dict, name: str) -> bool | None:
        if name not in payload:
            return None
        value = payload[name]
        if not isinstance(value, bool):
            raise StoreError(f"invalid {name}")
        return value

    def handle(self, method: str, raw_path: str, headers: dict, body: bytes):
        parsed = urlsplit(raw_path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)
        try:
            if method == "GET" and path == "/api/health":
                return _json(200, {"ok": True, "service": "maildeck"})

            if method == "GET" and path == "/api/accounts":
                provider = query.get("provider", [None])[0]
                if provider and provider not in PROVIDERS:
                    return _error(422, "VALIDATION_ERROR", "Неизвестная вкладка почты")
                return _json(200, {
                    "accounts": self.store.list_accounts(provider),
                    "folders": self.store.list_folders(provider),
                })

            if method == "POST" and path == "/api/accounts":
                payload = self._payload(body)
                account = parse_single_account(payload)
                folder_id = self._folder_id(payload)
                outcome = self.store.upsert_accounts([account], folder_id=folder_id)
                listed = self.store.list_accounts(account["provider"])
                public = next(
                    item for item in listed if item["email"].casefold() == account["email"].casefold()
                )
                return _json(201, {"account": public, **outcome})

            if method == "POST" and path == "/api/import":
                payload = self._payload(body)
                content = payload.get("content", "")
                if not isinstance(content, str):
                    raise ImportFormatError("файл должен быть текстовым UTF-8")
                if len(content.encode("utf-8")) > MAX_IMPORT_BYTES:
                    return _error(413, "FILE_TOO_LARGE", "Файл больше 1 МБ")
                accounts = parse_accounts(content, payload.get("provider"))
                folder_id = self._folder_id(payload)
                outcome = self.store.upsert_accounts(accounts, folder_id=folder_id)
                return _json(201, {"imported": len(accounts), **outcome})

            if method == "POST" and path == "/api/accounts/delete-batch":
                payload = self._payload(body)
                ids = payload.get("ids")
                if (
                    not isinstance(ids, list) or not ids or len(ids) > 5_000
                    or any(not isinstance(item, str) or not re.fullmatch(ACCOUNT_ID_RE, item) for item in ids)
                ):
                    return _error(422, "VALIDATION_ERROR", "Некорректный список аккаунтов")
                return _json(200, {"deleted": self.store.delete_accounts(ids)})

            if method == "POST" and path == "/api/folders":
                payload = self._payload(body)
                provider = payload.get("provider")
                name = payload.get("name")
                if provider not in PROVIDERS or not isinstance(name, str):
                    return _error(422, "VALIDATION_ERROR", "Некорректная папка")
                return _json(201, {"folder": self.store.create_folder(provider, name)})

            account_match = re.fullmatch(rf"/api/accounts/({ACCOUNT_ID_RE})", path)
            if method == "PATCH" and account_match:
                payload = self._payload(body)
                pinned = self._boolean(payload, "pinned")
                folder_id = self._folder_id(payload) if "folderId" in payload else _UNSET
                if pinned is None and folder_id is _UNSET:
                    return _error(422, "VALIDATION_ERROR", "Нет изменений")
                kwargs = {"pinned": pinned}
                if folder_id is not _UNSET:
                    kwargs["folder_id"] = folder_id
                account = self.store.update_account_organization(account_match.group(1), **kwargs)
                return _json(200, {"account": account})
            if method == "DELETE" and account_match:
                deleted = self.store.delete_account(account_match.group(1))
                if not deleted:
                    raise AccountNotFound(account_match.group(1))
                return _json(200, {"deleted": True})

            folder_match = re.fullmatch(rf"/api/folders/({ACCOUNT_ID_RE})", path)
            if method == "PATCH" and folder_match:
                payload = self._payload(body)
                pinned = self._boolean(payload, "pinned")
                name = payload.get("name") if "name" in payload else None
                if name is not None and not isinstance(name, str):
                    return _error(422, "VALIDATION_ERROR", "Некорректное имя папки")
                if name is None and pinned is None:
                    return _error(422, "VALIDATION_ERROR", "Нет изменений")
                folder = self.store.update_folder(folder_match.group(1), name=name, pinned=pinned)
                return _json(200, {"folder": folder})
            if method == "DELETE" and folder_match:
                if not self.store.delete_folder(folder_match.group(1)):
                    raise FolderNotFound(folder_match.group(1))
                return _json(200, {"deleted": True})

            check_match = re.fullmatch(rf"/api/accounts/({ACCOUNT_ID_RE})/check", path)
            if method == "POST" and check_match:
                return _json(200, self.mail_service.check_account(check_match.group(1)))

            messages_match = re.fullmatch(rf"/api/accounts/({ACCOUNT_ID_RE})/messages", path)
            if method == "GET" and messages_match:
                try:
                    page = int(query.get("page", ["1"])[0])
                    page_size = int(query.get("pageSize", ["30"])[0])
                except ValueError:
                    return _error(422, "VALIDATION_ERROR", "Некорректная страница")
                result = self.mail_service.list_messages(
                    messages_match.group(1), page=page, page_size=page_size,
                    folder=query.get("folder", ["all"])[0],
                )
                return _json(200, result)

            message_match = re.fullmatch(rf"/api/accounts/({ACCOUNT_ID_RE})/messages/(\d+)", path)
            if method == "GET" and message_match:
                result = self.mail_service.get_message(
                    message_match.group(1), message_match.group(2),
                    folder=query.get("folder", ["INBOX"])[0],
                )
                return _json(200, result)

            return _error(404, "NOT_FOUND", "Такого адреса нет")
        except OverflowError:
            return _error(413, "FILE_TOO_LARGE", "Запрос слишком большой")
        except ImportFormatError as exc:
            return _error(
                422, "INVALID_IMPORT_FORMAT", str(exc),
                {"line": exc.line} if exc.line else None,
            )
        except AccountNotFound:
            return _error(404, "ACCOUNT_NOT_FOUND", "Аккаунт не найден")
        except FolderNotFound:
            return _error(404, "FOLDER_NOT_FOUND", "Папка не найдена")
        except FolderProviderMismatch:
            return _error(422, "FOLDER_PROVIDER_MISMATCH", "Папка относится к другому типу почты")
        except FolderNameConflict:
            return _error(409, "FOLDER_NAME_CONFLICT", "Папка с таким именем уже есть")
        except MailboxError as exc:
            return _error(502, "MAILBOX_ERROR", str(exc))
        except StoreError:
            return _error(422, "VALIDATION_ERROR", "Некорректные данные")
