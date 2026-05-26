#!/usr/bin/env python3
"""Unified deploy runner — auto-discovers the deployer for the target
environment and executes deploy / verify / rollback.

Usage:
  python deploy_runner.py --target test --package build/app.tar.gz
  python deploy_runner.py --target production --package build/app.tar.gz \\
      --image myapp:v1.2.3 --port 8080
  python deploy_runner.py --target test --rollback
  python deploy_runner.py --target test --verify --endpoint http://127.0.0.1:8080
  python deploy_runner.py --list

参照 ``sw-lint-checker/lint_runner.py`` 的设计:
- 自动发现部署器（内置 + deployers_local/）
- 按 ``--target`` 匹配部署器
- 统一入口，流水线只需调用此脚本
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Inject the skill's own deployers onto the path
_SKILL_DIR = Path(__file__).resolve().parent
if str(_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILL_DIR))


# -- CLI --------------------------------------------------------------------

def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="sw-deployer — 环境部署统一入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list                                  # 列出可用部署器
  %(prog)s --target test                            # 测试环境部署
  %(prog)s --target production --image myapp:v1.0   # 生产环境部署
  %(prog)s --target test --verify --endpoint http://127.0.0.1:8080
  %(prog)s --target test --rollback                 # 回滚
  %(prog)s --target test --package-info pkg.json    # 复杂包信息通过 JSON 文件传入
""",
    )

    # -- action selection --
    p.add_argument("--target", default="",
                   help="目标环境: test, production, staging, ...")
    p.add_argument("--list", action="store_true",
                   help="列出所有可用部署器并退出")
    p.add_argument("--verify", action="store_true",
                   help="仅执行健康检查（不部署）")
    p.add_argument("--rollback", action="store_true",
                   help="回滚当前部署")

    # -- package info --
    p.add_argument("--package", default="",
                   help="安装包路径（tar.gz / dir / binary）")
    p.add_argument("--name", default="",
                   help="服务名")
    p.add_argument("--version", default="",
                   help="版本号")
    p.add_argument("--image", default="",
                   help="Docker 镜像名（docker/k8s 模式）")
    p.add_argument("--tag", default="",
                   help="镜像 tag（docker/k8s 模式）")
    p.add_argument("--port", default="",
                   help="服务端口（默认 8080）")
    p.add_argument("--port2", default="", dest="port_raw",
                   help=argparse.SUPPRESS)
    p.add_argument("--args", default="", dest="exec_args",
                   help="启动参数（direct 模式）")
    p.add_argument("--executable", default="",
                   help="可执行文件路径（direct 模式）")
    p.add_argument("--env-vars", default="",
                   help="环境变量 JSON 字符串 或 JSON 文件路径")
    p.add_argument("--namespace", default="",
                   help="K8s namespace（k8s 模式）")
    p.add_argument("--replicas", default="",
                   help="副本数（k8s 模式）")
    p.add_argument("--package-info", default="",
                   help="JSON 文件路径，包含完整 PackageInfo")

    # -- verify options --
    p.add_argument("--endpoint", default="",
                   help="服务端点 URL（用于 verify）")
    p.add_argument("--health-timeout", type=int, default=30,
                   help="健康检查超时（秒），默认 30")

    # -- output --
    p.add_argument("--json", action="store_true",
                   help="以 JSON 格式输出结果")

    return p


# -- list mode -------------------------------------------------------------

def _list_deployers() -> None:
    """Print all discovered deployers and exit."""
    from deployers import discover_deployers

    deployers = discover_deployers()
    if not deployers:
        print("No deployers found.")
        return

    print(f"  {'TARGET':<16} {'CLASS':<32} {'METHOD':<12} {'SOURCE'}")
    print(f"  {'-' * 74}")
    for cls in sorted(deployers, key=lambda c: (c.target, c.method)):
        mod = cls.__module__
        source = "local" if "deployers_local" in mod else "built-in"
        print(f"  {cls.target:<14}   {cls.__name__:<30} {cls.method:<12} {source}")

    print(f"\n  {len(deployers)} deployer(s) available.")
    print()
    print("  Use --target <TARGET> to select a deployer.")


# -- main ------------------------------------------------------------------

