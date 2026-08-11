import unittest
from email.message import EmailMessage
from unittest.mock import patch

from maildeck.mail_client import (
    MailService,
    MailboxError,
    _mailbox_label,
    _mailbox_wire_name,
    list_mailboxes,
    safe_folder_name,
)


class FakeStore:
    def get_account_with_secrets(self, account_id):
        return {"id": account_id, "provider": "firstmail", "email": "user@example.invalid", "password": "secret"}

    def update_status(self, *args):
        pass


class FakeIMAP:
    def __init__(self):
        self.selected = None
        self.state = "AUTH"
        self.untagged_responses = {}
        self.searches = {
            "INBOX": [b"1"],
            "Sent": [b"9"],
            "Drafts": [b"4"],
            "Archive": [b"2"],
        }
        self.messages = {
            ("INBOX", "1"): self._message("Inbox", "Tue, 04 Aug 2026 12:00:00 +0000"),
            ("Sent", "9"): self._message("Sent", "Tue, 04 Aug 2026 14:00:00 +0000"),
            ("Drafts", "4"): self._message("Draft", "Tue, 04 Aug 2026 13:00:00 +0000"),
            ("Archive", "2"): self._message("Archived", "Tue, 04 Aug 2026 11:00:00 +0000"),
        }

    @staticmethod
    def _message(subject, date):
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = "Sender <sender@example.invalid>"
        message["To"] = "user@example.invalid"
        message["Date"] = date
        message.set_content(f"Body for {subject}")
        return message.as_bytes()

    def list(self):
        return "OK", [
            b'(\\HasNoChildren) "/" "INBOX"',
            b'(\\HasNoChildren \\Sent) "/" "Sent"',
            b'(\\HasNoChildren \\Drafts) "/" "Drafts"',
            b'(\\HasNoChildren \\Archive) "/" "Archive"',
            b'(\\Noselect \\HasChildren) "/" "Parent"',
            b'(\\HasNoChildren \\Trash) "/" "Trash"',
            b'(\\HasNoChildren \\Junk) "/" "Junk"',
        ]

    def select(self, mailbox, readonly=False):
        if isinstance(mailbox, bytes):
            mailbox = mailbox.decode("ascii")
        self.selected = mailbox.strip('"').replace('\\"', '"').replace('\\\\', '\\')
        return "OK", [str(len(self.searches.get(self.selected, []))).encode()]

    def uid(self, command, *args):
        if command == "search":
            return "OK", [b" ".join(self.searches.get(self.selected, []))]
        if command == "fetch":
            requested = args[0].split(",")
            response = []
            for uid in requested:
                raw = self.messages[(self.selected, uid)]
                response.append((f"1 (UID {uid} FLAGS (\\Seen))".encode(), raw))
            return "OK", response
        raise AssertionError(command)

    def logout(self):
        pass


class MailboxListingTests(unittest.TestCase):
    def test_lists_every_selectable_mailbox(self):
        folders = list_mailboxes(FakeIMAP())
        self.assertEqual(folders, ["INBOX", "Sent", "Drafts", "Archive", "Trash", "Junk"])

    def test_safe_folder_name_accepts_discovered_names_but_rejects_injection(self):
        self.assertEqual(safe_folder_name('Projects/2026'), b'"Projects/2026"')
        self.assertEqual(safe_folder_name('Quotes "ready"'), b'"Quotes \\"ready\\""')
        with self.assertRaises(MailboxError):
            safe_folder_name("INBOX\r\nLOGOUT")

    def test_detail_rejects_folder_injection_before_connecting(self):
        service = MailService(FakeStore())
        with patch.object(service, "_connect") as connect:
            with self.assertRaises(MailboxError):
                service.get_message("account-1", "1", folder="INBOX\r\nLOGOUT")
        connect.assert_not_called()

    def test_round_trips_non_ascii_mailbox_names_through_modified_utf7(self):
        self.assertEqual(_mailbox_wire_name("Черновики"), b"&BCcENQRABD0EPgQyBDgEOgQ4-")
        self.assertEqual(_mailbox_label("&BCcENQRABD0EPgQyBDgEOgQ4-"), "Черновики")

    def test_decodes_non_ascii_list_response_without_losing_selectable_wire_name(self):
        folders = list_mailboxes(type("UnicodeIMAP", (), {
            "list": lambda self: ("OK", [b'(\\HasNoChildren \\Drafts) "/" "&BCcENQRABD0EPgQyBDgEOgQ4-"'])
        })())
        self.assertEqual(len(folders), 1)
        self.assertEqual(_mailbox_label(folders[0]), "Черновики")

    def test_combines_messages_from_all_selectable_mailboxes_newest_first(self):
        service = MailService(FakeStore())
        connection = FakeIMAP()
        with patch.object(service, "_connect", return_value=connection):
            result = service.list_messages("account-1", page=1, page_size=3)

        self.assertEqual([item["subject"] for item in result["messages"]], ["Sent", "Draft", "Inbox"])
        self.assertEqual([item["folder"] for item in result["messages"]], ["Sent", "Drafts", "INBOX"])
        self.assertEqual(result["total"], 4)
        self.assertTrue(result["hasMore"])
        self.assertEqual(result["scope"], "all")

    def test_opens_message_from_its_source_mailbox(self):
        service = MailService(FakeStore())
        connection = FakeIMAP()
        with patch.object(service, "_connect", return_value=connection):
            result = service.get_message("account-1", "4", folder="Drafts")

        self.assertEqual(result["subject"], "Draft")
        self.assertEqual(result["folder"], "Drafts")
        self.assertEqual(connection.selected, "Drafts")


if __name__ == "__main__":
    unittest.main()
