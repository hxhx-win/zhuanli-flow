# 变更记录

## 2.1.0 - 2026-08-31

- 采用 MIT License，并补充 vendored Skill 的来源、目录摘要和第三方许可证。
- 新增完整套件安装、校验和安全卸载 CLI。
- 将 live-link 管理移入开发者工具目录，不再作为普通用户安装或发布门禁。
- 新增确定性完整 Release ZIP、SHA-256 和 tag 自动发布工作流。

## 2.0.0 - 2026-08-30

- 将 `cn-patent-workflow-orchestrator` 硬重命名为 `cn-patent-domain-runtime`，不保留兼容 Skill 或转发入口。
- 新增薄 Domain Runtime CLI，统一提供状态查询、阶段校验和受控原子迁移。
- 调用方必须改用新的 Skill slug 与路径；宿主 Agent 继续负责加载专业 Skill、派发子 Agent 和写入业务结果。

## 1.6.0 - 2026-06-06

- 建立 `patents-workflow` 本地开发仓库。
- 纳入 9 个 `cn-patent-*` 核心专利工作流 skill。
- 纳入 6 个支撑型 vendored skill。
- 使用 Windows directory junction 让 `.codex\skills` 直接指向仓库内 skill。
- 添加 manifest、发布前检查和 live 链接检查。
