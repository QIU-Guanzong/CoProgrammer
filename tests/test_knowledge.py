import unittest
from importlib import resources
from pathlib import Path
from unittest.mock import patch

from coprogrammer import knowledge


REPO_ROOT = Path(__file__).resolve().parents[1]


class KnowledgeTests(unittest.TestCase):
    def test_catalog_is_complete_and_metadata_is_detached(self):
        catalog = knowledge.documents()
        self.assertEqual(len(catalog), 12)
        self.assertEqual(len({doc["id"] for doc in catalog}), len(catalog))
        self.assertEqual({doc["name"] for doc in catalog if doc["kind"] == "template"},
                         {"AGENTS", "CLAUDE", "copilot-instructions", "COORDINATION", "task-brief", "handoff"})
        for doc in catalog:
            with self.subTest(document=doc["id"]):
                self.assertEqual(set(doc), {"id", "kind", "name", "title", "description", "mime_type", "uri"})
                self.assertTrue(all(isinstance(value, str) and value for value in doc.values()))
                self.assertEqual(doc["mime_type"], "text/markdown")
                self.assertEqual(doc["uri"], "coprogrammer://" + doc["id"])
        original_id = catalog[0]["id"]
        catalog[0]["id"] = "templates/untrusted"
        catalog.clear()
        self.assertEqual(knowledge.documents()[0]["id"], original_id)

    def test_every_document_is_an_available_utf8_package_resource(self):
        for doc in knowledge.documents():
            with self.subTest(document=doc["id"]):
                content = knowledge.read_document(doc["id"])
                self.assertTrue(content.strip())
                parts = (("assets", "skills", doc["name"], "SKILL.md")
                         if doc["kind"] == "skill"
                         else ("assets", "templates", doc["name"] + ".md"))
                packaged = resources.files("coprogrammer").joinpath(*parts).read_bytes()
                self.assertEqual(content.encode("utf-8"), packaged)

    def test_bundled_skills_match_canonical_plugin_sources_byte_for_byte(self):
        skill_docs = [doc for doc in knowledge.documents() if doc["kind"] == "skill"]
        canonical_root = REPO_ROOT / "plugins" / "coprogrammer" / "skills"
        self.assertEqual({doc["name"] for doc in skill_docs},
                         {path.parent.name for path in canonical_root.glob("*/SKILL.md")})
        for doc in skill_docs:
            with self.subTest(skill=doc["name"]):
                source = (canonical_root / doc["name"] / "SKILL.md").read_bytes()
                self.assertEqual(knowledge.read_document(doc["id"]).encode("utf-8"), source)
                lines = source.decode("utf-8").splitlines()
                self.assertEqual(lines[0], "---")
                frontmatter = lines[1:lines.index("---", 1)]
                self.assertIn("name: " + doc["name"], frontmatter)
                self.assertTrue(any(line.startswith("description: ") for line in frontmatter))

    def test_unknown_or_path_like_input_is_rejected_before_resource_access(self):
        invalid = ("", "templates/../AGENTS", "templates/AGENTS.md", "templates/agents",
                   "templates/AGENTS/", "templates/AGENTS\x00", "./templates/AGENTS",
                   "templates/%2e%2e/AGENTS", "templates\\AGENTS", "/etc/passwd",
                   "file:///etc/passwd", "https://example.com/guide.md",
                   "coprogrammer://templates/AGENTS", "skills/coprogammer-active-sync",
                   None, 1, [], {})
        with patch.object(knowledge.resources, "files") as files:
            for document_id in invalid:
                with self.subTest(document=document_id), self.assertRaisesRegex(RuntimeError, "unknown knowledge document"):
                    knowledge.read_document(document_id)
            files.assert_not_called()

    def test_missing_or_invalid_resource_fails_with_runtime_error(self):
        for failure in (FileNotFoundError(), UnicodeError()):
            with self.subTest(failure=type(failure).__name__):
                with patch.object(knowledge.resources, "files") as files:
                    files.return_value.joinpath.return_value.read_bytes.side_effect = failure
                    with self.assertRaisesRegex(RuntimeError, "bundled knowledge document is unavailable"):
                        knowledge.read_document("templates/AGENTS")


if __name__ == "__main__":
    unittest.main()
