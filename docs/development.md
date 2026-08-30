# 开发说明

## 仓库定位

`patents-workflow` 源码仓库是 15 个声明 Skill 的真实文件位置。live link 仅用于贡献者开发；普通用户应使用 GitHub Release 完整包和 `scripts/install-skills.py`。

Codex 首次 clone 后运行：

```bash
python scripts/dev/link-live-skills.py --agent codex --apply
python scripts/dev/check-live-links.py --agent codex
```

Claude Code 首次 clone 后运行：

```bash
python scripts/dev/link-live-skills.py --agent claude --apply
python scripts/dev/check-live-links.py --agent claude
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
python -B scripts/check-release.py
python -B -m unittest discover -s tests -v
python -B scripts/build-release.py
python -B scripts/dev/check-live-links.py --agent codex
```

## 版本迭代

仓库名保持 `patents-workflow` 不变。版本通过 `VERSION`、`manifest.json`、`CHANGELOG.md`、git tag 和 GitHub Release 管理。
