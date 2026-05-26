# 交付检查清单

## 使用说明

在集成测试通过后、代码部署到生产环境前使用。

写入 `{project-root}/_context/memory/sw-shared/delivery/delivery-checklist-{requirement_id}.md`

---

# 交付检查清单: {需求标题}

**交付ID:** `{DELIVERY-YYYYMMDD-NNN}`
**关联需求:** `{REQ-YYYYMMDD-NNN}`
**目标环境:** `staging | production`
**计划交付时间:** `{timestamp}`

## 1. 代码就绪

- [ ] 所有 worktree 已合并到主分支，无冲突
- [ ] 代码审查通过（logic + security + performance review: 0 P0, 0 P1）
- [ ] 单元测试 + API 测试全部 PASS
- [ ] 集成测试全部 PASS
- [ ] 浏览器 E2E 测试全部 PASS (browser-e2e-results.yaml: 功能 + 非功能 + 兼容性)
- [ ] 视觉回归检查通过（无未预期的视觉变化）
- [ ] 代码覆盖率 ≥ 目标值（默认 80%）
- [ ] 无未解决的 TODO/FIXME（或已记录在 TODOS.md）

## 2. 文档就绪

- [ ] CHANGELOG 已更新
- [ ] API 文档已更新（如有新增/变更 endpoint）
- [ ] README 已更新（如有新增配置项或依赖）
- [ ] 知识库已更新（patterns, decisions, lessons）

## 3. 部署就绪

- [ ] 数据库迁移脚本已准备并测试回滚
- [ ] 环境变量/配置已在目标环境配置
- [ ] 特性开关已配置（如需要）
- [ ] 回滚方案已确认（预估回滚时间 < {N} 分钟）
- [ ] 监控/告警已配置（新增指标已添加）

## 4. 安全就绪

- [ ] 安全审查通过（0 P0, 0 P1 安全发现）
- [ ] 敏感数据未在日志/错误消息中暴露
- [ ] 依赖项安全扫描通过（无已知高危漏洞）

## 5. 发布就绪

- [ ] Release Notes 已编写（见 release-notes-template.md）
- [ ] 部署窗口已确认（业务低峰期）
- [ ] 值班/On-call 人员已知晓发布计划
- [ ] 回滚负责人已指定

## 6. 交付后验证

- [ ] 部署后 5 分钟内：冒烟测试 PASS
- [ ] 部署后 30 分钟内：关键指标无异常（错误率、延迟、吞吐量）
- [ ] 部署后 24 小时内：无 P0/P1 生产事故
- [ ] 交付复盘已完成（lessons learned 写入知识库）

## 7. 签署

| 角色 | 姓名 | 状态 | 时间 |
|------|------|------|------|
| 开发者 | {name} | ✅ 确认 | {timestamp} |
| Reviewer | {name} | ✅ 确认 | {timestamp} |
| 交付负责人 | {name} | ✅ 确认 | {timestamp} |
