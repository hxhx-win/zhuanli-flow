# Third-Party Notices

`patents-workflow` 自有内容使用仓库根目录的 MIT License。`skills/` 下列目录来源于第三方开源项目，并保留各自声明的许可证。

历史导入时未记录精确的上游 commit。为避免给出无法证明的版本信息，`third_party/provenance.json` 将 `source_revision` 明确记为 `null`，并使用当前仓库中每个 vendored Skill 的确定性目录树 SHA-256 标识实际分发内容。

## K-Dense Scientific Agent Skills

来源：

- 历史仓库：https://github.com/K-Dense-AI/claude-scientific-skills
- 当前仓库：https://github.com/K-Dense-AI/scientific-agent-skills
- 作者：K-Dense Inc.

包含：

- `generate-image` — MIT
- `scientific-schematics` — MIT
- `scientific-visualization` — MIT
- `seaborn` — Skill frontmatter 声明 BSD-3-Clause
- `matplotlib` — Skill frontmatter 指向 Matplotlib License

随发行包附带：

- `third_party/licenses/K-Dense-MIT.txt`
- `third_party/licenses/Seaborn-BSD-3-Clause.txt`
- `third_party/licenses/Matplotlib.txt`

`seaborn` 和 `matplotlib` 的许可证文件按其 Skill frontmatter 一并保留；本仓库不打包相应 Python 库本身。

## Markdown and Mermaid Writing

- 目录：`markdown-mermaid-writing`
- 来源：https://github.com/SuperiorByteWorks-LLC/agent-project
- 作者：Clayton Young / Superior Byte Works, LLC
- 许可证：Apache License 2.0
- 许可证文件：`third_party/licenses/SuperiorByteWorks-Apache-2.0.txt`

原 Skill 和相关模板、参考资料中的作者、来源和许可证注释均予以保留。
