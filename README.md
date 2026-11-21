# mcps

See every MCP server that Claude Code and Codex will load, by scope, across all your projects.

```
$ mcps -s

GLOBAL  every project
  ● claude  github     http   api.githubcopilot.com/mcp/

LOCAL  ~/code/infra
  ● claude  1password  stdio  1password-mcp                      repo only

PROJECT  ~/code/app  shared in the repo
  ● claude  app        stdio  uv run python -m app.mcp_server    needs approval
  ○ codex   spotify    stdio  run-spotify-mcp.sh                 ignored: project not trusted
```

`claude mcp list` and `codex mcp list` only show what's active in the folder you're in, for one tool. `mcps` reads both tools' config files and shows every server in one place, with the scope it lives in.

## Install

```sh
brew install js0n/tap/mcps
```

Or copy the single `mcps` file anywhere on your `PATH`. It needs Python 3.11 or newer and nothing else.

## Usage

```sh
mcps                 # list servers (instant)
mcps -s              # also check which Claude Code servers connect (a few seconds)
mcps --scan ~/code   # also include every repo directly inside ~/code
mcps --json          # machine-readable output
```

Set `MCPS_SCAN=~/code:~/work` to always include those folders.

### Scopes

| Scope | Applies to | Claude Code | Codex |
|---|---|---|---|
| global | every project | `~/.claude.json` | `~/.codex/config.toml` |
| local | one folder, private to you | `~/.claude.json`, per project path | (none) |
| project | everyone who clones the repo | `.mcp.json` | `.codex/config.toml` |

Notes in the list:

- **needs approval**: Claude Code asks before it starts a repo's `.mcp.json` servers. Run `claude` in that folder to approve them.
- **ignored: project not trusted**: Codex only reads a repo's `.codex/config.toml` once you trust the project.
- **disabled**: the server has `enabled = false` in Codex config.
- **failing**: with `-s`, Claude Code could not connect to it.

Projects come from the folders Claude Code has opened, the projects Codex knows about, the current folder, and any `--scan` folders. `CLAUDE_CONFIG_DIR` and `CODEX_HOME` are respected. Account connectors (claude.ai, ChatGPT) and plugin servers aren't stored in these files, so they aren't listed. The status check covers Claude Code only, since Codex has no health check command.

## Repo-only servers

Claude Code's local scope is keyed by folder, but it also applies inside **git worktrees** of that repo. If you give one repo a server with sensitive access, every worktree of it gets that server too.

`mcps guard` starts a server only when the agent runs inside the named repo itself:

```sh
cd ~/code/infra
claude mcp add --scope local 1password -- mcps guard "$PWD" -- /Applications/1Password.app/Contents/MacOS/1password-mcp
```

In a worktree, or anywhere else, the guard exits before starting the server, so the agent never connects to it. Subfolders of the repo still work. `mcps` marks guarded servers as **repo only**.

## Development

```sh
python3 -m unittest discover -s tests
```

## License

MIT
