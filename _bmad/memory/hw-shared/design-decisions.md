# 架构决策记录索引 (ADR Index)

ADRs are managed by `kb-log.py decision` — do NOT write ADR content directly in this file.
Create ADRs with the script and they will be auto-linked in `knowledge-base/decisions/`.

## 设计需求与 ADR 对照

| 设计需求 | ADR 列表 | 状态 |
|---------|---------|------|
| (尚无) | (尚无) | — |

## 查询

```bash
# 列出所有 ADR
python scripts/kb-search.py --type decision --json

# 按关键词查找
python scripts/kb-search.py "{关键词}" --type decision --max-results 10
```

## 更新方式

每次设计阶段完成后，hw-controller 将新创建的 ADR 追加到上方对照表中。
