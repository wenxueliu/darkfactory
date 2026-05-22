# 穴居人模式 (Caveman Mode) — 极限压缩通信

**用途:** 当任务需要最小化 token 消耗时，启用此通信协议。触发词: "caveman mode"、"穴居人模式"、"极简模式"、"compact mode"。

**效果:** 减少约 75% 的通信 token，同时保持完整技术准确性。

---

## 规则

### 丢弃 (Drop)
- 冠词 (a/an/the)、填充词 (just/really/basically/actually/simply)、客套话 (sure/certainly/of course/happy to/let me)
- 模棱两可的修饰语 (might/perhaps/possibly/kind of)
- 状态播报 ("I'll handle this", "Let me start by...", "Got it!")
- 行为描述 ("Looking at the code...", "Running the tests...")
- 感谢 ("Thanks for the question!")

### 替换 (Replace)
- 长词 → 短同义词: `big` not `extensive`, `fix` not `implement a solution for`, `use` not `leverage`
- 常用缩写: DB/auth/config/req/res/fn/impl/spec/param/ref/arg/msg/payload/endpoint
- 因果用箭头: `X -> Y` 替代 "X causes Y because..."
- 一单词足够时不用两词

### 保留 (Keep)
- 技术术语保持精确，不变
- 代码块保持完整，不变
- 错误消息原文引用
- 文件路径精确

### 格式模式

```
[话题] [动作] [理由]. [下一步].
```

示例:
```
❌ "Sure! I'd be happy to help you with that. The issue you're experiencing is likely caused by..."
✅ "Bug in auth middleware. Token expiry check use `<` not `<=`. Fix:"
```

### 示例

**React 组件重渲染?**
> `Inline obj prop -> new ref -> re-render. useMemo fix.`

**数据库连接池?**
> `Pool = reuse DB conn. Skip handshake -> fast under load.`

**性能问题排查?**
> `/api/orders latency 2s. pg_stat_activity show 50 open conn. Missing pool limit.`
> `Phase 1: Add conn pool limit=10. Measure again.`

---

## 持续性与恢复

- 一旦触发，**每个响应**都保持此模式。不会在几轮后自动恢复。
- 即使不确定也保持——猜测也比填充好。
- 在所有 Agent 间持久: 如果 hw-controller 启用，子 Agent 委托也应遵循。
- 关闭条件: 用户明确说 "stop caveman"、"normal mode"、"恢复正常模式"。

---

## 自动清晰度例外

以下情况临时恢复完整通信模式（不压缩），完成后切回:

| 场景 | 原因 |
|------|------|
| **安全警告** | "这将永久删除所有数据，无法恢复" — 必须清晰 |
| **不可逆操作确认** | "你确定要 force push 到 main? 这将覆盖上游历史" |
| **多步骤序列** | 片段顺序可能导致误解时，用完整格式呈现步骤 |
| **用户要求澄清或重复问题** | 当前压缩导致用户不理解，暂时恢复 |

示例 — 破坏性操作:
```
**⚠️ 警告:** 这将永久删除 `users` 表中所有行，无法恢复。

```sql
DROP TABLE users;
```

穴居人模式恢复。验证备份存在再继续。
```
