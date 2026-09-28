# Package lifecycle reference

## Package format

`package.py build` produces:

```text
harness-multiagents-{version}.tar.gz
harness-multiagents-{version}.tar.gz.sha256
```

The archive contains a root `harness-package.json` plus the skills, hooks,
agent templates, platform plugin files, documents, and the package installer.
The manifest is schema `1.0.0` and records the package version, source Git
revision, supported platforms/scopes, and a SHA-256 entry for each payload
file. Archives reject absolute paths, parent traversal, symbolic links, and
hard links during extraction.

## Repository index

Local and remote Git repositories use `packages/index.json`:

```json
{
  "schema_version": "1.0.0",
  "name": "harness-multiagents",
  "latest": "2.0.0",
  "releases": {
    "2.0.0": {
      "artifact": "harness-multiagents-2.0.0.tar.gz",
      "sha256": "...",
      "manifest": {"name": "harness-multiagents", "version": "2.0.0"}
    }
  }
}
```

The index is a distribution index, not a substitute for Git history. Remote
publishing clones the repository, updates this directory, creates a commit,
and pushes the selected branch. The command does not force-push or rewrite
unrelated files.

## Command matrix

| Command | Source | Side effect |
|---|---|---|
| `build` | Harness checkout | Writes an archive and checksum to `--output`. |
| `publish` | Archive | Writes local `packages/`, or commits/pushes a remote Git repository. |
| `download` | Archive, local index, HTTP index, or Git repository | Copies and validates one archive. |
| `install` | Any download source | Installs selected platform files and an installation record. |
| `init` | Current checkout or package source | Creates the workspace skeleton, then optionally installs. |

`install --scope project --target /path/to/project` is the explicit project
form. `install --scope user` defaults to the user's home directory; an
explicit `--target` is treated as the requested installation directory, which
also makes isolated testing possible.

## Agent mapping

The Agent should map natural-language requests as follows:

| User request | Command |
|---|---|
| “打包当前项目” | `build` |
| “发布到本地仓库” | `publish --repository /path` |
| “发布到远程仓库” | `publish --repository <git-url>` |
| “下载最新版” | `download --source <repository>` |
| “安装到这个项目” | `install --scope project --target <dir>` |
| “安装到用户目录” | `install --scope user` |
| “帮我初始化” | interview, then `init` |

Do not infer a remote URL, credentials, business domain, or user identity.
The Agent may default `latest`, `project`, `all`, and `general` only when the
user has not expressed a conflicting preference.

## Failure handling

- Invalid manifest/checksum: stop and report `BLOCKED`.
- Missing local repository version: report the available/latest resolution;
  do not select an arbitrary artifact.
- Missing Git: local build/download/install remain usable; remote Git actions
  are `BLOCKED`.
- Existing configuration: preserve it, report it as preserved, and ask before
  changing values that affect the workflow.
- Empty `services/`: setup is `READY` but development handoff is blocked until
  a source repository is placed under `services/`.
