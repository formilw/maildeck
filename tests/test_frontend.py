import json
import re
import subprocess
import unittest
from pathlib import Path


STATIC = Path(__file__).resolve().parents[1] / "static"


class FrontendTests(unittest.TestCase):
    def test_reader_renders_structured_links_with_safe_external_navigation(self):
        app = (STATIC / "app.js").read_text()
        self.assertIn("function renderMessageBody(message)", app)
        self.assertIn("message.bodyParts", app)
        self.assertIn("link.target = '_blank';", app)
        self.assertIn("link.rel = 'noopener noreferrer nofollow';", app)

    def test_combined_mailbox_list_preserves_source_folder_for_opening(self):
        app = (STATIC / "app.js").read_text()
        self.assertIn("button.dataset.folder = message.folder || 'INBOX';", app)
        self.assertIn("openMessage(message.uid, message.folder)", app)
        self.assertIn("?folder=${encodeURIComponent(folder)}", app)
        self.assertIn("message-folder", app)

    def test_every_static_translation_key_exists_in_both_languages(self):
        html = (STATIC / "index.html").read_text()
        i18n = (STATIC / "i18n.js").read_text()
        keys = set(re.findall(r'data-i18n(?:-placeholder|-aria|-title)?="([A-Za-z0-9]+)"', html))
        ru, en = i18n.split("  en: {", 1)
        for key in keys:
            self.assertIn(f"{key}:", ru, key)
            self.assertIn(f"{key}:", en, key)

    def test_all_localizable_russian_html_copy_is_annotated(self):
        html = (STATIC / "index.html").read_text()
        for tag in re.findall(r"<[^>]+>", html):
            if re.search(r"[А-Яа-яЁё]", tag):
                self.assertRegex(tag, r"data-i18n(?:-placeholder|-aria|-title)?=", tag)
        text_nodes = [value.strip() for value in re.findall(r">([^<>]+)<", html)]
        for value in text_nodes:
            if re.search(r"[А-Яа-яЁё]", value):
                self.assertRegex(html, rf'data-i18n="[A-Za-z0-9]+">{re.escape(value)}<', value)

    def test_dynamic_visible_russian_copy_lives_only_in_i18n_catalog(self):
        app = (STATIC / "app.js").read_text()
        self.assertIsNone(re.search(r"[А-Яа-яЁё]", app), "app.js contains untranslated Russian copy")

    def test_input_focus_has_no_aggressive_outline(self):
        css = (STATIC / "styles.css").read_text()
        self.assertIn("input:focus-visible { outline: none; }", css)
        self.assertIn("label:not(.drop-zone):focus-within { outline: none;", css)
        self.assertNotIn("input:focus-visible, label:focus-within", css)

    def test_language_is_initialized_from_saved_preference(self):
        app = (STATIC / "app.js").read_text()
        self.assertIn("lang: localStorage.getItem('maildeck-language')", app)
        self.assertIn("applyStaticTranslations();", app)
        self.assertIn("#language-toggle", app)

    def test_motion_hooks_cover_provider_and_dynamic_panels(self):
        app = (STATIC / "app.js").read_text()
        css = (STATIC / "styles.css").read_text()
        self.assertIn("restartAnimation($('#account-list'), 'is-switching')", app)
        self.assertIn("restartAnimation($('#reader-pane'), 'is-revealing')", app)
        self.assertIn(".account-list.is-switching", css)
        self.assertIn(".reader-pane.is-revealing", css)
        self.assertIn(".form-section.is-entering", css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertIn(".sync-copy { display: block; white-space: nowrap; }", css)

    def test_reader_is_an_independent_scroll_region_with_safe_text_wrapping(self):
        css = (STATIC / "styles.css").read_text()
        self.assertRegex(
            css,
            r"\.reader-pane\s*\{[^}]*overflow-y:\s*auto;[^}]*overscroll-behavior:\s*contain;",
        )
        self.assertRegex(css, r"\.reader-content\s*\{[^}]*width:\s*min\(100%,\s*850px\);")
        self.assertIn("padding-inline: clamp(28px, 5vw, 72px);", css)
        self.assertIn("padding-bottom: max(88px, env(safe-area-inset-bottom));", css)
        self.assertRegex(
            css,
            r"\.reader-body\s*\{[^}]*max-width:\s*72ch;[^}]*word-break:\s*break-word;",
        )
        self.assertIn("scrollbar-gutter: stable;", css)
        self.assertIn(".reader-pane::-webkit-scrollbar-thumb", css)
        self.assertRegex(css, r"\.workspace\s*\{[^}]*min-height:\s*0;[^}]*overflow:\s*hidden;")
        self.assertRegex(css, r"\.mail-layout\s*\{[^}]*overflow:\s*hidden;")
        app = (STATIC / "app.js").read_text()
        self.assertIn("reader.scrollTop = 0;", app)

    def test_all_dynamic_translation_keys_exist_in_both_languages(self):
        app = (STATIC / "app.js").read_text()
        html = (STATIC / "index.html").read_text()
        i18n = (STATIC / "i18n.js").read_text()
        output = subprocess.run(
            ["node", "-e", i18n + "\nconsole.log(JSON.stringify(I18N));"],
            check=True, capture_output=True, text=True,
        ).stdout
        catalog = json.loads(output)
        keys = set(re.findall(r"translate\(['\"]([A-Za-z0-9]+)['\"]", app))
        keys.update(re.findall(r'data-i18n(?:-placeholder|-aria|-title)?="([A-Za-z0-9]+)"', html))
        self.assertEqual(set(catalog["ru"]), set(catalog["en"]))
        self.assertFalse(keys - set(catalog["ru"]), keys - set(catalog["ru"]))

    def test_destructive_actions_use_site_dialog_not_browser_confirm(self):
        app = (STATIC / "app.js").read_text()
        html = (STATIC / "index.html").read_text()
        self.assertNotIn("window.confirm", app)
        self.assertIn('id="confirm-dialog"', html)
        self.assertIn("requestAccountDeletion", app)
        self.assertIn("deleteSelectedAccounts", app)

    def test_sidebar_account_organization_and_copy_controls_exist(self):
        app = (STATIC / "app.js").read_text()
        html = (STATIC / "index.html").read_text()
        for marker in (
            'id="selection-toggle"', 'id="create-folder-button"', 'id="selection-bar"',
            'id="copy-email-button"', 'id="folder-select"', 'id="folder-dialog"',
        ):
            self.assertIn(marker, html)
        for behavior in (
            "toggleAccountPin", "moveAccountToFolder", "toggleFolderPin",
            "copyActiveEmail", "renderAccountSections",
        ):
            self.assertIn(behavior, app)

    def test_browser_qa_preserves_existing_accounts_and_folders(self):
        qa = (Path(__file__).resolve().parents[1] / "tests" / "browser_qa.js").read_text()
        self.assertIn("const baseline = await request(session, '/api/accounts');", qa)
        self.assertNotIn("payload.accounts.map(a=>a.id)", qa)
        self.assertIn("browser QA must preserve baseline accounts", qa)
        self.assertIn("browser QA must preserve baseline folders", qa)
        self.assertIn("MAILDECK_QA_DIR", qa)
        self.assertIn("MAILDECK_CDP_URL", qa)


if __name__ == "__main__":
    unittest.main()
