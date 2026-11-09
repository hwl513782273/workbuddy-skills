<h1 align="center">workbuddy-skills / WorkBuddy 技能合集</h1>

<p align="center">
  <b>中文</b> | <a href="#english">English</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-macOS-black" alt="platform">
  <img src="https://img.shields.io/badge/skills-3--included-blue" alt="skills">
  <img src="https://img.shields.io/badge/lang-中文%20%2F%20English-orange" alt="lang">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="license">
</p>
<p align="center">
  <img src="https://img.shields.io/github/last-commit/hwl513782273/workbuddy-skills" alt="last commit">
  <img src="https://img.shields.io/github/stars/hwl513782273/workbuddy-skills" alt="stars">
</p>

---

> 三个 macOS 交付向的 Agent Skill：打包 DMG、无 gh CLI 发 GitHub Release、批量生成社交预览图。基于实际项目反复踩坑后固化，纯脚本 + 纯文档，无外部运行时依赖。 / Three macOS-delivery-focused agent skills: build DMGs, publish GitHub releases without the `gh` CLI, and batch-generate social preview images. Hardened through real projects; scripts and docs only, no external runtime.
>
> **作者 Author：banqiu** **许可证 License：MIT**（详见 LICENSE）。

## 中文

### 包含的技能

| 目录 | 用途 | 依赖 |
|------|------|------|
| `macos-dmg-build/` | macOS App 从构建到 `.dmg` 的完整流水线：图标自动生成（SwitchLink 风格 squircle）、顶部品牌头、`hdiutil` 打包、安装到 `/Applications`（规避 `cp -R` 嵌套坑）、启动冒烟验证 | macOS 命令行工具（`swiftc` / `sips` / `iconutil` / `hdiutil`） |
| `macos-github-release-no-gh/` | `gh` CLI 不存在时，用 `git` + GitHub REST API 建仓、推送、打 tag、发 Release、上传 DMG；内含 README 模板 V3.1 与机器自检脚本 | Python 3 标准库（零第三方包） |
| `social-preview-generator/` | 批量生成 1280×640 的 GitHub 社交预览图：深色渐变 + 图标自动取色 + 左图右文版式 | Python 3 + Pillow |

### 安装

把需要的目录整个拷进本地技能库即可，目录名就是技能名：

```bash
git clone https://github.com/hwl513782273/workbuddy-skills.git
cp -R workbuddy-skills/macos-dmg-build ~/.workbuddy/skills/
cp -R workbuddy-skills/macos-github-release-no-gh ~/.workbuddy/skills/
cp -R workbuddy-skills/social-preview-generator ~/.workbuddy/skills/
```

> 只想用其中一个，就只拷那一个目录，各自独立、互不依赖。

### 使用

技能由 Agent 按 `SKILL.md` 的 `description` 触发词自动匹配；也可以直接点名，例如「按 DMG 流程打包这个 App」「没有 gh 帮我发 GitHub Release」「给我的仓库做社交预览图」。

三个技能各自的完整规范、踩坑清单与代码模板都在对应目录的 `SKILL.md` 里，例如：

- DMG 打包的分卷规则：产物 >2 GiB 时 `hdiutil create -srcfolder` 会忽略 `segmentSize`，必须改用 `hdiutil segment`
- Release 资产名不支持非 ASCII：中文名会被服务端静默剥离，上传脚本已内置 ASCII 安全化 + 回读校验
- 大文件上传在内网代理下必被 broken pipe 截断，唯一解药是 `--limit-rate` 限速（脚本按 900k → 600k → 400k 阶梯重试）
- 社交预览图的标题必须用 Helvetica Neue **Light**（face index 7），下划线纵向位置要用 `textbbox()` 实际字形底边定位，否则细字重时横线压字

### 目录结构

```
workbuddy-skills/
├── macos-dmg-build/
│   └── SKILL.md
├── macos-github-release-no-gh/
│   ├── SKILL.md
│   └── scripts/
│       ├── check_readme.py        # README 格式机器自检（24 项）
│       └── publish_release.py     # 幂等发版 + 资产上传
└── social-preview-generator/
    ├── SKILL.md
    ├── references/
    │   └── template_diagram.svg   # 风格规格标注图
    └── scripts/
        ├── make_social_preview.py # 单张生成器
        └── batch_make_previews.py # 批量驱动（示例配置）
```

### 已知限制

- **仅面向 macOS**：DMG 打包链路依赖 macOS 专有工具（`hdiutil`、`iconutil`、`sips`）；另两个技能的生成逻辑本身跨平台，但产物与验收步骤按 macOS 写。
- **未公证（notarized）**：DMG 流程默认走 ad-hoc 签名，产物首次打开需右键放行；要公证得自备 Developer ID。
- `batch_make_previews.py` 里的项目清单是示例配置，需要按自己的仓库改写 `PROJECTS` 与 `PREVIEW_BASE`（默认取仓库根目录）。

## English

### What's inside

| Folder | Purpose | Requirements |
|--------|---------|--------------|
| `macos-dmg-build/` | End-to-end macOS app pipeline: auto-generated squircle icon (SwitchLink style), in-app brand header, `hdiutil` packaging, install into `/Applications` (avoids the `cp -R` nesting trap), launch smoke test | macOS command line tools (`swiftc` / `sips` / `iconutil` / `hdiutil`) |
| `macos-github-release-no-gh/` | Create repos, push, tag, publish releases and upload DMGs with `git` + the GitHub REST API when `gh` is unavailable. Ships README template V3.1 and a machine checker | Python 3 stdlib only |
| `social-preview-generator/` | Batch-generate 1280×640 GitHub social preview cards: dark gradient, accent sampled from the app icon, icon-left text-right layout | Python 3 + Pillow |

### Install

Copy the folder you need into your local skills directory — the folder name is the skill name:

```bash
git clone https://github.com/hwl513782273/workbuddy-skills.git
cp -R workbuddy-skills/macos-dmg-build ~/.workbuddy/skills/
cp -R workbuddy-skills/macos-github-release-no-gh ~/.workbuddy/skills/
cp -R workbuddy-skills/social-preview-generator ~/.workbuddy/skills/
```

> Each folder is self-contained; take only the ones you need.

### Usage

Skills are picked up automatically from the trigger keywords in each `SKILL.md` `description`, or you can reference them by name ("package this app with the DMG pipeline", "publish a GitHub release without gh", "make social previews for my repos").

### Known limitations

- **macOS only**: the DMG chain needs `hdiutil` / `iconutil` / `sips`. The other two skills are cross-platform in logic, but their outputs and acceptance steps are written for macOS.
- **Not notarized**: DMGs are ad-hoc signed by default, so right-click → Open on first launch. Notarization requires your own Developer ID.
- `batch_make_previews.py` ships with sample project config; adjust `PROJECTS` and `PREVIEW_BASE` (defaults to the repo root).

## 许可证 / License

> **MIT License** — 版权归 **banqiu** 所有（2026）。
>
> - 允许个人与商业免费使用、修改、再分发，须保留版权与许可声明。
> - 完整条款见 [LICENSE](https://github.com/hwl513782273/workbuddy-skills/blob/main/LICENSE)。

## 支持 / Support

这些技能都是从实际项目里反复踩坑后沉淀下来的，免费开源，基于 MIT 许可发布。如果它们帮你省了几次调试，欢迎在 GitHub 上点个 Star，或反馈问题 / 提交 PR —— 纯自愿。 These skills were distilled from real projects and many dead ends. They are free and open-source under MIT. If they save you a debugging session, a Star or an issue/PR is warmly welcome — entirely optional.
