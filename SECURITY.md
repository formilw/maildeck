# Security policy

## Reporting a vulnerability

Do not open a public issue with credentials, mailbox addresses, message content, database files, encryption keys, or exploit details that expose user data.

Use GitHub's private vulnerability reporting for this repository. Include affected versions, reproduction steps using synthetic data, and the expected impact. Remove all real mailbox data before attaching logs or screenshots.

## Deployment boundary

Maildeck is a single-installation self-hosted application. It does not provide user accounts, tenant isolation, or built-in authentication. Operators must keep it on loopback and place an authenticated HTTPS proxy, VPN, or identity-aware gateway in front of it.

The SQLite database and Fernet key are sensitive. Keep the key separate from the database, restrict both to the service account, and never commit either file. Maildeck refuses to start when the key is readable by users outside its owner/group boundary.

## Supported versions

Security fixes target the latest release on the default branch.
