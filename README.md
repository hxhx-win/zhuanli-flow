# patents-workflow

`patents-workflow` 是面向中文发明专利工作的 Agent Skill 套件，包含确定性领域 Runtime、主线分析、现有技术检索、技术交底、正式稿起草、代理师审稿和 DOCX 导出能力。

当前版本：`2.1.0`

## 获取发行包

普通用户请从 [GitHub Releases](https://github.com/hxhx-win/patents-workflow/releases) 下载：

```text
patents-workflow-v2.1.0-full.zip
patents-workflow-v2.1.0-full.zip.sha256
```

命名的完整发行包包含 9 个核心专利 Skill、6 个绘图支撑 Skill、安装器和全部许可证材料。GitHub 自动生成的 Source code 压缩包是贡献者源码，不是面向用户整理的安装包。

下载后先核对 SHA-256，再解压并进入 `patents-workflow-2.1.0/` 目录。

## 安装

安装器默认面向 Codex 的 `~/.codex/skills`。不加 `--apply` 时只预览：

```bash
python scripts/install-skills.py install
python scripts/install-skills.py install --apply
```

安装到 Claude Code：

```bash
python scripts/install-skills.py install --agent claude
python scripts/install-skills.py install --agent claude --apply
```

安装到其他 Agent Skills 目录：

```bash
python scripts/install-skills.py install --target-root "<path-to-skills>"
python scripts/install-skills.py install --target-root "<path-to-skills>" --apply
```

目标中已有真实 Skill 目录时，安装器默认拒绝覆盖。确认直接更新且不保留持久备份后，显式添加：

```bash
python scripts/install-skills.py install --apply --overwrite
```

安装器始终拒绝覆盖 symlink、junction 或其他 reparse point；开发仓库的 live-link 工作流参见 `CONTRIBUTING.md`。

## 校验与卸载

校验安装收据、版本、文件集合和内容哈希：

```bash
python scripts/install-skills.py verify
python scripts/install-skills.py verify --agent claude
```

卸载默认只预览，添加 `--apply` 后才执行：

```bash
python scripts/install-skills.py uninstall
python scripts/install-skills.py uninstall --apply
```

如果已安装 Skill 有任何修改、增删文件或哈希变化，安装器会整体拒绝自动卸载，以免删除用户内容。

校验或卸载时应使用与已安装版本相同的发行包；升级安装成功后会生成新版本收据。

## Skill 范围

核心专利工作流 Skill：

- `cn-patent-repo-scout`
- `cn-patent-mainline-analysis`
- `cn-patent-prior-art-search`
- `cn-patent-disclosure-draft`
- `cn-patent-disclosure-review`
- `cn-patent-formal-drafting`
- `cn-patent-attorney-review`
- `cn-patent-docx-export`
- `cn-patent-domain-runtime`

支撑型 vendored Skill：

- `seaborn`
- `scientific-visualization`
- `scientific-schematics`
- `matplotlib`
- `markdown-mermaid-writing`
- `generate-image`

## 许可证

本项目自有内容采用 [MIT License](LICENSE)。第三方 Skill 的来源、目录摘要和许可证见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 与 `third_party/`。

## 参与开发

源码开发、live link、提交前检查和版本发布流程见 [CONTRIBUTING.md](CONTRIBUTING.md)。
