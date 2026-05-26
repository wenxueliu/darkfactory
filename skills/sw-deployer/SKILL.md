---
name: sw-deployer
description: 环境部署器 — 测试/生产环境统一部署入口，支持 direct/docker/k8s
---

# sw-deployer — 环境部署器

## 触发词

`deploy`, `部署`, `环境部署`, `发布`, `deploy to test`, `deploy to production`,
`deployment`, `environment deploy`

## 核心能力

1. **环境抽象** — 统一接口，按 `--target` 选择对应环境的部署策略
2. **多方式支持** — 内置 direct（直接启动）、docker、k8s 三种部署方式
3. **可扩展** — 参照 checkers 模式，通过 ABC + 自动发现 + local 覆盖实现业务定制
4. **流水线集成** — 流水线只需调用 `deploy_runner.py --target <env>`，无需关心底层差异

## 使用方式

```bash
# 列出所有可用部署器
python deploy_runner.py --list

# 测试环境部署（内置 direct 模式）
python deploy_runner.py --target test --package ./build/myapp --port 8080

# 生产环境部署（内置 docker 模式）
python deploy_runner.py --target production --image myapp:v1.2.3 --port 8080

# 生产环境部署（k8s 模式，需 local override 指定 target="production"）
python deploy_runner.py --target production --name myapp --namespace prod

# 健康检查
python deploy_runner.py --target test --verify --endpoint http://127.0.0.1:8080

# 回滚
python deploy_runner.py --target production --rollback

# 通过 JSON 文件传入完整包信息
python deploy_runner.py --target test --package-info pkg.json

# 环境变量注入
python deploy_runner.py --target test --package ./build/app \\
  --env-vars '{"DB_HOST":"localhost","LOG_LEVEL":"debug"}'

# JSON 输出模式
python deploy_runner.py --target test --package ./build/app --json
```

## 架构

```
sw-deployer/
├── SKILL.md                      # 技能定义
├── deploy_runner.py              # 统一 CLI 入口（流水线调用此脚本）
├── deployers/                    # 内置部署器
│   ├── __init__.py              # 自动发现 + local-first 优先级
│   ├── base.py                  # Deployer ABC + PackageInfo + DeployResult
│   ├── direct_deployer.py       # 直接启动服务进程（测试环境默认）
│   ├── docker_deployer.py       # Docker 容器部署（生产环境默认）
│   └── k8s_deployer.py          # Kubernetes 部署
├── deployers_local/             # 业务方本地覆盖
│   └── _example.py              # 自定义部署器模板
└── references/                  # 参考文档
```

## 设计模式（参照 sw-lint-checker/checkers）

| 概念 | checkers | deployers |
|------|----------|-----------|
| ABC | `LintChecker` | `Deployer` |
| 匹配方法 | `handles(file_path)` | `handles(target, method)` |
| 配置载体 | `CheckResult` | `DeployResult` |
| 核心方法 | `check()` / `auto_fix()` | `deploy()` / `verify()` / `rollback()` |
| local 覆盖 | `checkers_local/` | `deployers_local/` |
| 统一入口 | `lint_runner.py` | `deploy_runner.py` |

## 内置部署器

| 部署器 | target | method | 适用场景 |
|--------|--------|--------|---------|
| DirectDeployer | `test` | `direct` | 本地/测试环境，直接启动进程 |
| DockerDeployer | `production` | `docker` | 生产环境，Docker 容器部署 |
| K8sDeployer | `production` | `k8s` | 生产环境，Kubernetes 集群部署 |

> 注意: `DockerDeployer` 和 `K8sDeployer` 的 `target` 都是 `"production"`。
> 匹配时按发现顺序返回第一个。如果需要用 k8s 部署生产环境，
> 请在 `deployers_local/` 中创建覆盖。

## 业务定制

### 场景 1: 测试环境用 Docker Compose

```python
# deployers_local/test_deployer.py
from deployers.base import Deployer, DeployResult, PackageInfo, run_command

class DockerComposeTestDeployer(Deployer):
    target = "test"
    method = "docker-compose"

    def deploy(self, package: PackageInfo) -> DeployResult:
        exit_code, stdout, stderr = run_command(
            ["docker-compose", "-f", package.extra.get("compose_file", "docker-compose.test.yml"),
             "up", "-d"],
            timeout=120,
        )
        if exit_code == 0:
            return DeployResult(status="SUCCESS", target=self.target,
                                method=self.method, message="Docker Compose up", logs=stdout)
        return DeployResult(status="FAILED", target=self.target,
                            method=self.method, error=stderr)

    def verify(self, endpoint="", timeout=30):
        # ... health check logic

    def rollback(self, package=None):
        # ... docker-compose down
```

### 场景 2: 生产环境用 Helm

```python
# deployers_local/production_deployer.py
from deployers.base import Deployer, DeployResult, PackageInfo, run_command

class HelmProductionDeployer(Deployer):
    target = "production"
    method = "helm"

    def deploy(self, package: PackageInfo) -> DeployResult:
        chart = package.extra.get("helm_chart", f"./charts/{package.name}")
        ns = package.extra.get("namespace", "default")
        exit_code, stdout, stderr = run_command(
            ["helm", "upgrade", "--install", package.name, chart,
             "-n", ns, "--set", f"image.tag={package.version}"],
            timeout=300,
        )
        # ...
```

## PackageInfo 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `path` | str | 安装包路径 |
| `name` | str | 服务名 |
| `version` | str | 版本号 |
| `env_vars` | dict | 注入的环境变量 |
| `extra` | dict | 业务自定义字段（image, port, namespace, replicas, ...） |

## 与其他 Skill 的集成

在流水线的集成测试阶段：

```
sw-task-decomposer → sw-plan-executor → sw-tdd-agent (build)
  → sw-deployer (deploy to test)       # <-- 部署到测试环境
  → sw-integration-tester (test)       # <-- 运行集成测试
  → sw-deployer (deploy to production) # <-- 部署到生产环境
  → sw-delivery-manager (release)
```
