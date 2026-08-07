from __future__ import annotations

import html
import imaplib
import json
import re
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

from email import policy
from email.header import decode_header
from email.message import Message
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from threading import Lock

from .store import AccountNotFound, AccountStore


MAX_MESSAGE_BODY = 300_000
MAX_MESSAGE_BYTES = 12 * 1024 * 1024


class MailboxError(RuntimeError):
    def __init__(self, message: str, kind: str = "unknown"):
        super().__init__(message)
        self.kind = kind


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[dict[str, str]] = []
        self.hidden_depth = 0
        self.tag_stack: list[tuple[str, bool]] = []
        self.link_stack: list[str | None] = []

    @staticmethod
    def _safe_href(value: str | None) -> str | None:
        if not value or len(value) > 8192 or re.search(r"[\x00-\x1f\x7f]", value):
            return None
        href = html.unescape(value).strip()
        parsed = urllib.parse.urlsplit(href)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            return None
        return href

    def _append(self, text: str, href: str | None = None) -> None:
        if not text:
            return
        part = {"text": text}
        if href:
            part["href"] = href
        if self.parts and self.parts[-1].get("href") == part.get("href"):
            self.parts[-1]["text"] += text
        else:
            self.parts.append(part)

    def handle_starttag(self, tag: str, attrs):
        attributes = dict(attrs)
        style = re.sub(r"\s+", "", (attributes.get("style") or "").lower())
        hidden = self.hidden_depth > 0 or tag in {"script", "style", "noscript", "template"}
        hidden = hidden or "display:none" in style or "visibility:hidden" in style
        if hidden:
            self.hidden_depth += 1
        self.tag_stack.append((tag, hidden))
        if not hidden:
            if tag in {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "blockquote"}:
                self._append("\n")
            if tag == "a":
                self.link_stack.append(self._safe_href(attributes.get("href")))

    def handle_endtag(self, tag: str):
        hidden = False
        for index in range(len(self.tag_stack) - 1, -1, -1):
            if self.tag_stack[index][0] == tag:
                closed = self.tag_stack[index:]
                del self.tag_stack[index:]
                hidden = any(item[1] for item in closed)
                self.hidden_depth = max(0, self.hidden_depth - sum(item[1] for item in closed))
                break
        if not hidden and not self.hidden_depth:
            if tag == "a" and self.link_stack:
                self.link_stack.pop()
            if tag in {"p", "div", "li", "tr", "blockquote"}:
                self._append("\n")

    def handle_data(self, data: str):
        if not self.hidden_depth:
            self._append(data, self.link_stack[-1] if self.link_stack else None)

    def text(self) -> str:
        value = html.unescape("".join(part["text"] for part in self.parts)).replace("\r", "")
        value = re.sub(r"[ \t]+", " ", value)
        value = re.sub(r"\n[ \t]+", "\n", value)
        value = re.sub(r"\n{3,}", "\n\n", value)
        return value.strip()

    def public_parts(self) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        remaining = MAX_MESSAGE_BODY
        pending_whitespace = ""

        def append(text: str, href: str | None = None) -> None:
            nonlocal remaining
            if not text or remaining <= 0:
                return
            text = text[:remaining]
            part = {"text": text}
            if href:
                part["href"] = href
            if result and result[-1].get("href") == part.get("href"):
                result[-1]["text"] += text
            else:
                result.append(part)
            remaining -= len(text)

        for source in self.parts:
            if remaining <= 0:
                break
            text = source["text"].replace("\r", "").replace("\xa0", " ")
            text = re.sub(r"[\u200b-\u200d\ufeff]", "", text)
            for chunk in re.split(r"(\s+)", text):
                if not chunk:
                    continue
                if chunk.isspace():
                    if "\n" in chunk:
                        pending_whitespace = "\n\n" if chunk.count("\n") >= 2 or "\n" in pending_whitespace else "\n"
                    elif not pending_whitespace:
                        pending_whitespace = " "
                    continue
                if result and pending_whitespace:
                    whitespace_href = source.get("href") if pending_whitespace == " " else None
                    append(pending_whitespace, whitespace_href)
                pending_whitespace = ""
                append(chunk, source.get("href"))
        return result


