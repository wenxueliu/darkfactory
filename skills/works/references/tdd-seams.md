# TDD seam 与测试质量（无人化）

`READY_FOR_RED` 选公共行为 seam 写测试，`READY_FOR_IMPLEMENTATION` 最小实现。这是内置 reference，不加载外部 `tdd` Skill。

## Seam 已由契约确定

Seam（测试所在的公共边界）**已由 `requirement-contract.json` 和 `impact-map.json` 的 `test_seams` 决定**，不再向用户确认。每项的 `boundary` 是已存在的公共行为边界，`planned_test` 是 Red 阶段要新建或复用的 Maven 测试文件。若 impact-map 缺 test_seams，按 [exploration](exploration.md) 补全后继续。

## 好测试

- 测**公共接口行为**，不测实现细节；实现可以整体重写，测试不该变。
- 期望值来自**独立真值**（已知字面量、手工算例、规格），不是用被测代码同款逻辑重算。
- 测试触及数据库、消息队列、对象存储、第三方 API 等外部依赖时，直接在边界处 mock；不连接真实外部服务，不要求本地或 CI 预先启动基础设施。
- 一个 Req 一次 Red→Green，**纵向切片**：一次一个 test → 一次一个最小实现，不批量写全部测试。
- 在 `planned_test` 指定的路径创建或复用测试类，通过 `boundary` 指定的公共边界驱动行为；不要因为 `planned_test` 在 impact-check 时尚不存在而更换 seam。

## 反模式（拒绝）

- **implementation-coupled**：mock 内部协作者、测私有方法、或绕接口查库验证。
- **tautological**：断言用与实现相同的方式重算期望值，天然恒真。
- **horizontal slicing**：先写全部测试再写全部实现，测的是臆想结构而非用户行为。

## 无人化硬约束

- 不引用 `codebase-design` / `code-review`（works 无这些 Skill）。
- 不向用户确认 seam；Red 的有效性由 `red` 门禁（真实断言失败、无编译/fixture 错误）判定，见 [TDD evidence](tdd-evidence.md)。
