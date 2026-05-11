# 委托提示结构 (Delegation Prompt Structure)

参考: Sisyphus orchestrator DNA — oh-my-openagent 的委托 prompt 模板

## 核心理念

委托的质量 = 委托 prompt 的质量。一个模糊的委托 prompt 会产生模糊的结果，需要多轮返工。6 段式委托模板确保每个委托都是**完整、精确、可验证**的。

**原则:** 宁可多花 2 分钟写好委托 prompt，也不要花 20 分钟矫正子 Agent 的偏差。

## 6 段式委托模板

每个委托 MUST 包含以下 6 个段：

```
1. TASK         — 精确的任务描述
2. EXPECTED OUTCOME — "done" 是什么样子，验收标准
3. REQUIRED TOOLS   — worker 需要什么工具/权限
4. MUST DO      — 不可协商的要求
5. MUST NOT DO  — 禁止的行为
6. CONTEXT      — 相关代码位置、模式、决策
```

### 段 1: TASK — 精确的任务描述

**要求:** 1-3 句话，精确描述要做什么。包含具体的目标文件/模块/端点。

```
✅ 正确:
TASK: 在 UserService.java 中实现 createUser(UserDto dto) 方法。
      方法接收 UserDto，验证字段，调用 UserRepository.save()，返回 User 实体。

❌ 错误:
TASK: 实现用户创建功能
→ 太模糊！哪个文件？什么方法？什么逻辑？
```

### 段 2: EXPECTED OUTCOME — 验收标准

**要求:** 可测量的 "done" 定义。包含具体的输出和通过条件。

```
✅ 正确:
EXPECTED OUTCOME:
  - UserService.createUser() 方法存在且通过编译
  - UT (UserServiceTest): 3 个测试用例 PASS
    - testCreateUser_validInput: 正常输入 → 返回 User
    - testCreateUser_duplicateEmail: 重复 email → 抛 DuplicateUserException
    - testCreateUser_invalidEmail: 无效 email 格式 → 抛 ValidationException
  - API 测试: POST /api/users 返回 201 + User JSON
  - 代码覆盖率 ≥ 85%

❌ 错误:
EXPECTED OUTCOME: 功能正常工作
→ 无法验证！什么算 "正常"？什么测试？
```

### 段 3: REQUIRED TOOLS — 所需工具

**要求:** 列出子 Agent 执行任务所需的工具/权限/环境。

```
✅ 正确:
REQUIRED TOOLS:
  - Java 17 编译环境
  - JUnit 5 + Mockito
  - 项目的 build.gradle
  - Newman (API 测试)
  - 访问 src/main/java/com/example/user/ 目录

❌ 错误:
REQUIRED TOOLS: 开发环境
→ 太模糊！什么语言？什么框架？什么版本？
```

### 段 4: MUST DO — 不可协商的要求

**要求:** 列出子 Agent 必须遵守的规则和必须执行的步骤。

```
✅ 正确:
MUST DO:
  - 遵循 TDD 铁律: 先写失败的测试，再写生产代码
  - RED → GREEN → REFACTOR 三轮
  - UserDto 使用 Jakarta Validation annotations (非 Spring)
  - 密码必须 BCrypt 哈希 (使用项目中已有的 PasswordEncoder)
  - 方法必须包含 JavaDoc
  - 测试数据必须使用具体值，不能用占位符

❌ 错误:
MUST DO: 写干净代码
→ 太主观！什么算 "干净"？
```

### 段 5: MUST NOT DO — 禁止的行为

**要求:** 明确列出子 Agent 绝对不能做的事。

```
✅ 正确:
MUST NOT DO:
  - 不要修改 UserRepository 接口（已存在且稳定）
  - 不要在 Controller 层写业务逻辑
  - 不要引入新的依赖库（保持零外部依赖原则）
  - 不要使用 @Autowired 字段注入（项目使用构造器注入）
  - 不要删除或 skip 任何已有的测试

❌ 错误:
(无此段)
→ 子 Agent 可能做任何 "合理" 的事，但这些事可能违反项目约束
```

### 段 6: CONTEXT — 相关上下文

**要求:** 提供子 Agent 理解任务所需的背景信息。

