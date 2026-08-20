# 代码库探索（无人化）

填 `requirement-contract.json` 之前，在仓库里定位实现证据。这是内置 reference，不加载外部 Skill。

## 要定位什么

- **入口点**：`@Controller`/`@RestController`/`Job`/`Listener`/`Command`/`Handler` 等，需求从哪个入口进来。
- **调用链**：入口 → Service → Mapper/Repository 的完整路径。
- **本类方法与 Service API**：将要修改的类自身是否已有等价能力；只有本类没有时，再查同业务对象的同层 Service API。
- **持久层**：Mapper/DAO/Repository 类型与依赖声明。
- **测试 seam**：哪个类和方法承载本次新增行为、应创建哪个快速测试，以及哪些第三方或外部协作者必须隔离。

## 方法

1. 用 git / 文件搜索定位符号：类名、方法名、注解、`import` 依赖声明。
2. 顺调用链追踪：从入口的依赖字段、构造器、方法体向下走，直到数据层。对每个计划修改的类，先阅读本类全部已有方法及其调用方，记录能覆盖需求的复用候选；本类无候选时才向外查同层 Service，最后才查 Mapper/Repository。
3. 找测试 seam：记录行为边界和计划测试文件。存在协作者时使用 Mockito 或项目已有 fake；纯逻辑使用普通 JUnit。不要继承无必要的 `@SpringBootTest` 或存量行为断言。
4. 只对高风险或不确定结论做第二来源验证；读源码已经明确的普通事实无需机械重复搜索。

## 无人化硬约束

- **只读**：不修改任何文件。
- **找不到就如实报告**：把「已穷尽搜索、确定不存在」写进 finding，不请求用户提供更多线索，不停在「待确认」状态。
- **证据落字段**：把入口写入 contract 的 `implementation.entrypoint`，复用目标写入 `implementation.reuse`，计划测试写入 `implementation.test_target`。源码目标使用项目相对 `path + symbol`；测试文件可以尚不存在。
- **复用顺序**：当前类已有等价方法 > 同层 Service API > 新增或直接调用 Mapper/Repository。不得因为 Mapper 调用更直接就跳过前两级。
- **冻结决策**：每个 Req 必须填写 `implementation.reuse`。选择 `persistence` 时，`absence_evidence` 分别记录 `current_class` 和 `same_layer_service` 的搜索范围与缺失理由；其他 kind 必须为空。

分层规则与「入口不得直接依赖持久层」的判定见 [Service boundary](service-boundary.md)。
