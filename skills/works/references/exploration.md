# 代码库探索（无人化）

填 `requirement-contract.json` 和 `impact-map.json` 之前，在仓库里定位证据。这是内置 reference，不加载外部 Skill。

## 要定位什么

- **入口点**：`@Controller`/`@RestController`/`Job`/`Listener`/`Command`/`Handler` 等，需求从哪个入口进来。
- **调用链**：入口 → Service → Mapper/Repository 的完整路径。
- **本类方法与 Service API**：将要修改的类自身是否已有等价能力；只有本类没有时，再查同业务对象的同层 Service API。
- **持久层**：Mapper/DAO/Repository 类型与依赖声明。
- **测试 seam**：哪个类和方法承载本次新增行为、应创建哪个 Mockito 单元测试，以及哪些第三方或外部协作者必须 mock。

## 方法

1. 用 git / 文件搜索定位符号：类名、方法名、注解、`import` 依赖声明。
2. 顺调用链追踪：从入口的依赖字段、构造器、方法体向下走，直到数据层。对每个计划修改的类，先阅读本类全部已有方法及其调用方，记录能覆盖需求的复用候选；本类无候选时才向外查同层 Service，最后才查 Mapper/Repository。
3. 找测试 seam：把本次新增行为所在的 Controller/Service/API 边界记为 `boundary`，把要创建的 Mockito `src/test/java/` 文件记为 `planned_test`。只规划当前 Req 的 `Class#method`；列出要直接 mock 的第三方和外部协作者。参考现有同类测试的结构，但不要继承 `@SpringBootTest` 或存量行为断言，也不要把未创建的测试文件当作已存在证据。
4. 交叉验证：至少两种方式（如 grep + 读文件）确认一个结论，再写进 contract/impact-map。

## 无人化硬约束

- **只读**：不修改任何文件。
- **找不到就如实报告**：把「已穷尽搜索、确定不存在」写进 finding，不请求用户提供更多线索，不停在「待确认」状态。
- **证据落字段**：找到的文件证据（`路径:行号`）直接写进 impact-map 的 `entrypoints`/`service_apis`/`persistence`。`test_seams` 每项必须是 `{"boundary":"已存在文件:有效行号","planned_test":"<module>/src/test/java/...Test.java"}`；`planned_test` 可以尚不存在。
- **复用顺序**：当前类已有等价方法 > 同层 Service API > 新增或直接调用 Mapper/Repository。不得因为 Mapper 调用更直接就跳过前两级。

分层规则与「入口不得直接依赖持久层」的判定见 [Service boundary](service-boundary.md)。