```
✅ 正确:
CONTEXT:
  - UserRepository 位于 src/main/java/com/example/user/UserRepository.java
    已有方法: findById(), findByEmail(), save(), delete()
  - 项目中已存在 PasswordEncoder Bean (config/SecurityConfig.java)
  - UserDto 定义在 src/main/java/com/example/user/dto/UserDto.java
    字段: email, password, name, phone (email 和 password 必填)
  - 错误处理模式: 项目统一使用 GlobalExceptionHandler 捕获自定义异常
  - 现有 UserService 只有 getUser() 方法，createUser() 是新增的
  - 参考同级 OrderService.createOrder() 的实现模式

❌ 错误:
CONTEXT: 项目是 Spring Boot
→ 信息不足！子 Agent 需要自己去发现上面所有信息
```

## 完整示例

### 示例 1: 后端任务 (Java Spring Boot)

```
TASK:
  在 OrderService.java 中实现 createOrder(CreateOrderRequest req) 方法。
  方法接收 CreateOrderRequest，检查库存（调用 InventoryClient），
  计算总价，调用 OrderRepository.save()，返回 OrderResponse。

EXPECTED OUTCOME:
  - OrderService.createOrder() 编译通过
  - UT: 5 个测试用例 PASS
    1. createOrder_success: 正常下单 → 返回 OrderResponse
    2. createOrder_insufficientStock: 库存不足 → 抛 InsufficientStockException
    3. createOrder_invalidProduct: 商品不存在 → 抛 ProductNotFoundException
    4. createOrder_emptyCart: 空购物车 → 抛 EmptyCartException
    5. createOrder_priceCalculation: 验证总价计算正确（含折扣）
  - API 测试: POST /api/orders 返回 201 + OrderResponse JSON
  - 覆盖率 ≥ 85%

REQUIRED TOOLS:
  - Java 17, Gradle
  - JUnit 5 + Mockito + AssertJ
  - 项目的 build.gradle
  - Newman (API 测试)

MUST DO:
  - TDD: RED → GREEN → REFACTOR 三轮
  - 使用构造器注入（非 @Autowired）
  - 使用 FeignClient 调用 InventoryClient（非 RestTemplate）
  - 订单状态初始值为 PENDING_PAYMENT
  - 价格计算使用项目中的 PriceCalculator 工具类
  - 所有异常继承项目已有的 BusinessException
  - 测试数据使用具体的 SKU/价格值，不用占位符

MUST NOT DO:
  - 不要修改 InventoryClient 接口定义
  - 不要在 OrderService 中直接操作数据库（只通过 OrderRepository）
  - 不要硬编码价格或折扣率
  - 不要使用 @Transactional(readOnly = true) 在写方法上
  - 不要删除已有的 orderServiceTest.java 中的测试

CONTEXT:
  - OrderRepository: src/main/java/com/example/order/OrderRepository.java
    方法: save(), findById(), findByUserId()
  - InventoryClient: src/main/java/com/example/inventory/InventoryClient.java
    方法: checkStock(sku, quantity) → StockResponse
  - CreateOrderRequest: src/main/java/com/example/order/dto/CreateOrderRequest.java
    字段: userId, items(List<OrderItem>), couponCode(optional)
  - PriceCalculator: src/main/java/com/example/common/PriceCalculator.java
    方法: calculateTotal(List<OrderItem>) → BigDecimal
  - BusinessException: src/main/java/com/example/common/BusinessException.java
    派生类: InsufficientStockException, ProductNotFoundException, EmptyCartException
  - 参考: PaymentService.createPayment() 的实现模式（注入、异常处理、日志）
  - application.yml 中 order.service.discount-strategy: "tiered"
```

### 示例 2: 前端任务 (React + TypeScript)

