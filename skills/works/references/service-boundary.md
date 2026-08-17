# Service boundary

## Default dependency direction

```text
Controller / Job / Listener / Command handler
                    ↓
          Service / Application Service
                    ↓
          Mapper / DAO / Repository
                    ↓
                 Database
```

上层入口表达传输或触发机制；Service/Application Service 表达用例、事务和跨组件编排；Mapper/DAO/Repository 封装持久化。现有项目的命名可能不同，应按职责和调用图识别，不能只匹配 `*Service` 后缀。

## Decision table

| 场景 | 允许的依赖 |
|---|---|
| Controller、RPC endpoint、Job、Listener 发起业务用例 | 调用 Service；不直接调用 Mapper/Repository |
| 一个写操作涉及校验、状态变化、权限、多个 Mapper 或事件 | Service 作为事务/用例边界 |
| Service 内部完成单表查询或持久化 | 可以调用 Mapper/Repository |
| 同领域已有 Service API | 优先复用；不要绕过后复制逻辑 |
| 缺少所需业务能力 | 扩展职责匹配的 Service API，再由 Service 调数据层 |
| CQRS 独立只读 Query handler | 仅在项目已有明确模式、无领域规则且有测试时可直接使用只读数据访问 |
| Spring Data REST 直接资源暴露 | 仅沿用项目明确采用且不绕过已有 Service、领域不变量、授权、审计、事件或事务编排的资源模型；不推广到普通 Controller 或新业务写路径 |
| Mapper/Repository 实现或切片测试 | 可以直接测试持久化职责，但不能据此代替 Service 行为测试 |
| 迁移/基础设施批处理 | 仅沿用项目已有同类边界；涉及业务规则或副作用编排时仍进入 Service/Application boundary |

## Why

- Spring 把 Controller、Service 和 Repository 定义为不同语义的 stereotype，并强调清晰分层及业务/服务层与数据访问层的交互。
- Spring Data JPA 建议在涉及多个 repository 或非 CRUD 用例时使用 facade/service 定义事务边界。
- DDD 实践将 Application Service 定位为用例编排者，将 Repository 定位为持久化抽象；写入和领域不变量不应由表示层直接操作数据层。

## Inspection procedure

1. 从需求入口查依赖字段、构造器和调用图。
2. 搜索同一业务对象的 Service 接口、实现和现有调用方。
3. 搜索 Service 是否已经包装目标 Mapper 方法、事务、权限、缓存、事件或状态校验。
4. 对比计划 diff：如果入口新增 Mapper 依赖，而 Service 没有相应变化，视为高概率绕层。
5. 为 Service 公共行为写测试；必要时另写 Mapper 集成测试，但不能只测 Mapper 就宣称业务功能完成。
6. 项目使用 ArchUnit 或 Spring Modulith 时，运行现有架构测试；按项目惯例补充“入口包不得依赖 mapper/repository”“跨模块只能依赖 API/service 包”等规则。
7. 即使项目没有 ArchUnit，也必须先运行 `scripts/service_boundary.py init` 保存 dirty baseline，随后用 `verify` 阻断新增入口→持久层依赖。它同时识别后缀、Spring `@Repository`、MyBatis `@Mapper`/`BaseMapper` 和常见直接数据访问客户端。

## Sources

- Spring Framework, Data Access: https://docs.spring.io/spring/reference/data-access.html
- Spring Framework, ORM layering: https://docs.spring.io/spring-framework/reference/data-access/orm/general.html
- Spring Data JPA, transactionality and service facade: https://docs.spring.io/spring-data/jpa/reference/jpa/transactions.html
- Spring `@Repository` semantics: https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/stereotype/Repository.html
- Microsoft DDD persistence-layer guidance: https://learn.microsoft.com/en-us/dotnet/architecture/microservices/microservice-ddd-cqrs-patterns/infrastructure-persistence-layer-design
- Azure tactical DDD, application services: https://learn.microsoft.com/en-ca/azure/architecture/microservices/model/tactical-ddd
- Spring Modulith, module verification: https://docs.spring.io/spring-modulith/reference/verification.html
- Oracle Java EE, service/session facade patterns: https://docs.oracle.com/javaee/6/tutorial/doc/gipjg.html

Spring 并未规定所有 Controller 在任何系统中都绝不能直接使用 Repository；这是本 skill 面向既有分层项目采用的保守架构契约。若仓库已有 CQRS/资源暴露例外，应以现有测试和架构证据识别，不能仅凭模型判断绕过门禁。
