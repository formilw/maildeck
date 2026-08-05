import unittest

from maildeck.parsers import ImportFormatError, parse_accounts


class ParserTests(unittest.TestCase):
    @staticmethod
    def mailbox(local: str, domain: str) -> str:
        return f"{local}{chr(64)}{domain}"

    def test_parses_firstmail_file(self):
        first = self.mailbox("alpha", "firsthidden.com")
        second = self.mailbox("beta", "analismail.com")
        result = parse_accounts(
            f"{first}:Secret!1234\n"
            f"{second}:Other!5678\n",
            "firstmail",
        )
        self.assertEqual([item["email"] for item in result], [first, second])
        self.assertEqual(result[0]["password"], "Secret!1234")

    def test_parses_outlook_file(self):
        address = self.mailbox("alpha", "outlook.com")
        result = parse_accounts(
            f"{address}:Password1:refresh-token:client-id\n",
            "outlook",
        )
        self.assertEqual(result[0]["refresh_token"], "refresh-token")
        self.assertEqual(result[0]["client_id"], "client-id")

    def test_rejects_wrong_format_with_line_number_and_hint(self):
        address = self.mailbox("alpha", "outlook.com")
        with self.assertRaises(ImportFormatError) as caught:
            parse_accounts(f"{address}:only-password\n", "outlook")
        self.assertEqual(caught.exception.line, 1)
        self.assertIn("email:password:refresh_token:client_id", caught.exception.message)

    def test_rejects_mixed_provider_file(self):
        address = self.mailbox("alpha", "outlook.com")
        with self.assertRaises(ImportFormatError) as caught:
            parse_accounts(f"{address}:Secret!1234\n", "firstmail")
        self.assertIn("Firstmail", caught.exception.message)

    def test_rejects_duplicate_email_in_one_file(self):
        address = self.mailbox("alpha", "firsthidden.com")
        duplicate = self.mailbox("ALPHA", "firsthidden.com")
        with self.assertRaises(ImportFormatError) as caught:
            parse_accounts(
                f"{address}:Secret!1234\n"
                f"{duplicate}:Other!5678\n",
                "firstmail",
            )
        self.assertEqual(caught.exception.line, 2)
        self.assertIn("повторяется", caught.exception.message)

    def test_ignores_blank_lines_and_utf8_bom(self):
        address = self.mailbox("alpha", "firsthidden.com")
        result = parse_accounts(f"\ufeff{address}:Secret!1234\n\n", "firstmail")
        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()
