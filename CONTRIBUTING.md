# 贡献指南

本仓库以中文协作为主。路径、命令、代码标识符、版本号、文件名和 GitHub 专有名词可保留英文。

## 修改范围

- `cn-patent-*` 是核心专利工作流 skill，可以在明确任务范围内修改。
- `seaborn`、`scientific-visualization`、`scientific-schematics`、`matplotlib`、`markdown-mermaid-writing`、`generate-image` 是支撑型 vendored skill。除非任务明确要求，默认只随仓库托管和检查，不主动改造行为。

## 日常开发

可以直接修改：

```text
C:\Users\spade k\.codex\skills\<skill-name>
```

这些目录是 junction，真实文件在：

```text
C:\Users\spade k\patents-workflow\skills\<skill-name>
```

## 提交前检查

```bash
python scripts/check-release.py
python scripts/check-live-links.py
```

## 版本规则

- `1.6.x`：修复、文档、兼容性调整。
- `1.7.0`：新增能力或调整工作流契约。
- `2.0.0`：破坏性变化。
