"""Black-box tests: run mcps against a throwaway home folder."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MCPS = Path(__file__).resolve().parent.parent / "mcps"


def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


class McpsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(os.path.realpath(self.tmp.name))
        self.repo = self.home / "code" / "app"
        self.repo.mkdir(parents=True)
        git("init", "-q", cwd=self.repo)
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "init", cwd=self.repo)

        (self.home / ".claude.json").write_text(json.dumps({
            "mcpServers": {"github": {"type": "http", "url": "https://api.example.com/mcp/"}},
            "projects": {str(self.repo): {"mcpServers": {
                "vault": {"command": "/usr/local/bin/mcps",
                          "args": ["guard", str(self.repo), "--", "/opt/vault/vault-mcp", "--quiet"]},
            }}},
        }))
        (self.repo / ".mcp.json").write_text(json.dumps({"mcpServers": {"docs": {"command": "docs-mcp"}}}))
        (self.repo / ".codex").mkdir()
        (self.repo / ".codex" / "config.toml").write_text('[mcp_servers.music]\ncommand = "music-mcp"\n')
        (self.home / ".codex").mkdir()
        (self.home / ".codex" / "config.toml").write_text(
            '[mcp_servers.search]\nurl = "https://search.example.com/mcp"\nenabled = false\n'
        )

    def tearDown(self):
        self.tmp.cleanup()

    def run_mcps(self, *args, cwd=None):
        env = {"HOME": str(self.home), "PATH": os.environ["PATH"]}
        return subprocess.run([sys.executable, str(MCPS), *args], cwd=cwd or self.home,
                              env=env, capture_output=True, text=True)

    def sections(self, *args):
        out = self.run_mcps("--json", *args)
        self.assertEqual(out.returncode, 0, out.stderr)
        return {(s["scope"], s["dir"]): {(v["tool"], v["name"]): v for v in s["servers"]}
                for s in json.loads(out.stdout)}

    def test_lists_every_scope_and_tool(self):
        found = self.sections()
        home, repo = str(self.home), str(self.repo)
        self.assertEqual(set(found[("global", home)]), {("claude", "github"), ("codex", "search")})
        self.assertEqual(set(found[("local", repo)]), {("claude", "vault")})
        self.assertEqual(set(found[("project", repo)]), {("claude", "docs"), ("codex", "music")})

    def test_notes(self):
        found = self.sections()
        self.assertEqual(found[("global", str(self.home))][("codex", "search")]["note"], "disabled")
        music = found[("project", str(self.repo))][("codex", "music")]
        self.assertEqual(music["note"], "ignored: project not trusted")

    def test_trusted_codex_project_has_no_note(self):
        config = self.home / ".codex" / "config.toml"
        config.write_text(config.read_text() + f'\n[projects."{self.repo}"]\ntrust_level = "trusted"\n')
        music = self.sections()[("project", str(self.repo))][("codex", "music")]
        self.assertEqual(music["note"], "")

    def test_guarded_server_shows_wrapped_command(self):
        vault = self.sections()[("local", str(self.repo))][("claude", "vault")]
        self.assertTrue(vault["guarded"])
        self.assertEqual(vault["target"], "vault-mcp --quiet")

    def test_scan_finds_unopened_repos(self):
        other = self.home / "code" / "other"
        other.mkdir()
        git("init", "-q", cwd=other)
        (other / ".mcp.json").write_text(json.dumps({"mcpServers": {"x": {"command": "x"}}}))
        self.assertNotIn(("project", str(other)), self.sections())
        self.assertIn(("project", str(other)), self.sections("--scan", str(self.home / "code")))

    def test_table_output(self):
        out = self.run_mcps()
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("GLOBAL  every project", out.stdout)
        self.assertIn("repo only", out.stdout)
        self.assertNotIn("\033[", out.stdout)  # no color when not a terminal

    def test_wide_terminal_does_not_stretch_rows(self):
        env = {"HOME": str(self.home), "PATH": os.environ["PATH"], "COLUMNS": "300"}
        out = subprocess.run([sys.executable, str(MCPS)], cwd=self.home, env=env,
                             capture_output=True, text=True)
        self.assertLess(max(len(line) for line in out.stdout.splitlines()), 100)

    def test_guard_runs_only_in_its_repo(self):
        ok = self.run_mcps("guard", str(self.repo), "--", "echo", "started", cwd=self.repo)
        self.assertEqual((ok.returncode, ok.stdout), (0, "started\n"))

        worktree = self.home / "code" / "app-wt"
        git("worktree", "add", "-q", str(worktree), cwd=self.repo)
        refused = self.run_mcps("guard", str(self.repo), "--", "echo", "started", cwd=worktree)
        self.assertNotEqual(refused.returncode, 0)
        self.assertEqual(refused.stdout, "")
        self.assertIn("only runs in", refused.stderr)

        elsewhere = self.run_mcps("guard", str(self.repo), "--", "echo", "started", cwd=self.home)
        self.assertNotEqual(elsewhere.returncode, 0)


if __name__ == "__main__":
    unittest.main()
