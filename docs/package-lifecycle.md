# Harness 打包、发布与一键初始化

Harness 的发行物是带 `harness-package.json` 清单的 `tar.gz`。清单记录
版本、源 Git revision、支持的平台/安装范围和每个 payload 文件的 SHA-256。
安装时会先校验清单与文件哈希，再写入目标目录。

## 快速使用

在 Harness 仓库的 `services/multiagents/` 目录执行：

```bash
# 1. 打包
python package.py build --version 2.0.0 --output dist

# 2. 发布到本地目录仓库
python package.py publish \
  --package dist/harness-multiagents-2.0.0.tar.gz \
  --repository /srv/harness-packages

# 3. 从本地仓库下载最新版
python package.py download \
  --source /srv/harness-packages \
  --output /tmp/harness-download

# 4. 一键安装到项目
python package.py install \
  --source /srv/harness-packages \
  --target /path/to/project \
  --scope project \
  --platform claude,codex

# 5. 一键创建工作区并安装
python package.py init \
  --target /path/to/project \
  --platform all \
  --business-domain general \
  --enabled-reviewers security,logic,performance
```

远程 Git 仓库：

```bash
python package.py publish \
  --package dist/harness-multiagents-2.0.0.tar.gz \
  --repository https://git.example.com/team/harness-packages.git

python package.py install \
  --source https://git.example.com/team/harness-packages.git \
  --target /path/to/project \
  --platform codex
```

远程发布会 clone → 更新 `packages/index.json` → commit → push；不会强推，
也不会改写仓库中的无关文件。远程操作需要当前用户已经配置 Git 凭据。

## 安装范围

- `--scope project --target <dir>`：安装到项目目录。
- `--scope user`：默认安装到当前用户目录；适合全局技能与 hooks。
- `--platform claude,codex,opencode`：只启用指定平台，默认 `all`。
- `--minimal`：仅安装核心技能（沿用 `install.py` 的最小集合）。

安装完成会写入 `<target>/.harness/installation.json`，方便 Agent 查询当前
版本和平台。OpenCode 安装会复制插件和 skills，并保留已有配置文件。

## Agent 对话初始化

在 Agent 中直接说：

> 帮我把 Harness 安装到 `/path/to/project`，使用本地仓库最新版，启用 Codex，
> 业务域为 internal-tools，审核只保留 logic。

`sw-controller` 将请求路由到 `sw-setup`。`sw-setup` 会确认目标、来源、版本、
平台、业务域和写入计划，然后执行 `package.py init`。初始化会创建：

```text
services/
knowledge/
_context/config.yaml
_context/config.user.yaml
.worktree/
```

不会覆盖已有配置。`services/` 仍需要用户放入一个或多个独立 Git 源码仓；
目录为空时初始化完成，但开发流程会在服务发现前阻塞并给出下一步提示。

## 仓库结构

发布目录只维护 `packages/`：

```text
packages/
├── index.json
├── harness-multiagents-2.0.0.tar.gz
└── harness-multiagents-2.0.0.tar.gz.sha256
```

`index.json` 的 `latest` 指向最新版本，也可以通过 `--version` 安装历史版本。
本地目录和远程 Git 仓库使用相同索引格式，因此可以先离线验证，再迁移到远程。
