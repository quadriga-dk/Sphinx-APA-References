import os
import re
from dataclasses import dataclass, field

import pybtex.plugin
import sphinxcontrib.bibtex.plugin
from docutils import nodes
from names.firstlast import NameStyle as APAFirstLastNameStyle

# formatting.apa resolves firstlast at import time, so pin the matching
# pybtex-apa-style name plugin before other distributions can shadow it.
pybtex.plugin.register_plugin(
    "pybtex.style.names",
    "firstlast",
    APAFirstLastNameStyle,
    force=True,
)

from formatting.apa import APAStyle, date, editor_names
from pybtex.richtext import Symbol, Text
from pybtex.style.formatting import toplevel
from pybtex.style.template import FieldIsMissing, node
from pybtex.style.template import field as template_field
from pybtex.style.template import (
    first_of,
    join,
    optional,
    optional_field,
    sentence,
    tag,
)
from sphinx.application import Sphinx
from sphinx.util.fileutil import copy_asset_file
from sphinxcontrib.bibtex.directives import BibliographyDirective
from sphinxcontrib.bibtex.style.referencing import BracketStyle
from sphinxcontrib.bibtex.style.referencing.author_year import \
    AuthorYearReferenceStyle


class APABibliographyDirective(BibliographyDirective):
    """Same as BibliographyDirective, but forces style='apa'."""

    def run(self):
        # ensure 'style' option is set to 'apa' unless user overrides it
        self.options.setdefault("style", "apa")
        nodes = super().run()
        print(nodes[0].children)
        return nodes


def bracket_style() -> BracketStyle:
    return BracketStyle(
        left="(",
        right=")",
    )


@dataclass
class MyReferenceStyle(AuthorYearReferenceStyle):
    bracket_parenthetical: BracketStyle = field(default_factory=bracket_style)
    bracket_textual: BracketStyle = field(default_factory=bracket_style)
    bracket_author: BracketStyle = field(default_factory=bracket_style)
    bracket_label: BracketStyle = field(default_factory=bracket_style)
    bracket_year: BracketStyle = field(default_factory=bracket_style)


def format_pages_without_prefix(text):
    page_parts = re.split(r"[-\u2012\u2013\u2014\u2015]+", str(text))
    return Text(Symbol("ndash")).join(page_parts)


pages_without_prefix = template_field(
    "pages",
    apply_func=format_pages_without_prefix,
)


@node
def inbook_details_without_parentheses(children, context, **kwargs):
    assert not children

    entry = context["entry"]
    parts = []

    edition = entry.fields.get("edition")
    if edition:
        parts.append(Text(edition, " ed."))

    volume = entry.fields.get("volume")
    if volume:
        parts.append(Text("Vol.", Symbol("nbsp"), volume))

    pages = entry.fields.get("pages")
    if pages:
        parts.append(format_pages_without_prefix(pages))

    if not parts:
        raise FieldIsMissing("pages", entry)

    return Text(", ").join(parts)


