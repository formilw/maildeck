from __future__ import annotations

import argparse
from pathlib import Path

from .parsers import ImportFormatError, parse_accounts
from .store import AccountStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Import account files into Maildeck")
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--key", type=Path, required=True)
    parser.add_argument("--outlook", type=Path)
    parser.add_argument("--firstmail", type=Path)
    args = parser.parse_args()

    sources = [("outlook", args.outlook), ("firstmail", args.firstmail)]
    selected = [(provider, path) for provider, path in sources if path]
    if not selected:
        parser.error("provide --outlook and/or --firstmail")

    parsed: list[tuple[str, list[dict[str, str | None]]]] = []
    try:
        for provider, path in selected:
            content = path.read_text(encoding="utf-8-sig")
            parsed.append((provider, parse_accounts(content, provider)))
    except (OSError, UnicodeError, ImportFormatError) as exc:
        parser.error(str(exc))

    store = AccountStore(args.db, args.key.read_bytes().strip())
    store.initialize()
    for provider, accounts in parsed:
        outcome = store.upsert_accounts(accounts)
        print(
            f"{provider}: parsed={len(accounts)} "
            f"created={outcome['created']} updated={outcome['updated']}"
        )


if __name__ == "__main__":
    main()
