# Maildeck

Maildeck is a self-hosted, read-only mail panel for Outlook and Firstmail. Users add their own mailbox credentials in the browser or upload a UTF-8 text file, then read messages from every selectable IMAP folder in one bilingual Russian/English timeline.

![MIT license](https://img.shields.io/badge/license-MIT-blue.svg)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB.svg)

## Features

- separate Outlook and Firstmail tabs;
- single-account and bulk text-file import;
- folders for grouping accounts, with pinned folders and accounts;
- per-account and batch deletion through an in-app confirmation dialog;
- optional destination folder during single-account add or bulk import;
- read-only IMAP access using `BODY.PEEK`, so opening mail does not mark it as read;
- one newest-first timeline across Inbox, Drafts, Sent, Archive, Spam, Trash, and other selectable IMAP folders;
- safe plain-text rendering of HTML messages, with scripts and remote content discarded;
- encrypted password, refresh-token, and client-ID storage using Fernet;
- no credential fields in API responses;
- responsive message reader with independent scrolling and long-URL wrapping;
- complete Russian and English UI;
- no proxy support, analytics, third-party frontend assets, or telemetry.

## Security model

Maildeck is a single-installation application, not a multi-tenant hosted service. Anyone who can reach the panel can view all configured mailbox addresses and messages, add accounts, or remove accounts.

Run it on a trusted machine and put authentication in front of it before allowing network access. Bind the application to loopback and use an authenticated HTTPS reverse proxy, VPN, or identity-aware access proxy. Do not expose the raw HTTP listener to the internet.

Mailbox passwords and Outlook OAuth material are encrypted at rest. The encryption key must be stored separately from the SQLite database and protected with restrictive file permissions. Encryption at rest does not replace access control: a process that can read both files can decrypt the credentials.

Maildeck reads message bodies as plain text. It lists attachment metadata but does not download attachment contents through the UI.

## Supported account formats

Outlook uses OAuth refresh-token authentication for IMAP:

```text
email:password:refresh_token:client_id
```

The password field remains part of the import format for compatibility, but Outlook IMAP authentication uses the refresh token and client ID.

Firstmail uses username/password IMAP authentication:

```text
email:password
```

Blank lines are allowed. One upload is limited to 1 MB and 5,000 accounts. Use only mailbox credentials you own or are authorized to access.

## Quick start

Requirements:

- Python 3.11 or newer;
- OpenSSL-backed outbound HTTPS and IMAPS connectivity;
- a Fernet key generated locally.

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt

mkdir -p .local
python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())' > .local/encryption.key
chmod 600 .local/encryption.key

python3 -m maildeck.server \
  --host 127.0.0.1 \
  --port 18793 \
  --db .local/maildeck.sqlite \
  --key .local/encryption.key
```

Open `http://127.0.0.1:18793`. For access from another machine, configure authenticated HTTPS instead of changing the bind address directly.

The `.local/` directory, databases, keys, credentials, and account-list files are ignored by Git.

## Reverse proxy and systemd

`deploy/Caddyfile.example` is a minimal HTTPS reverse-proxy template. Add an authentication layer suitable for your environment before making the hostname reachable by other people.

`deploy/maildeck.service` is a hardened systemd template that expects:

- application code at `/opt/maildeck`;
- database at `/var/lib/maildeck/maildeck.sqlite`;
- encryption key at `/etc/maildeck/encryption.key`;
- a dedicated `maildeck` system user and group.

Example installation:

```bash
sudo useradd --system --home /var/lib/maildeck --shell /usr/sbin/nologin maildeck
sudo install -d -o root -g root -m 0755 /opt/maildeck
sudo install -d -o maildeck -g maildeck -m 0700 /var/lib/maildeck
sudo install -d -o root -g maildeck -m 0750 /etc/maildeck

python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())' \
  | sudo tee /etc/maildeck/encryption.key >/dev/null
sudo chown root:maildeck /etc/maildeck/encryption.key
sudo chmod 0640 /etc/maildeck/encryption.key
```

Copy the repository to `/opt/maildeck`, install `requirements.txt` in the runtime environment, review the service paths, then install and start the service. The template rate-limits journald output to prevent unbounded log storms.

## Development

```bash
python3 -m pip install -r requirements.txt
PYTHONPATH=. python3 -m unittest discover -s tests -v
node --check static/app.js
node --check static/i18n.js
```

Tests use synthetic mailbox addresses assembled at runtime. The repository contains no real mailbox addresses, credential files, database, or encryption key.

For private vulnerability reports, see [SECURITY.md](SECURITY.md).

## Privacy checklist before deployment

- keep the server bound to `127.0.0.1`;
- require authentication at the HTTPS reverse proxy or VPN boundary;
- keep the database and encryption key out of Git and backups with public access;
- restrict both files to the Maildeck service account;
- never paste production credentials into issues, screenshots, logs, or pull requests;
- rotate credentials immediately if they are ever published.

## License

MIT. See [LICENSE](LICENSE).
