import unittest
from email.message import EmailMessage

from maildeck.mail_client import MailboxError, message_to_public, safe_folder_name


class MailParsingTests(unittest.TestCase):
    def test_converts_html_only_message_to_safe_plain_text(self):
        message = EmailMessage()
        message["Subject"] = "Добро пожаловать"
        message["From"] = f"Sender <sender{chr(64)}example.com>"
        message["To"] = f"alpha{chr(64)}example.com"
        message["Date"] = "Tue, 04 Aug 2026 12:00:00 +0000"
        message.set_content("<h1>Hello</h1><script>alert(1)</script><p>Safe text</p>", subtype="html")
        result = message_to_public(message, "42")
        self.assertIn("Hello", result["body"])
        self.assertIn("Safe text", result["body"])
        self.assertNotIn("<script", result["body"])
        self.assertNotIn("alert(1)", result["body"])

    def test_prefers_plain_text_and_lists_attachments_without_bytes(self):
        message = EmailMessage()
        message["Subject"] = "Invoice"
        message.set_content("Plain body")
        message.add_attachment(b"secret-content", maintype="application", subtype="pdf", filename="invoice.pdf")
        result = message_to_public(message, "9")
        self.assertEqual(result["body"], "Plain body")
        self.assertEqual(result["attachments"][0]["name"], "invoice.pdf")
        self.assertNotIn("secret-content", str(result))

    def test_rejects_folder_injection(self):
        self.assertEqual(safe_folder_name("INBOX"), "INBOX")
        with self.assertRaises(MailboxError):
            safe_folder_name("INBOX\r\nLOGOUT")


if __name__ == "__main__":
    unittest.main()
