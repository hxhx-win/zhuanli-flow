# 贡献指南

本仓库以中文协作为主。路径、命令、代码标识符、版本号、文件名和 GitHub 专有名词可保留英文。

## 修改范围

- `cn-patent-*` 是核心专利工作流 Skill，可以在明确任务范围内修改。
- `seaborn`、`scientific-visualization`、`scientific-schematics`、`matplotlib`、`markdown-mermaid-writing`、`generate-image` 是支撑型 vendored Skill。除非任务明确要求，默认只随仓库托管和检查，不主动改造行为。
- 修改 vendored Skill 后必须同步更新 `third_party/provenance.json` 中对应的目录树 SHA-256，并确认许可证和来源记录仍然准确。

## 开发者 live link

live link 只用于源码开发，不是用户安装方式。脚本位于 `scripts/dev/`，支持 Codex 和 Claude Code：

```text
~/.codex/skills/<skill-name>
  -> <repo>/skills/<skill-name>

~/.claude/skills/<skill-name>
  -> <repo>/skills/<skill-name>
```

Codex：

```bash
python scripts/dev/link-live-skills.py --agent codex
python scripts/dev/link-live-skills.py --agent codex --apply
python scripts/dev/check-live-links.py --agent codex
```

Claude Code：

```bash
python scripts/dev/link-live-skills.py --agent claude
python scripts/dev/link-live-skills.py --agent claude --apply
python scripts/dev/check-live-links.py --agent claude
```

也可指定测试用 live 根目录：

```bash
python scripts/dev/link-live-skills.py --live-root "<path-to-skills>" --apply
python scripts/dev/check-live-links.py --live-root "<path-to-skills>"
```

在 Windows 上脚本创建 junction，在其他平台创建 symlink。已有真实目录会先移动到带时间戳的备份目录；已有链接只按脚本中的安全规则处理。

## 提交前检查

```bash
python -B scripts/check-release.py
python -B -m unittest discover -s tests -v
python -B scripts/build-release.py
python -B scripts/dev/check-live-links.py --agent codex
```

前三项与机器的 live-link 状态无关；最后一项仅用于已配置 live link 的开发环境。

## 版本与发布

- 修复使用补丁版本。
- 向后兼容的新能力使用次版本。
- 破坏性 Skill 或状态契约变化使用主版本。

`VERSION`、`manifest.json`、README 和 CHANGELOG 必须保持一致。推送 `v<VERSION>` tag 后，GitHub Actions 会重新检查并生成命名的完整 ZIP 和 SHA-256；不要把 GitHub 自动生成的 Source code 压缩包当作用户发行包。

Git commit 必须使用中文描述。
