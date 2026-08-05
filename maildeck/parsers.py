from __future__ import annotations

import re
from dataclasses import dataclass


EMAIL_RE = re.compile(r"^[^\s@:\x00-\x1f]+@[^\s@:\x00-\x1f]+\.[^\s@:\x00-\x1f]+$")
FIRSTMAIL_DOMAINS = {
    "firsthidden.com",
    "ishowfirstmail.com",
    "analismail.com",
    "blackfirsta.com",
}
MAX_IMPORT_BYTES = 1024 * 1024
MAX_IMPORT_ACCOUNTS = 5000


@dataclass
class ImportFormatError(ValueError):
    message: str
    line: int | None = None

    def __str__(self) -> str:
        return f"Строка {self.line}: {self.message}" if self.line else self.message


def _validate_email(email: str, provider: str, line_number: int) -> str:
    normalized = email.strip().lower()
    if not EMAIL_RE.fullmatch(normalized):
        raise ImportFormatError("некорректный email", line_number)
    domain = normalized.rsplit("@", 1)[1]
    if provider == "outlook" and domain not in {"outlook.com", "hotmail.com", "live.com"}:
        raise ImportFormatError("для вкладки Outlook нужен адрес Outlook/Hotmail/Live", line_number)
    if provider == "firstmail" and domain not in FIRSTMAIL_DOMAINS:
        raise ImportFormatError("для вкладки Firstmail нужен адрес из Firstmail-файла", line_number)
    return normalized


def parse_accounts(content: str, provider: str) -> list[dict[str, str | None]]:
    if provider not in {"outlook", "firstmail"}:
        raise ImportFormatError("неизвестный тип почты")
    if not isinstance(content, str):
        raise ImportFormatError("файл должен быть текстовым UTF-8")
    if len(content.encode("utf-8")) > MAX_IMPORT_BYTES:
        raise ImportFormatError("файл больше 1 МБ")

    rows: list[dict[str, str | None]] = []
    seen: set[str] = set()
    for line_number, raw_line in enumerate(content.lstrip("\ufeff").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(":")
        expected = 4 if provider == "outlook" else 2
        if len(parts) != expected or any(not part.strip() for part in parts):
            hint = (
                "ожидается email:password:refresh_token:client_id"
                if provider == "outlook"
                else "ожидается email:password"
            )
            raise ImportFormatError(hint, line_number)

        email = _validate_email(parts[0], provider, line_number)
        if email in seen:
            raise ImportFormatError("этот email повторяется в файле", line_number)
        seen.add(email)

        if provider == "outlook":
            password, refresh_token, client_id = (part.strip() for part in parts[1:])
        else:
            password = parts[1].strip()
            refresh_token = None
            client_id = None
        rows.append({
            "provider": provider,
            "email": email,
            "password": password,
            "refresh_token": refresh_token,
            "client_id": client_id,
        })
        if len(rows) > MAX_IMPORT_ACCOUNTS:
            raise ImportFormatError(f"в одном файле можно загрузить до {MAX_IMPORT_ACCOUNTS} аккаунтов")

    if not rows:
        raise ImportFormatError("в файле нет аккаунтов")
    return rows


def parse_single_account(payload: dict) -> dict[str, str | None]:
    provider = payload.get("provider")
    if provider not in {"outlook", "firstmail"}:
        raise ImportFormatError("выбери Outlook или Firstmail")
    email = _validate_email(str(payload.get("email", "")), provider, 1)
    password = str(payload.get("password", "")).strip()
    if not password:
        raise ImportFormatError("укажи пароль")
    refresh_token = str(payload.get("refreshToken", "")).strip() or None
    client_id = str(payload.get("clientId", "")).strip() or None
    if provider == "outlook" and (not refresh_token or not client_id):
        raise ImportFormatError("для Outlook нужны refresh token и client ID")
    return {
        "provider": provider,
        "email": email,
        "password": password,
        "refresh_token": refresh_token,
        "client_id": client_id,
    }
