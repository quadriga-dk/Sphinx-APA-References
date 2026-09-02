import unittest
from types import SimpleNamespace

from docutils import nodes

from sphinx_apa_references import move_multiple_backrefs_to_end


def html_app():
    return SimpleNamespace(builder=SimpleNamespace(format="html"))


class CitationBackrefTests(unittest.TestCase):
    def test_multiple_backrefs_are_appended_to_reference_text(self):
        doctree = nodes.document("", "")
        citation = nodes.citation(backrefs=["citation-1", "citation-2"])
        citation += nodes.label("", "sample")
        paragraph = nodes.paragraph("", "Reference text.")
        citation += paragraph
        doctree += citation

        move_multiple_backrefs_to_end(html_app(), doctree, "index")

        self.assertEqual(citation["backrefs"], [])
        self.assertEqual(paragraph.astext(), "Reference text. (1,2)")
        moved_backrefs = paragraph[-1]
        self.assertIsInstance(moved_backrefs, nodes.inline)
        self.assertEqual(moved_backrefs["classes"], ["backrefs"])
        links = list(moved_backrefs.findall(nodes.reference))
        self.assertEqual(
            [link["refid"] for link in links],
            ["citation-1", "citation-2"],
        )

    def test_single_backref_keeps_default_docutils_behavior(self):
        doctree = nodes.document("", "")
        citation = nodes.citation(backrefs=["citation-1"])
        paragraph = nodes.paragraph("", "Reference text.")
        citation += nodes.label("", "sample")
        citation += paragraph
        doctree += citation

        move_multiple_backrefs_to_end(html_app(), doctree, "index")

        self.assertEqual(citation["backrefs"], ["citation-1"])
        self.assertEqual(paragraph.astext(), "Reference text.")


if __name__ == "__main__":
    unittest.main()
