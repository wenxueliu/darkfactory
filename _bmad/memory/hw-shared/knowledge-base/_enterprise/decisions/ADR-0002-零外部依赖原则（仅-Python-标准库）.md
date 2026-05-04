# ADR-0002: 零外部依赖原则（仅 Python 标准库）

**状态:** `accepted`
**日期:** `2026-05-04`
**决策者:** `hw-controller`
**Scope:** enterprise

## 背景

harness-framework 是多 Agent 协作的核心引擎，需要运行在多个 Agent 的工作环境中。每个 Agent 的环境可能不同（Python 版本、操作系统、依赖管理工具），如果框架引入了外部 pip 包，Agent 环境需要额外安装依赖，增加了部署门槛和维护成本。

## 决策

**我们决定:** harness-framework 的所有核心模块（daemon、aggregator、watchdog、webapi、consul_client、message_bus）仅使用 Python 标准库，零外部依赖。

## 理由

1. Agent 运行在不同环境中（容器、裸机、CI 管道），零依赖意味着可以直接 `python -m harness_framework.daemon` 启动，无需任何 pip install
2. Consul HTTP API 可以通过标准库 urllib 访问，不需要 consul Python 客户端库
3. WebAPI 使用标准库 http.server.ThreadingHTTPServer，不需要 Flask/FastAPI 等框架
4. JSON 处理、base64 编解码、日期时间处理等全部使用标准库模块
5. 减少了 supply chain 攻击面（不需要审查第三方包的依赖树）
6. 测试直接 mock 标准库接口，不需要 mock 第三方库

## 考虑的替代方案

| 方案 | 优点 | 缺点 | 为什么不选 |
|------|------|------|-----------|
| Flask + Consul Python Client | 开发效率高，开箱即用 | 需要安装至少 3 个依赖包（Flask, requests, python-consul），版本兼容问题 | 每个 Agent 环境都需要 pip install 违背了"即拉即用"的设计目标 |
| FastAPI + httpx | 异步支持好，类型安全 | 需要安装 FastAPI + uvicorn + httpx + pydantic 等多个依赖 | 异步模型的收益在本场景中被单进程多线程模型覆盖，增加的依赖代价不值得 |
| 部分依赖（仅使用 requests） | 减少部分开发工作 | 仍然需要 pip install requests | Consul HTTP API 非常薄（主要就是 GET/PUT/DELETE），urllib 完全够用 |

## 后果

### 正面
- 部署简单：git clone + python 即可运行，不需要包管理
- 无版本冲突：没有 pip 依赖冲突需要解决
- 测试轻量：不需要 mock 第三方库，直接 mock 标准库 urllib
- Supply chain 安全：不需要审查和信任第三方包

### 负面
- 需要自己实现 Consul HTTP 协议细节（如 base64 解码、ModifyIndex 解析）
- http.server 的功能比 Flask/FastAPI 少（无请求验证、无路由装饰器）
- 不能复用社区生态中成熟的 Python 包
- 开发效率略低于使用现成框架
