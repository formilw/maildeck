import re
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


if __name__ == "__main__":
    unittest.main()
