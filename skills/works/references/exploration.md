# 代码库探索（无人化）

填 `requirement-contract.json` 和 `impact-map.json` 之前，在仓库里定位证据。这是内置 reference，不加载外部 Skill。

## 要定位什么

- **入口点**：`@Controller`/`@RestController`/`Job`/`Listener`/`Command`/`Handler` 等，需求从哪个入口进来。
- **调用链**：入口 → Service → Mapper/Repository 的完整路径。
- **Service API**：同业务对象已有哪些可复用的 Service 方法（优先复用，不绕过）。
- **持久层**：Mapper/DAO/Repository 类型与依赖声明。
- **测试 seam**：哪个已存在的公共行为边界应被测试，以及 Red 阶段要创建的 Maven 测试文件路径。

## 方法

1. 用 git / 文件搜索定位符号：类名、方法名、注解、`import` 依赖声明。
2. 顺调用链追踪：从入口的依赖字段、构造器、方法体向下走，直到数据层。
3. 找测试 seam：把已存在的 Controller/Service/API 公共边界记为 `boundary`，把 Red 阶段要创建的 `src/test/java/` 文件记为 `planned_test`。参考现有同类测试的结构和断言，但不要把未创建的测试文件当作已存在证据。
4. 交叉验证：至少两种方式（如 grep + 读文件）确认一个结论，再写进 contract/impact-map。

## 无人化硬约束

- **只读**：不修改任何文件。
- **找不到就如实报告**：把「已穷尽搜索、确定不存在」写进 finding，不请求用户提供更多线索，不停在「待确认」状态。
- **证据落字段**：找到的文件证据（`路径:行号`）直接写进 impact-map 的 `entrypoints`/`service_apis`/`persistence`。`test_seams` 每项必须是 `{"boundary":"已存在文件:有效行号","planned_test":"<module>/src/test/java/...Test.java"}`；`planned_test` 可以尚不存在。

分层规则与「入口不得直接依赖持久层」的判定见 [Service boundary](service-boundary.md)。
