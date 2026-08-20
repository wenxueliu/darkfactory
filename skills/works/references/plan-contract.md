# Works state contract

`.planning/works-*/state.json` 是唯一进度来源：

```text
SETUP_REQUIRED -> preflight
CONTRACT_REQUIRED -> 主 Agent 编写并校验 Req 契约
READY_FOR_IMPLEMENTATION -> 生产 checkpoint
READY_FOR_TEST -> 定向测试证据；生产修复需要时 rework -> READY_FOR_IMPLEMENTATION
READY_FOR_ACCEPTANCE -> finalize；失败时追加 repair Req
COMPLETE | PARTIAL（存在三次测试失败后跳过的 Req）
```

关键持久文件只有 `state.json`、`activity.jsonl`、`requirement-contract.json`、每个 Req 的 implementation/test evidence 和 `final-verification.json`。findings/decisions 按需追加，不创建第二套计划。
