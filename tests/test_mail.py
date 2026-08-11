import unittest
from email.message import EmailMessage

from maildeck.mail_client import MailboxError, message_to_public, safe_folder_name


class MailParsingTests(unittest.TestCase):
    def test_normalizes_email_template_spacing_and_skips_hidden_preheader(self):
        message = EmailMessage()
        message.set_content(
            '''<div style="display: none; max-height: 0">Hidden preview&nbsp;\u200c&nbsp;\u200c</div>
            <table><tr><td>
                <p>Hey John,</p>
                <p>Welcome to DataImpulse.</p>
                <table><tr><td>
                    <a href="https://example.com/activate">Activate My Account</a>
                </td></tr></table>
                <p>Once confirmed, you can:</p>
                <ul>
                    <li>Start with <strong>just $5</strong> - pay only for what you use</li>
                    <li>Generate proxy credentials instantly</li>
                </ul>
            </td></tr></table>''',
            subtype="html",
        )

        result = message_to_public(message, "44")
        rendered = "".join(part["text"] for part in result["bodyParts"])

        self.assertNotIn("Hidden preview", rendered)
        self.assertNotIn("\u200c", rendered)
        self.assertNotRegex(rendered, r"\n{3,}")
        self.assertNotRegex(rendered, r"[ \t]{2,}")
        self.assertIn("Hey John,\n\nWelcome to DataImpulse.", rendered)
        self.assertIn("Start with just $5 - pay only for what you use", rendered)

    def test_preserves_safe_html_links_as_structured_body_parts(self):
        message = EmailMessage()
        message["Subject"] = "Activate account"
        message.set_content("Activate My Account")
        message.add_alternative(
            '<p>Welcome</p><a href="https://example.com/activate?token=secret">Activate My Account</a>'
            '<a href="javascript:alert(1)">Unsafe action</a>',
            subtype="html",
        )

        result = message_to_public(message, "43")

        self.assertIn("Activate My Account", result["body"])
        linked = [part for part in result["bodyParts"] if part.get("href")]
        self.assertEqual(linked, [{
            "text": "Activate My Account",
            "href": "https://example.com/activate?token=secret",
        }])
        unsafe = [part for part in result["bodyParts"] if "Unsafe action" in part.get("text", "")]
        self.assertEqual(len(unsafe), 1)
        self.assertEqual(unsafe[0]["text"].strip(), "Unsafe action")
        self.assertNotIn("href", unsafe[0])

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
        self.assertEqual(safe_folder_name("INBOX"), b'"INBOX"')
        with self.assertRaises(MailboxError):
            safe_folder_name("INBOX\r\nLOGOUT")


if __name__ == "__main__":
    unittest.main()
