from __future__ import annotations

import json
import re
from urllib.parse import parse_qs, urlsplit

from .mail_client import MailboxError
from .parsers import ImportFormatError, MAX_IMPORT_BYTES, parse_accounts, parse_single_account
from .store import AccountNotFound, AccountStore, StoreError


ACCOUNT_ID_RE = r"[0-9a-fA-F-]{36}"


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

    def handle(self, method: str, raw_path: str, headers: dict, body: bytes):
        parsed = urlsplit(raw_path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)
        try:
            if method == "GET" and path == "/api/health":
                return _json(200, {"ok": True, "service": "maildeck"})

            if method == "GET" and path == "/api/accounts":
                provider = query.get("provider", [None])[0]
                if provider and provider not in {"outlook", "firstmail"}:
                    return _error(422, "VALIDATION_ERROR", "Неизвестная вкладка почты")
                return _json(200, {"accounts": self.store.list_accounts(provider)})

            if method == "POST" and path == "/api/accounts":
                account = parse_single_account(self._payload(body))
                outcome = self.store.upsert_accounts([account])
                listed = self.store.list_accounts(account["provider"])
                public = next(item for item in listed if item["email"] == account["email"])
                return _json(201, {"account": public, **outcome})

            if method == "POST" and path == "/api/import":
                payload = self._payload(body)
                content = payload.get("content", "")
                if not isinstance(content, str):
                    raise ImportFormatError("файл должен быть текстовым UTF-8")
                if len(content.encode("utf-8")) > MAX_IMPORT_BYTES:
                    return _error(413, "FILE_TOO_LARGE", "Файл больше 1 МБ")
                accounts = parse_accounts(content, payload.get("provider"))
                outcome = self.store.upsert_accounts(accounts)
                return _json(201, {"imported": len(accounts), **outcome})

            account_match = re.fullmatch(rf"/api/accounts/({ACCOUNT_ID_RE})", path)
            if method == "DELETE" and account_match:
                deleted = self.store.delete_account(account_match.group(1))
                if not deleted:
                    raise AccountNotFound(account_match.group(1))
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
                    folder=query.get("folder", ["INBOX"])[0],
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
        except MailboxError as exc:
            return _error(502, "MAILBOX_ERROR", str(exc))
        except StoreError:
            return _error(500, "STORE_ERROR", "Не удалось прочитать данные аккаунта")
