# 开发说明

## 仓库定位

`patents-workflow` 是开发仓库，也是 15 个声明 skill 的真实文件位置。Codex 和 Claude Code 实际扫描的 live skill 目录会通过本机 live link 指向当前 clone 的 `skills/<skill-name>`。

Codex 首次 clone 后运行：

```bash
python scripts/link-live-skills.py --agent codex --apply
python scripts/check-live-links.py --agent codex
```

Claude Code 首次 clone 后运行：

```bash
python scripts/link-live-skills.py --agent claude --apply
python scripts/check-live-links.py --agent claude
```

默认 live root：

- Codex: `~/.codex/skills`
- Claude Code: `~/.claude/skills`

需要自定义位置时传入 `--live-root`。

## 日常修改

可以直接修改：

```text
~/.codex/skills/<skill-name>
~/.claude/skills/<skill-name>
```

由于该目录指向仓库中的 skill 目录，Git 会在仓库中看到对应改动：

```bash
git status --short
git diff
```

## 本地检查

```bash
python scripts/check-release.py
python scripts/check-live-links.py
```

## 版本迭代

仓库名保持 `patents-workflow` 不变。版本通过 `VERSION`、`manifest.json`、`CHANGELOG.md`、git tag 和 GitHub Release 管理。
