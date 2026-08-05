from __future__ import annotations

import argparse
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .api import MaildeckAPI
from .mail_client import MailService
from .store import AccountStore


MAX_REQUEST_BYTES = 1_200_000
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; font-src 'self'; "
        "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    ),
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


class MaildeckHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, handler, api: MaildeckAPI):
        super().__init__(address, handler)
        self.api = api


class RequestHandler(BaseHTTPRequestHandler):
    server_version = "Maildeck"
    sys_version = ""

    def log_message(self, format: str, *args) -> None:
        # Keep app logs bounded via journald and never log query strings/body/secrets.
        safe_path = urlsplit(self.path).path
        print(f"{self.address_string()} {self.command} {safe_path} {args[1] if len(args) > 1 else '-'}")

    def _headers(self, status: int, headers: dict[str, str], length: int) -> None:
        self.send_response(status)
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        for name, value in headers.items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(length))
        self.end_headers()

    def _api(self) -> None:
        content_length = self.headers.get("Content-Length", "0")
        try:
            length = int(content_length)
        except ValueError:
            length = MAX_REQUEST_BYTES + 1
        server = self.server
        if not isinstance(server, MaildeckHTTPServer):
            raise RuntimeError("unexpected HTTP server")
        if length < 0 or length > MAX_REQUEST_BYTES:
            status, headers, body = server.api.handle(
                self.command, self.path, dict(self.headers), b"x" * (MAX_REQUEST_BYTES + 1)
            )
        else:
            body_in = self.rfile.read(length) if length else b""
            status, headers, body = server.api.handle(
                self.command, self.path, dict(self.headers), body_in
            )
        self._headers(status, headers, len(body))
        if self.command != "HEAD":
            self.wfile.write(body)

    def _static(self) -> None:
        path = unquote(urlsplit(self.path).path)
        if path == "/":
            relative = Path("index.html")
        else:
            relative = Path(path.lstrip("/"))
        if any(part in {"..", ""} for part in relative.parts) or relative.suffix not in {".html", ".css", ".js", ".svg", ".ico"}:
            self.send_error(404)
            return
        candidate = (STATIC_DIR / relative).resolve()
        if STATIC_DIR.resolve() not in candidate.parents or not candidate.is_file():
            self.send_error(404)
            return
        data = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        if candidate.suffix == ".js":
            content_type = "text/javascript; charset=utf-8"
        elif candidate.suffix in {".html", ".css"}:
            content_type += "; charset=utf-8"
        headers = {"Content-Type": content_type}
        if candidate.name != "index.html":
            headers["Cache-Control"] = "public, max-age=3600"
        self._headers(200, headers, len(data))
        if self.command != "HEAD":
            self.wfile.write(data)

    def do_GET(self) -> None:
        self._api() if urlsplit(self.path).path.startswith("/api/") else self._static()

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_POST(self) -> None:
        self._api() if urlsplit(self.path).path.startswith("/api/") else self.send_error(405)

    def do_DELETE(self) -> None:
        self._api() if urlsplit(self.path).path.startswith("/api/") else self.send_error(405)


def build_api(db_path: Path, key_path: Path) -> MaildeckAPI:
    mode = key_path.stat().st_mode & 0o777
    if mode & 0o037:
        raise PermissionError(
            f"encryption key permissions are too broad ({mode:04o}); use 0640 or stricter"
        )
    key = key_path.read_bytes().strip()
    store = AccountStore(db_path, key)
    store.initialize()
    return MaildeckAPI(store, MailService(store))


def main() -> None:
    parser = argparse.ArgumentParser(description="Maildeck read-only mail panel")
    parser.add_argument("--host", default=os.environ.get("MAILDECK_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MAILDECK_PORT", "18793")))
    parser.add_argument("--db", type=Path, default=Path(os.environ.get("MAILDECK_DB", "/var/lib/maildeck/maildeck.sqlite")))
    parser.add_argument("--key", type=Path, default=Path(os.environ.get("MAILDECK_KEY", "/etc/maildeck/encryption.key")))
    args = parser.parse_args()
    server = MaildeckHTTPServer((args.host, args.port), RequestHandler, build_api(args.db, args.key))
    print(f"maildeck listening on {args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