```
TASK:
  在 src/components/checkout/CheckoutForm.tsx 中实现结账表单组件。
  包含: 收货地址表单、支付方式选择、订单摘要、提交按钮。
  使用 React Hook Form + Zod 验证。

EXPECTED OUTCOME:
  - CheckoutForm 组件渲染正确
  - UT: 4 个测试用例 PASS
    1. renders all form sections: 地址/支付/摘要/按钮全部渲染
    2. validates required fields: 必填项为空时显示错误提示
    3. submits valid form: 表单提交后调用 onSubmit prop
    4. disables submit while loading: 提交中按钮 disabled
  - 无 TypeScript 错误
  - 无 ESLint warnings

REQUIRED TOOLS:
  - Node 20, pnpm
  - React 18, TypeScript 5
  - React Hook Form + Zod
  - Jest + React Testing Library
  - 访问 src/components/checkout/ 目录

MUST DO:
  - 使用项目中的 useAddressAutocomplete hook
  - 支付方式从 config/payment-methods.ts 读取（非硬编码）
  - 表单 loading 状态使用 useTransition (React 18)
  - 所有文本使用 i18n (useTranslation hook)
  - Zod schema 抽取到 src/schemas/checkout.ts
  - 遵循项目 Container/Presentational 分离
  - 测试每个表单项的必填验证

MUST NOT DO:
  - 不要直接 fetch API（使用项目中的 useApi hook）
  - 不要导入 antd 组件（项目使用 Tailwind + Headless UI）
  - 不要硬编码路由路径（使用项目 ROUTES 常量）
  - 不要修改 CartSummary 组件（已存在，直接导入使用）
  - 不要在组件内定义 Zod schema

CONTEXT:
  - 项目组件模式: Container (逻辑) + Presentational (UI)
  - useAddressAutocomplete: src/hooks/useAddressAutocomplete.ts
  - useApi: src/hooks/useApi.ts (封装了 fetch + error handling)
  - ROUTES: src/constants/routes.ts
  - CartSummary: src/components/cart/CartSummary.tsx
  - payment-methods: src/config/payment-methods.ts
  - 参考: src/components/profile/ProfileForm.tsx 的表单实现模式
  - Tailwind 主题在 tailwind.config.ts 中定义
```

## 委托前 vs 委托后: 对比

### 太短 (会导致返工)

```
❌ 太短:
"在 UserService 加个 createUser 方法"

→ 子 Agent 会做什么？
  - 可能用 @Autowired（但项目用构造器注入）
  - 可能不写测试（没有明确要求）
  - 可能返回 UserDto 而不是 User 实体（风格不一致）
  - 可能硬编码密码哈希（但项目已有 PasswordEncoder）
  → 结果: 3 轮返工修正

✅ 完整:
[6 段式模板，如上例]
→ 子 Agent 返回的代码：
  - 使用构造器注入 ✅
  - 所有测试 PASS ✅
  - 返回类型一致 ✅
  - 使用现有 PasswordEncoder ✅
  → 结果: 0 轮返工
```

## 委托 Prompt 质量检查清单

在发送委托之前，检查以下项：

- [ ] TASK 段: 如果子 Agent 只看这段，能知道要做什么吗？（目标文件 + 具体操作）
- [ ] EXPECTED OUTCOME 段: 所有验收标准都可以客观测量吗？（不是 "看起来好"）
- [ ] REQUIRED TOOLS 段: 子 Agent 缺少任何工具时能否立即发现？
- [ ] MUST DO 段: 遗漏了任何项目约定吗？（检查: 注入方式、命名规范、异常类型、测试数据要求）
- [ ] MUST NOT DO 段: 子 Agent 可能 "合理但错误" 地做的操作都列出来了吗？
- [ ] CONTEXT 段: 子 Agent 不需要自己去探索任何已经在 prompt 中的信息？
- [ ] 所有 6 段都存在？（不跳过任何一段）
- [ ] 委托中的引用路径都真实存在？
- [ ] 委托中的模式参考文件确实遵循你要求子 Agent 遵循的模式？
- [ ] 有不必要的重复吗？（同一件事同时在 MUST DO 和 EXPECTED OUTCOME 说了）

## 与子 Agent 约定的关系

此 6 段式模板是总控与所有子 Agent 的通信约定。每个子 Agent 的 SKILL.md 中的 "On Activation" 段应包含对应的解析逻辑。这是跨 Agent 通信协议的核心。

总控负责输出 6 段式 prompt。子 Agent 负责遵守 MUST DO / MUST NOT DO 规则。总控在接收结果时负责验证（见 completion-gate.md）。
```
