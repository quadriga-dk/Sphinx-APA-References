import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from sphinx.application import Sphinx


class IncollectionBibliographyTests(unittest.TestCase):
    def test_html_build_renders_incollection_links_with_optional_publisher(self):
        cases = {
            "doi_only": {
                "doi": "10.1234/doi-only",
                "publisher": "Example Press",
            },
            "both": {
                "doi": "10.1234/both",
                "url": "https://example.com/both",
                "publisher": "Example Press",
            },
            "no_publisher": {
                "doi": "10.1234/no-publisher",
                "url": "https://example.com/no-publisher",
            },
            "url_only": {"url": "https://example.com/url-only"},
            "no_links": {},
        }
        entries = []
        for key, web_fields in cases.items():
            fields = {
                "author": "Doe, Jane",
                "editor": "Smith, John",
                "title": "A Chapter",
                "booktitle": "A Sample Book",
                "year": "2024",
                "pages": "12--34",
                **web_fields,
            }
            body = ",\n".join(
                f"    {name} = {{{value}}}" for name, value in fields.items()
            )
            entries.append(f"@incollection{{{key},\n{body}\n}}")

        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "source"
            source.mkdir()
            (source / "conf.py").write_text(
                'extensions = ["sphinx_apa_references"]\n'
                'bibtex_bibfiles = ["references.bib"]\n'
                'master_doc = "index"\n',
                encoding="utf-8",
            )
            (source / "references.bib").write_text(
                "\n\n".join(entries), encoding="utf-8"
            )
            (source / "index.rst").write_text(
                "References\n==========\n\n"
                ".. bibliography::\n   :all:\n",
                encoding="utf-8",
            )
            warnings = StringIO()
            app = Sphinx(
                srcdir=str(source),
                confdir=str(source),
                outdir=str(root / "html"),
                doctreedir=str(root / "doctrees"),
                buildername="html",
                status=StringIO(),
                warning=warnings,
                freshenv=True,
                warningiserror=True,
            )
            app.build(force_all=True)
            html = (root / "html" / "index.html").read_text(encoding="utf-8")

            self.assertEqual(app.statuscode, 0, warnings.getvalue())
            for key, fields in cases.items():
                with self.subTest(entry=key):
                    if "doi" in fields:
                        self.assertIn(
                            f'href="https://doi.org/{fields["doi"]}"', html
                        )
                        self.assertIn(f'doi:{fields["doi"]}', html)
                        if "url" in fields:
                            self.assertNotIn(fields["url"], html)
                    elif "url" in fields:
                        self.assertIn(f'href="{fields["url"]}"', html)
            self.assertNotIn("missing publisher", html)
            self.assertIn("A Sample Book", html)


if __name__ == "__main__":
    unittest.main()