class APANoInbookPagePrefixStyle(APAStyle):
    """Customized APA style for the bibliography entry types we support."""

    def format_preferred_web_ref(self, e):
        return sentence(add_period=False)[
            first_of[
                optional[self.format_doi(e)],
                optional[self.format_url(e)],
            ]
        ]

    def format_creator_and_date(self, e):
        if "author" in e.persons:
            creator = self.format_names("author", as_sentence=False)
        elif "editor" in e.persons:
            creator = self.format_editor(e, as_sentence=False)
        else:
            creator = optional_field("organization")

        return sentence(sep=" ")[
            creator,
            join[
                "(",
                first_of[
                    optional[date],
                    optional_field("date"),
                    "n.d.",
                ],
                ")",
            ],
        ]

    def get_article_template(self, e):
        # Required fields: author, title, journal, year
        # Optional fields: volume, number, pages, month, note, key, doi, url
        volume_and_pages = first_of[
            optional[
                join[
                    self.format_volume(e, for_article=True),
                    optional[", ", pages_without_prefix],
                ],
            ],
            pages_without_prefix,
        ]
        return toplevel[
            self.format_names("author"),
            sentence[
                join["(", date, ")"],
            ],
            self.format_title(e, "title"),
            sentence[
                tag("em")[template_field("journal")],
                optional[volume_and_pages],
            ],
            sentence[optional_field("note")],
            self.format_preferred_web_ref(e),
        ]
        
    def get_misc_template(self, e):
        # All fields are optional for BibTeX misc entries.
        # Supported fields: author/editor, organization, title, year/date,
        #                   howpublished, note, doi, url
        return toplevel[
            self.format_creator_and_date(e),
            optional[self.format_btitle(e, "title")],
            sentence[optional_field("howpublished")],
            sentence[optional_field("note")],
            self.format_preferred_web_ref(e),
        ]

    def get_book_template(self, e):
        # Required fields: author/editor, title, publisher, year
        # Optional fields: volume, series, address, edition, month, note, key,
        #                  isbn, doi, url
        return toplevel[
            self.format_author_or_editor_and_date(e),
            sentence(sep=" ")[
                self.format_btitle(e, "title"),
                optional[
                    sentence[
                        optional[template_field("edition"), " ed."],
                        self.format_volume(e),
                    ]
                ],
            ],
            sentence(sep=": ")[
                optional_field("address"),
                template_field("publisher"),
            ],
            sentence[optional_field("note")],
            self.format_preferred_web_ref(e),
        ]
    
    def get_inbook_template(self, e):
        # Required fields: author/editor, title, chapter/pages, publisher, year
        # Optional fields: volume, series, address, edition, month, note, key,
        #                  doi, url
        return toplevel[
            sentence(sep=" ")[
                self.format_names("author"),
                join["(", date, ")"],
            ],
            self.format_title(e, "title"),
            sentence(sep=" ")[
                optional[
                    "In ",
                    editor_names(),
                    ",",
                ],
                join[
                    self.format_btitle(e, "booktitle", as_sentence=False),
                    optional[", ", inbook_details_without_parentheses()],
                ],
            ],
            sentence(sep=": ")[
                optional_field("address"),
                template_field("publisher"),
            ],
            sentence[optional_field("note")],
            self.format_preferred_web_ref(e),
        ]

    def get_incollection_template(self, e):
        return self.get_inbook_template(e)

    def get_online_template(self, e):
        # Required field: title
        # Optional fields: author/editor, organization, year/date, note,
        #                  doi, url
        return toplevel[
            self.format_creator_and_date(e),
            self.format_title(e, "title"),
            sentence[optional_field("note")],
            self.format_preferred_web_ref(e),
        ]


def copy_stylesheet(app: Sphinx, exc: None) -> None:
    base_dir = os.path.dirname(__file__)
    style = os.path.join(base_dir, "assets", "apastyle.css")

    if app.builder.format == "html" and not exc:
        static_dir = os.path.join(app.builder.outdir, "_static")

        copy_asset_file(style, static_dir)


def override_config(app, config):
    # This runs after the user's conf is read
    config.bibtex_reference_style = "author_year_round"  # override or set


def move_multiple_backrefs_to_end(app, doctree, docname):
    """Move citation backrefs after the rendered bibliography text."""
    if app.builder.format != "html":
        return

    for citation in doctree.findall(nodes.citation):
        backrefs = citation.get("backrefs", [])
        if len(backrefs) < 2:
            continue

        paragraphs = list(citation.findall(nodes.paragraph))
        if not paragraphs:
            continue

        backrefs_node = nodes.inline(classes=["backrefs"])
        backrefs_node += nodes.Text("(")
        for index, backref in enumerate(backrefs, 1):
            if index > 1:
                backrefs_node += nodes.Text(",")
            backrefs_node += nodes.reference(
                "",
                str(index),
                refid=backref,
                internal=True,
            )
        backrefs_node += nodes.Text(")")

        paragraphs[-1] += nodes.Text(" ")
        paragraphs[-1] += backrefs_node
        citation["backrefs"] = []


def register_plugins():
    sphinxcontrib.bibtex.plugin.register_plugin(
        "sphinxcontrib.bibtex.style.referencing",
        "author_year_round",
        MyReferenceStyle,
        force=True,
    )
    pybtex.plugin.register_plugin(
        "pybtex.style.formatting",
        "apa",
        APANoInbookPagePrefixStyle,
        force=True,
    )


def setup(app):
    app.setup_extension("sphinxcontrib.bibtex")
    register_plugins()
    app.add_directive("bibliography", APABibliographyDirective, override=True)
    app.connect("build-finished", copy_stylesheet)
    app.add_css_file("apastyle.css")
    app.connect("config-inited", override_config)
    app.connect("doctree-resolved", move_multiple_backrefs_to_end)