def _decode_header(value: str | None) -> str:
    if not value:
        return ""
    decoded: list[str] = []
    for part, charset in decode_header(value):
        if isinstance(part, bytes):
            try:
                decoded.append(part.decode(charset or "utf-8", errors="replace"))
            except LookupError:
                decoded.append(part.decode("utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded).strip()


def _decode_part(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        raw = part.get_payload()
        return raw if isinstance(raw, str) else ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def _message_body(message: Message) -> tuple[str, list[dict[str, str]]]:
    plain: list[str] = []
    rich: list[str] = []
    rich_parts: list[dict[str, str]] = []
    parts = message.walk() if message.is_multipart() else [message]
    for part in parts:
        disposition = part.get_content_disposition()
        if disposition == "attachment":
            continue
        content_type = part.get_content_type()
        if content_type == "text/plain":
            plain.append(_decode_part(part))
        elif content_type == "text/html":
            parser = _TextExtractor()
            parser.feed(_decode_part(part))
            parser.close()
            public_parts = parser.public_parts()
            if rich_parts:
                rich_parts.append({"text": "\n\n"})
            rich_parts.extend(public_parts)
            rich.append("".join(item["text"] for item in public_parts))
    body = "\n\n".join(value.strip() for value in (plain or rich) if value.strip())
    return body[:MAX_MESSAGE_BODY], rich_parts


def _attachments(message: Message) -> list[dict]:
    result: list[dict] = []
    for part in message.walk():
        filename = part.get_filename()
        if not filename:
            continue
        payload = part.get_payload(decode=True) or b""
        result.append({
            "name": _decode_header(filename)[:240],
            "contentType": part.get_content_type(),
            "size": len(payload),
        })
    return result


def _date_iso(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).isoformat()
    except (TypeError, ValueError, OverflowError):
        return None


def message_to_public(message: Message, uid: str, flags: str = "") -> dict:
    body, body_parts = _message_body(message)
    return {
        "uid": str(uid),
        "subject": _decode_header(message.get("Subject")) or "Без темы",
        "from": _decode_header(message.get("From")) or "Неизвестный отправитель",
        "to": _decode_header(message.get("To")),
        "date": _date_iso(message.get("Date")),
        "isUnread": "\\Seen" not in flags,
        "body": body,
        "bodyParts": body_parts,
        "attachments": _attachments(message),
    }


def safe_folder_name(folder: str) -> str:
    if folder != "INBOX":
        raise MailboxError("Доступна только папка «Входящие»", "unknown")
    return folder


def _extract_fetch_bytes(response) -> tuple[bytes, str]:
    raw = b""
    flags = ""
    for item in response or []:
        if isinstance(item, tuple):
            meta, payload = item
            flags += meta.decode("ascii", errors="ignore") if isinstance(meta, bytes) else str(meta)
            if isinstance(payload, bytes):
                raw += payload
    return raw, flags


class MailService:
    def __init__(self, store: AccountStore, timeout: int = 20):
        self.store = store
        self.timeout = timeout
        self._oauth_cache: dict[str, tuple[str, float]] = {}
        self._oauth_lock = Lock()

    def _outlook_access_token(self, account: dict) -> str:
        with self._oauth_lock:
            cached = self._oauth_cache.get(account["id"])
            if cached and cached[1] > time.time() + 60:
                return cached[0]
        try:
            body = urllib.parse.urlencode({
                "client_id": account["client_id"],
                "grant_type": "refresh_token",
                "refresh_token": account["refresh_token"],
                "scope": "https://outlook.office.com/IMAP.AccessAsUser.All offline_access",
            }).encode("ascii")
            request = urllib.request.Request(
                "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
                data=body,
                method="POST",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.load(response)
            token = data.get("access_token")
            if not isinstance(token, str) or not token:
                raise MailboxError("Outlook не вернул токен доступа", "oauth")
            expires = int(data.get("expires_in", 3600))
            with self._oauth_lock:
                self._oauth_cache[account["id"]] = (token, time.time() + expires)
            return token
        except urllib.error.HTTPError as exc:
            raise MailboxError("Не удалось обновить доступ Outlook", "oauth") from exc
        except (urllib.error.URLError, socket.timeout, OSError) as exc:
            raise MailboxError("Сервер авторизации Outlook временно недоступен", "network") from exc
        except (json.JSONDecodeError, ValueError) as exc:
            raise MailboxError("Не удалось обновить доступ Outlook", "oauth") from exc

    def _connect(self, account: dict) -> imaplib.IMAP4_SSL:
        host = "outlook.office365.com" if account["provider"] == "outlook" else "imap.firstmail.ltd"
        try:
            if account["provider"] == "outlook":
                connection = imaplib.IMAP4_SSL(
                    host=host,
                    port=993,
                    ssl_context=ssl.create_default_context(),
                    timeout=self.timeout,
                )
                token = self._outlook_access_token(account)
                auth = f"user={account['email']}\x01auth=Bearer {token}\x01\x01"
                connection.authenticate("XOAUTH2", lambda _: auth.encode("utf-8"))
            else:
                connection = imaplib.IMAP4_SSL(
                    host=host,
                    port=993,
                    ssl_context=ssl.create_default_context(),
                    timeout=self.timeout,
                )
                connection.login(account["email"], account["password"])
            return connection
        except MailboxError:
            raise
        except imaplib.IMAP4.error as exc:
            raise MailboxError("Не удалось войти в почту", "auth") from exc
        except (OSError, socket.timeout, ssl.SSLError) as exc:
            raise MailboxError("Сервер почты временно недоступен", "network") from exc

    def _with_account(self, account_id: str, operation):
        return operation(self.store.get_account_with_secrets(account_id))

    @staticmethod
    def _close(connection: imaplib.IMAP4_SSL | None) -> None:
        if connection is None:
            return
        try:
            connection.logout()
        except Exception:
            pass

    def check_account(self, account_id: str) -> dict:
        def operation(account):
            connection = None
            try:
                connection = self._connect(account)
                status, _ = connection.select("INBOX", readonly=True)
                if status != "OK":
                    raise MailboxError("Не удалось открыть входящие", "unknown")
                return {"ok": True, "message": "Подключение работает"}
            finally:
                self._close(connection)
        try:
            result = self._with_account(account_id, operation)
            self.store.update_status(account_id, "connected")
            return result
        except MailboxError as exc:
            self.store.update_status(account_id, "error", exc.kind)
            raise

    def list_messages(self, account_id: str, page: int = 1, page_size: int = 30, folder: str = "INBOX") -> dict:
        folder = safe_folder_name(folder)
        if page < 1 or page_size < 1 or page_size > 50:
            raise MailboxError("Некорректная страница", "unknown")

        def operation(account):
            connection = None
            try:
                connection = self._connect(account)
                status, _ = connection.select(folder, readonly=True)
                if status != "OK":
                    raise MailboxError("Не удалось открыть входящие", "unknown")
                status, data = connection.uid("search", None, "ALL")
                if status != "OK":
                    raise MailboxError("Не удалось получить список писем", "unknown")
                uids = data[0].split() if data and data[0] else []
                uids.reverse()
                start = (page - 1) * page_size
                selected = uids[start:start + page_size]
                messages: list[dict] = []
                for uid_bytes in selected:
                    uid = uid_bytes.decode("ascii", errors="ignore")
                    status, response = connection.uid(
                        "fetch", uid,
                        "(BODY.PEEK[HEADER.FIELDS (FROM TO SUBJECT DATE MESSAGE-ID)] FLAGS)",
                    )
                    if status != "OK":
                        continue
                    raw, flags = _extract_fetch_bytes(response)
                    if not raw:
                        continue
                    message = BytesParser(policy=policy.default).parsebytes(raw)
                    public = message_to_public(message, uid, flags)
                    public.pop("body", None)
                    public.pop("bodyParts", None)
                    public.pop("attachments", None)
                    messages.append(public)
                return {
                    "messages": messages,
                    "page": page,
                    "pageSize": page_size,
                    "hasMore": start + len(selected) < len(uids),
                    "total": len(uids),
                    "folder": folder,
                }
            finally:
                self._close(connection)
        try:
            result = self._with_account(account_id, operation)
            self.store.update_status(account_id, "connected")
            return result
        except MailboxError as exc:
            self.store.update_status(account_id, "error", exc.kind)
            raise

    def get_message(self, account_id: str, uid: str, folder: str = "INBOX") -> dict:
        folder = safe_folder_name(folder)
        if not uid.isdigit():
            raise MailboxError("Некорректный идентификатор письма", "unknown")

        def operation(account):
            connection = None
            try:
                connection = self._connect(account)
                status, _ = connection.select(folder, readonly=True)
                if status != "OK":
                    raise MailboxError("Не удалось открыть входящие", "unknown")
                status, response = connection.uid("fetch", uid, "(BODY.PEEK[] FLAGS)")
                if status != "OK":
                    raise MailboxError("Письмо не найдено", "unknown")
                raw, flags = _extract_fetch_bytes(response)
                if not raw:
                    raise MailboxError("Письмо не найдено", "unknown")
                if len(raw) > MAX_MESSAGE_BYTES:
                    raise MailboxError("Письмо слишком большое для просмотра", "unknown")
                message = BytesParser(policy=policy.default).parsebytes(raw)
                return message_to_public(message, uid, flags)
            finally:
                self._close(connection)
        try:
            result = self._with_account(account_id, operation)
            self.store.update_status(account_id, "connected")
            return result
        except MailboxError as exc:
            self.store.update_status(account_id, "error", exc.kind)
            raise
