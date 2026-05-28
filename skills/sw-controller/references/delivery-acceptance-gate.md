# 交付验收门禁

## 触发时机

交付检查清单全部 ✅ 后，最终部署前。

## 门禁清单

### G1: 质量门禁

- [ ] 所有 Reviewer Logic 发现: 0 P0, 0 P1
- [ ] 所有 Reviewer Security 发现: 0 P0, 0 P1
- [ ] 所有 Reviewer Performance 发现: 0 P0, 0 P1
- [ ] 单元测试 + API 测试: 100% PASS
- [ ] 集成测试: 100% PASS or SKIP (有理由)
- [ ] AI 代码 acceptance rate ≥ 70%

### G2: 文档门禁

- [ ] CHANGELOG/Release Notes 已编写（面向用户，非面向开发者）
- [ ] 知识库已更新（至少 1 条 pattern/decision/lesson）
- [ ] README/配置文档反映最新状态

### G3: 部署门禁

- [ ] 数据库迁移回滚已测试
- [ ] 监控/告警已配置
- [ ] 回滚方案已确认（回滚负责人 + 预估时间）
- [ ] 特性开关已就绪（如适用）

### G4: 合规门禁

- [ ] 无已知高危安全漏洞
- [ ] 敏感数据处理合规
- [ ] 依赖项许可证检查通过

## 门禁输出

```
PASS: → 执行部署
FAIL: → 标记阻塞原因。最大重试 2 轮。
       P0/P1 安全问题 → 立即阻塞，不容许跳过
       其他 FAIL → 可人工签字跳过（需记录理由）
```

## 输出文件

门禁结果写入 `{project-root}/_context/memory/sw-shared/delivery/acceptance-gate-{requirement_id}.md`
