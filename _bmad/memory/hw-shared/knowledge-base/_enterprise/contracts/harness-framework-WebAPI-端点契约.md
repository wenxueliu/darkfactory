# harness-framework WebAPI 端点契约

**Type:** API
**Created:** 2026-05-04
**Scope:** enterprise
**Author:** hw-controller

## Summary

harness-framework 的 WebAPI 模块基于 Python 标准库 http.server.ThreadingHTTPServer 提供业务看板查询和控制接口。所有端点返回 JSON 格式，支持跨域（CORS）访问。

## Details

WebAPI 基于 ThreadingHTTPServer 实现，每个请求在独立线程中处理。API 路径以 `/api/` 为前缀。支持 CORS（Access-Control-Allow-Origin: *），适用于前端看板直连。

## Context

前端看板（Vue 3 + Vite + Tailwind）通过此 API 查询工作流状态和发送控制信号。Agent 也可以通过 API 查看全局状态。

## Usage

### 查询类端点（GET）
| 端点 | 功能 | 返回格式 |
|------|------|---------|
| `GET /api/workflows` | 所有需求聚合视图（看板首屏） | `{"workflows": [{"req_id","title","control","total_tasks","done_tasks","phase","progress"},...]}` |
| `GET /api/workflow/<req_id>` | 单个需求的完整状态（含 tasks、context、dependencies） | `{"req_id","status","control","dependencies","tasks","context"}` |
| `GET /api/workflow/<req_id>/messages/<task_name>` | 查看任务的消息队列 | `{"req_id","task","messages": [...]}` |
| `GET /api/workflow/<req_id>/proposals` | 获取待确认的提案 | `{"req_id","status","proposals": [...]}` |
| `GET /api/sessions/<req_id>/<task_name>` | 查看任务的会话事件记录 | `{"req_id","task","events": [...]}` |
| `GET /api/agents` | 所有注册 Agent 列表及健康状态 | `{"agents": [{"agent_id","tags","meta","healthy"},...]}` |
| `GET /api/health` | 框架健康检测 | `{"ok": true, "service": "harness-framework"}` |

### 控制类端点（POST，JSON body）
| 端点 | body 格式 | 功能 |
|------|-----------|------|
| `POST /api/workflow/<req_id>/control` | `{"action": "PAUSE"|"RESUME"|"ABORT"|"RETRY", "task_name": "..."}` | 控制 workflow 生命周期 |
| `POST /api/workflow/<req_id>/messages` | `{"from": "...", "to": "...", "action": "...", "params": {...}}` | 发送消息给指定任务 |
| `POST /api/workflow/<req_id>/proposals` | `{"action": "confirm"|"reject", "accepted_tasks": [...], "rejected_tasks": [...]}` | 确认或拒绝 Agent 提案 |

### 控制信号说明
- `PAUSE`：暂停 workflow 的 DAG 推进（Aggregator 跳过此 req_id 的 tick）
- `RESUME`：删除 control 键，恢复调度
- `ABORT`：将所有非终态任务（PENDING/IN_PROGRESS/BLOCKED）设为 ABORTED
- `RETRY`：将指定 task 重置为 PENDING 并清除 error_message

### 异常响应
- `404`：`{"error": "not found"}`（不存在的端点或 workflow）
- `400`：`{"error": "invalid action"}` 等参数错误
- `500`：`{"error": "<异常详情>"}`（服务器内部错误）

### 实现说明
- 基于 `http.server.BaseHTTPRequestHandler`，路径路由在 `do_GET`/`do_POST` 中手工匹配
- 使用 `ThreadingHTTPServer` 处理并发请求
- ConsulClient 和 MessageBus 作为类属性注入到 Handler 中
- 日志格式复用框架的统一日志格式

## Related

_No content provided._
