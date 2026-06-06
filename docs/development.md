# 开发说明

## 仓库定位

`patents-workflow` 是开发仓库，也是 15 个声明 skill 的真实文件位置。Codex 实际扫描的 `.codex\skills\<skill-name>` 目录会通过 Windows directory junction 指向本仓库的 `skills\<skill-name>`。

## 日常修改

可以直接修改：

```text
C:\Users\spade k\.codex\skills\<skill-name>
```

由于该目录是 junction，Git 会在仓库中看到对应改动：

```powershell
git status --short
git diff
```

## 本地检查

```powershell
.\scripts\check-release.ps1
.\scripts\check-live-links.ps1
```

## 版本迭代

仓库名保持 `patents-workflow` 不变。版本通过 `VERSION`、`manifest.json`、`CHANGELOG.md`、git tag 和 GitHub Release 管理。
