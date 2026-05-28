# E2E 设计验证器 (E2E Design Validator)

## 触发时机

E2E 测试设计文档 (`designs/{requirement_id}-e2e-design.md`) 完成后，进入设计门禁之前。

## 验证清单

### V1: 功能 E2E

- [ ] 每个用户旅程 ≥ 1 条 functional happy E2E
- [ ] 关键旅程 (支付/数据修改/权限变更) ≥ 1 条 functional error E2E
- [ ] 关键旅程 ≥ 1 条 boundary E2E
- [ ] 每个 E2E 用例的 GIVEN/WHEN/THEN/CLEANUP 为具体值

### V2: 非功能 E2E (按 business_domain 矩阵检查)

| Domain | 最少安全 | 最少性能 | 最少可靠性 | 最少无障碍 |
|--------|---------|---------|----------|----------|
| fintech | ≥6 | ≥3 | ≥5 | ≥4 |
| ecommerce | ≥4 | ≥3 | ≥3 | ≥2 |
| general | ≥2 | ≥2 | — | — |
| internal-tools | — | — | — | — |

### V3: 兼容性 E2E (按 business_domain 矩阵检查)

| Domain | 浏览器 | 设备 |
|--------|--------|------|
| fintech | Chrome+FF+Safari | Desk+Tab+Mob |
| ecommerce | Chrome+FF+Safari | Desk+Tab+Mob |
| general | Chrome+FF | Desk+Mob |
| internal-tools | Chrome | Desk |

### V4: 数据自包含

- [ ] 每个 E2E 用例有独立的 GIVEN (数据准备) 和 CLEANUP (数据清理)
- [ ] 用例之间无隐式顺序依赖 (可并行执行)
- [ ] CLEANUP 恢复到测试前状态 (不留脏数据)
- [ ] GIVEN 中跨服务的数据分布明确 (哪个数据在哪个服务)

### V5: 自定义扩展

- [ ] 如果 `sw.e2e_extensions.custom_categories` 有定义，对应场景已填充
- [ ] 如果 `sw.e2e_extensions.priority_overrides` 有定义，优先级已生效

## 输出

```
PASS: → E2E 设计完成，进入设计门禁
FAIL: → 标记缺失项，回到 E2E 设计修订。最大重试 3 轮。
       3 轮后仍未 PASS → 升级到人工决策。
```
