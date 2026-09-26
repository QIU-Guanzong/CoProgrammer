import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "coprogrammer"


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


class PluginPackageTests(unittest.TestCase):
    def test_portable_manifest_and_openai_extension_are_present(self) -> None:
        manifest = read_json(PLUGIN_ROOT / "plugin.json")

        self.assertEqual(
            manifest["$schema"],
            "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        )
        self.assertEqual(manifest["name"], "coprogrammer")
        self.assertRegex(manifest["version"], r"^\d+\.\d+\.\d+-[0-9A-Za-z.-]+$")
        self.assertEqual(
            manifest["extensions"]["com.openai"]["interface"]["displayName"],
            "CoProgrammer",
        )

    def test_claude_marketplace_and_plugin_identity_match(self) -> None:
        marketplace = read_json(REPO_ROOT / ".claude-plugin" / "marketplace.json")
        entry = next(item for item in marketplace["plugins"] if item["name"] == "coprogrammer")
        source = entry["source"]
        self.assertTrue(source.startswith("./"))
        self.assertNotIn("..", Path(source).parts)

        resolved_source = (REPO_ROOT / source).resolve()
        self.assertTrue(resolved_source.is_relative_to(REPO_ROOT.resolve()))
        self.assertTrue((resolved_source / ".claude-plugin" / "plugin.json").is_file())

        claude_manifest = read_json(resolved_source / ".claude-plugin" / "plugin.json")
        portable_manifest = read_json(resolved_source / "plugin.json")
        self.assertEqual(entry["name"], claude_manifest["name"])
        self.assertEqual(claude_manifest["name"], portable_manifest["name"])
        self.assertEqual(claude_manifest["version"], portable_manifest["version"])

    def test_codex_marketplace_points_to_the_portable_package(self) -> None:
        marketplace = read_json(REPO_ROOT / ".agents" / "plugins" / "marketplace.json")
        entry = next(item for item in marketplace["plugins"] if item["name"] == "coprogrammer")

        self.assertEqual(marketplace["name"], "coprogrammer-codex")
        self.assertEqual(entry["source"]["source"], "local")
        self.assertEqual(entry["source"]["path"], "./plugins/coprogrammer")
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
        self.assertEqual(entry["policy"]["authentication"], "ON_INSTALL")
        self.assertEqual(entry["category"], "Productivity")
        self.assertTrue((REPO_ROOT / entry["source"]["path"] / "plugin.json").is_file())

    def test_codex_compatibility_manifest_tracks_portable_version(self) -> None:
        portable = read_json(PLUGIN_ROOT / "plugin.json")
        codex = read_json(PLUGIN_ROOT / ".codex-plugin" / "plugin.json")

        self.assertEqual(codex["name"], portable["name"])
        self.assertEqual(codex["version"], portable["version"])
        self.assertEqual(codex["skills"], "./skills/")

    def test_packaged_skills_do_not_assume_consumer_source_tree(self) -> None:
        skill_files = sorted((PLUGIN_ROOT / "skills").glob("*/SKILL.md"))
        self.assertEqual(len(skill_files), 5)

        for skill_file in skill_files:
            content = skill_file.read_text(encoding="utf-8")
            with self.subTest(skill=skill_file.parent.name):
                self.assertNotIn("PYTHONPATH=src", content)
                self.assertIn("coprogrammer", content)
                self.assertIn("CLI", content)


if __name__ == "__main__":
    unittest.main()
