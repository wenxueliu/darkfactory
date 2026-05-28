"""Shared fixtures for KB script tests."""

import os
import pytest
import tempfile


@pytest.fixture
def tmp_kb(tmp_path):
    """Create a temporary knowledge-base directory with empty category subdirs and a skeleton index.md."""
    kb_base = tmp_path / "knowledge-base"
    for subdir in ["patterns", "decisions", "lessons", "api-contracts", "services"]:
        (kb_base / subdir).mkdir(parents=True)

    index_content = """# 知识库索引

## 概述

测试用知识库索引。

## 目录结构

```
knowledge-base/
├── index.md          # 本索引文件
├── patterns/         # 可复用的设计模式
├── decisions/        # 架构决策记录 (ADR)
├── lessons/          # 经验教训
└── api-contracts/    # API文档
```

## Patterns

## Architecture Decisions

## Lessons Learned

## API Contracts

## Service Knowledge

## 更新记录

| 日期 | 更新内容 | 更新人 |
|------|----------|--------|
"""
    (kb_base / "index.md").write_text(index_content)
    return kb_base


@pytest.fixture
def project_root(tmp_path):
    """Create a full project skeleton with _context/memory/sw-shared/knowledge-base/."""
    multiagents = tmp_path / "multiagents"
    scripts_dir = multiagents / "scripts"
    scripts_dir.mkdir(parents=True)

    kb_base = multiagents / "_context" / "memory" / "sw-shared" / "knowledge-base"
    for subdir in ["patterns", "decisions", "lessons", "api-contracts", "services"]:
        (kb_base / subdir).mkdir(parents=True)

    index_content = """# 知识库索引

## 概述

测试用知识库索引。

## Patterns

## Architecture Decisions

## Lessons Learned

## API Contracts

## Service Knowledge

## 更新记录

| 日期 | 更新内容 | 更新人 |
|------|----------|--------|
"""
    (kb_base / "index.md").write_text(index_content)
    return multiagents