def run(args: argparse.Namespace | None = None) -> DeployResult:
    """Main entry point.  Returns a ``DeployResult``."""
    from deployers.base import DeployResult

    if args is None:
        parser = _build_argparser()
        args = parser.parse_args()

    if args.list:
        _list_deployers()
        return DeployResult(status="SUCCESS")

    target = args.target or os.environ.get("DEPLOY_TARGET", "")
    if not target:
        print("ERROR: --target is required (e.g. --target test, --target production)",
              file=sys.stderr)
        print("       Use --list to see available deployers.", file=sys.stderr)
        sys.exit(2)

    # Discover the right deployer
    from deployers import deployer_for_target

    cls = deployer_for_target(target)
    if cls is None:
        print(f"ERROR: No deployer found for target '{target}'", file=sys.stderr)
        print("       Use --list to see available deployers.", file=sys.stderr)
        sys.exit(2)

    deployer = cls()
    source = "local" if "deployers_local" in cls.__module__ else "built-in"
    print(f"[deploy_runner] 目标: {target} → {cls.__name__} ({cls.method}, {source})",
          file=sys.stderr)

    # -- verify only mode --
    if args.verify:
        result = deployer.verify(
            endpoint=args.endpoint,
            timeout=args.health_timeout,
        )
        _print_result(result, args.json)
        return result

    # -- rollback mode --
    if args.rollback:
        result = deployer.rollback()
        _print_result(result, args.json)
        return result

    # -- deploy mode --
    package = _build_package(args)
    result = deployer.deploy(package)

    if result.status == "SUCCESS":
        print(f"[deploy_runner] 部署成功 → {result.endpoint or result.message}",
              file=sys.stderr)
    else:
        print(f"[deploy_runner] 部署失败: {result.error}", file=sys.stderr)

    _print_result(result, args.json)

    if result.status != "SUCCESS":
        sys.exit(1)

    return result


def _build_package(args: argparse.Namespace) -> PackageInfo:
    """Build a ``PackageInfo`` from CLI args."""
    from deployers.base import PackageInfo

    # If --package-info file is provided, load from JSON
    if args.package_info:
        try:
            with open(args.package_info) as f:
                data = json.load(f)
            return PackageInfo(
                path=data.get("path", ""),
                name=data.get("name", ""),
                version=data.get("version", ""),
                env_vars=data.get("env_vars", {}),
                extra=data.get("extra", {}),
            )
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"ERROR: 无法加载 --package-info: {e}", file=sys.stderr)
            sys.exit(2)

    # Parse --env-vars
    env_vars: dict[str, str] = {}
    if args.env_vars:
        ev = args.env_vars
        if os.path.isfile(ev):
            try:
                with open(ev) as f:
                    env_vars = json.load(f)
            except json.JSONDecodeError:
                env_vars = {}
        else:
            try:
                env_vars = json.loads(ev)
            except json.JSONDecodeError:
                env_vars = {}

    port = args.port or "8080"
    extra: dict = {}
    if args.image:
        extra["image"] = args.image
    if args.tag:
        extra["tag"] = args.tag
    if args.exec_args:
        extra["args"] = args.exec_args
    if args.executable:
        extra["executable"] = args.executable
    if args.namespace:
        extra["namespace"] = args.namespace
    if args.replicas:
        extra["replicas"] = args.replicas
    extra["port"] = port

    return PackageInfo(
        path=args.package or ".",
        name=args.name or os.path.basename(args.package or os.getcwd()),
        version=args.version or "latest",
        env_vars=env_vars,
        extra=extra,
    )


def _print_result(result: DeployResult, as_json: bool = False) -> None:
    from deployers.base import DeployResult
    if as_json:
        d = {
            "status": result.status,
            "target": result.target,
            "method": result.method,
            "endpoint": result.endpoint,
            "pid": result.pid,
            "container_id": result.container_id,
            "message": result.message,
            "error": result.error,
            "elapsed_ms": result.elapsed_ms,
        }
        # Include logs only on failure
        if result.status != "SUCCESS" and result.logs:
            d["logs"] = result.logs[:2000]
        json.dump(d, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        flag = "OK" if result.status == "SUCCESS" else "FAIL"
        print(f"[{flag}] {result.message}")
        if result.error:
            print(f"       Error: {result.error}")
        if result.endpoint:
            print(f"       Endpoint: {result.endpoint}")
        print(f"       Elapsed: {result.elapsed_ms}ms")


# -- CLI entry point --------------------------------------------------------

if __name__ == "__main__":
    run()
