import unittest

from pybtex.database import parse_string
from pybtex.plugin import find_plugin

from sphinx_apa_references import APANoInbookPagePrefixStyle, register_plugins


def render_entry(
    entry_type,
    pages=None,
    style_class=APANoInbookPagePrefixStyle,
    doi=None,
    url=None,
    howpublished=None,
    note=None,
):
    optional_fields = ""
    if pages:
        optional_fields += f"            pages = {{{pages}}},\n"
    if doi:
        optional_fields += f"            doi = {{{doi}}},\n"
    if url:
        optional_fields += f"            url = {{{url}}},\n"
    if howpublished:
        optional_fields += f"            howpublished = {{{howpublished}}},\n"
    if note:
        optional_fields += f"            note = {{{note}}},\n"

    bib_data = parse_string(
        f"""
        @{entry_type}{{sample,
            author = {{Doe, Jane}},
            editor = {{Smith, John}},
            title = {{A Sample Chapter}},
            booktitle = {{A Sample Book}},
            journal = {{A Sample Journal}},
            publisher = {{Example Press}},
            year = {{2024}},
{optional_fields}
        }}
        """,
        "bibtex",
    )
    entry = bib_data.entries["sample"]
    formatted = style_class().format_entry("sample", entry)
    return formatted.text.render_as("text")


class InbookPageFormattingTests(unittest.TestCase):
    def test_inbook_pages_do_not_render_page_prefix(self):
        rendered = render_entry("inbook", "12-34")

        self.assertRegex(rendered, r"A Sample Book, 12[-\u2013]34")
        self.assertNotRegex(rendered, r"A Sample Book \([^\)]*12[-\u2013]34\)")
        self.assertNotIn("pp. 12", rendered)
        self.assertNotIn("pp 12", rendered)
        self.assertNotIn("p. 12", rendered)

    def test_article_pages_do_not_render_page_prefix(self):
        rendered = render_entry("article", "12-34")

        self.assertRegex(rendered, r"A Sample Journal, 12[-\u2013]34")
        self.assertNotIn("pp. 12", rendered)
        self.assertNotIn("pp 12", rendered)
        self.assertNotIn("p. 12", rendered)

    def test_article_renders_only_doi_when_doi_and_url_exist(self):
        rendered = render_entry(
            "article",
            "12-34",
            doi="10.1234/article",
            url="https://example.com/article",
        )

        self.assertIn("doi:10.1234/article", rendered)
        self.assertNotIn("URL:", rendered)
        self.assertNotIn("https://example.com/article", rendered)

    def test_extension_registers_custom_apa_formatter(self):
        register_plugins()

        registered_style = find_plugin("pybtex.style.formatting", "apa")

        self.assertIs(registered_style, APANoInbookPagePrefixStyle)

    def test_registered_apa_formatter_removes_inbook_page_prefix(self):
        register_plugins()
        registered_style = find_plugin("pybtex.style.formatting", "apa")

        rendered = render_entry("inbook", "12-34", registered_style)

        self.assertRegex(rendered, r"A Sample Book, 12[-\u2013]34")
        self.assertNotRegex(rendered, r"A Sample Book \([^\)]*12[-\u2013]34\)")
        self.assertNotIn("pp. 12", rendered)

    def test_inbook_renders_doi_when_only_doi_exists(self):
        rendered = render_entry("inbook", "12-34", doi="10.1234/example")

        self.assertIn("doi:10.1234/example", rendered)
        self.assertNotIn("URL:", rendered)

    def test_inbook_renders_url_when_only_url_exists(self):
        rendered = render_entry(
            "inbook",
            "12-34",
            url="https://example.com/chapter",
        )

        self.assertIn("URL: https://example.com/chapter", rendered)
        self.assertNotIn("doi:", rendered)

    def test_inbook_renders_only_doi_when_doi_and_url_exist(self):
        rendered = render_entry(
            "inbook",
            "12-34",
            doi="10.1234/example",
            url="https://example.com/chapter",
        )

        self.assertIn("doi:10.1234/example", rendered)
        self.assertNotIn("URL:", rendered)
        self.assertNotIn("https://example.com/chapter", rendered)

    def test_book_renders_doi_when_only_doi_exists(self):
        rendered = render_entry("book", "12-34", doi="10.1234/book")

        self.assertIn("doi:10.1234/book", rendered)
        self.assertNotIn("URL:", rendered)

    def test_book_renders_url_when_only_url_exists(self):
        rendered = render_entry(
            "book",
            "12-34",
            url="https://example.com/book",
        )

        self.assertIn("URL: https://example.com/book", rendered)
        self.assertNotIn("doi:", rendered)

    def test_book_renders_only_doi_when_doi_and_url_exist(self):
        rendered = render_entry(
            "book",
            "12-34",
            doi="10.1234/book",
            url="https://example.com/book",
        )

        self.assertIn("doi:10.1234/book", rendered)
        self.assertNotIn("URL:", rendered)
        self.assertNotIn("https://example.com/book", rendered)

    def test_incollection_uses_chapter_format_and_prefers_doi(self):
        rendered = render_entry(
            "incollection",
            "12-34",
            doi="10.1234/collection",
            url="https://example.com/collection",
        )

        self.assertRegex(rendered, r"A Sample Book, 12[-\u2013]34")
        self.assertNotIn("pp.", rendered)
        self.assertIn("doi:10.1234/collection", rendered)
        self.assertNotIn("URL:", rendered)
        self.assertNotIn("https://example.com/collection", rendered)

    def test_online_renders_url_when_doi_missing(self):
        rendered = render_entry(
            "online",
            url="https://example.com/online",
        )

        self.assertIn("URL: https://example.com/online", rendered)
        self.assertNotIn("doi:", rendered)

    def test_online_prefers_doi_over_url(self):
        rendered = render_entry(
            "online",
            doi="10.1234/online",
            url="https://example.com/online",
        )

        self.assertIn("doi:10.1234/online", rendered)
        self.assertNotIn("URL:", rendered)
        self.assertNotIn("https://example.com/online", rendered)

    def test_misc_renders_misc_fields_and_prefers_doi(self):
        rendered = render_entry(
            "misc",
            doi="10.1234/misc",
            url="https://example.com/misc",
            howpublished="Research archive",
            note="Supplementary material",
        )

        self.assertIn("Doe, J. (2024)", rendered)
        self.assertIn("A Sample Chapter", rendered)
        self.assertIn("Research archive", rendered)
        self.assertIn("Supplementary material", rendered)
        self.assertIn("doi:10.1234/misc", rendered)
        self.assertNotIn("URL:", rendered)
        self.assertNotIn("https://example.com/misc", rendered)
        self.assertNotIn("A Sample Journal", rendered)

    def test_misc_renders_url_when_doi_missing(self):
        rendered = render_entry(
            "misc",
            url="https://example.com/misc",
        )

        self.assertIn("URL: https://example.com/misc", rendered)
        self.assertNotIn("doi:", rendered)


if __name__ == "__main__":
    unittest.main()
