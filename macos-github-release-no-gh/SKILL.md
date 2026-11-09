---
name: "[【发布 github】] macos-github-release-no-gh"
description: 发布 macOS 应用/项目到 GitHub 时 `gh` CLI 未安装。使用 git + GitHub REST API（从环境变量中获取令牌，从未写入磁盘）。内含**完整内嵌的发布 README 模板 V3.1**（居中头部 + 两行八徽章 + 中英镜像，独立可用、不依赖外部模板文件；格式基准为样板仓库 SSHAppInstaller）、**`scripts/check_readme.py` 机器自检**（头部/徽章/章节顺序/占位符残留/隐私泄漏一次判成败）、隐私安全发布（无本地路径/SSH/真实电子邮件/令牌在仓库中）、DMG 资产上传以及使用 python-stdlib 技巧避免 shell `\n` 转义错误。当用户说“发布 github / 推送 github / 发布版本 / 打 tag 上传 DMG / 按某某仓库格式改 README”且 `gh` 不存在时触发。
---
# Publish to GitHub without `gh` CLI

## When to use
- `gh` CLI not installed (`command -v gh` empty) but user wants to publish a repo / release to GitHub.
- macOS app projects that ship a `.dmg` as the release asset.
- User provides a GitHub PAT (or you read `GITHUB_TOKEN` from env). Token is used **only** in the command line, never written to any file/README/commit.
- 用户说「按某个仓库的格式改 README / 照 xx 项目的样子排版」→ 先看该仓库，再对照本 skill 的「格式基准」与模板 V3.1；改完必跑 `scripts/check_readme.py`。

## 格式基准（唯一参考样板）

新发布的仓库，README **一律对齐这个样板仓库**（2026-11-05 起为唯一基准）：

> **https://github.com/hwl513782273/SSHAppInstaller**

判断「格式对不对」不要凭感觉，逐项对照它：

| 位置 | 样板做法 |
|---|---|
| 头部第 1 块 | `<p align="center">` + `<img width="128">` 应用图标 |
| 头部第 2 块 | `<h1 align="center">{英文名} / {中文名}</h1>`（英文在左、中文在右） |
| 头部第 3 块 | `<b>中文</b> \| <a href="#english">English</a>` 语言锚点 |
| 头部第 4 块 | 徽章第一行 4 枚：platform 黑 / arch 蓝 / engine 橙 / license 绿 |
| 头部第 5 块 | 徽章第二行 4 枚：**network 紫 → released 蓝 → last commit 黄 → release 灰绿**（顺序不可换） |
| 分隔 | 徽章后一条 `---`，再居中「下载最新版 / Download · 问题反馈 / Issues」 |
| 简介 | **一个 blockquote 内**：第 1 行「中文 / English」合并成一行；空 `>` 行；第 2 段作者+许可证 |
| 正文 | `## 中文` 与 `## English` 整块镜像（六节一一对应），再接公共区 `隐私 / 许可证 / 支持` |
| 收尾 | 段落级中英混排（同一段里中文句 + 英文句），不拆成两段 |

**反例**：旧仓库（如 SocialPreviewMaker）那种「一行四徽章 + `## ✨ 简介` + `### 🚀 功能特性` + 无英文镜像」的写法已废弃，不要再产出。

## 发布仓库标准结构

```
{repo}/
├── README.md          # 模板 V3.1 产出，头部八徽章
├── LICENSE            # MIT，Copyright (c) {年份} banqiu
├── app-icon.png       # 256×256，README 头部引用，必须入库
├── .gitignore         # 排除 build/ *.dmg *.app iconset/
├── build.sh           # 相对路径构建，无绝对路径
├── make_dmg.sh        # 打包脚本，产物名遵循命名格式
└── {源码目录}/         # 只提交源码，不提交二进制
```

## Hard rules (privacy)
1. **Token**: pass via `export TOKEN=...` then reference `$TOKEN`. After push, run `git remote set-url origin https://github.com/OWNER/REPO.git` to strip the token from `.git/config`. Never echo it, never put it in README/commit/Source.
2. **No local paths** (`/Users/...`), **no SSH addresses** (`user@host`), **no real personal email**. Use `banqiu@users.noreply.github.com` (GitHub official privacy email) for git author. Public署名 `banqiu` + `Copyright (c) 2026 ... MIT` are fine (user's公开惯例).
3. **Build commands in README** use relative paths + generic macOS version (e.g. `macosx12.0`), never absolute machine paths.

## 私有仓库变体（private + 无署名 / 无版权）

当用户说「走私有 / 不公开」「版权都不写 / 抹掉一切痕迹」时，公开流程的下列环节必须改（2026-09-12 首次实跑验证）：

| 公开版做法 | 私有版改成 |
|---|---|
| `-d '{"public":true}'` | `-d '{"private":true}'` |
| README 头部两行 8 枚 shields 徽章 | **全删**——私库 shields.io 无权限取数据，徽章会破图 |
| 「作者 Author：…／许可证 License：MIT」行、许可证整段、Star/PR 推广段 | **全删** |
| `LICENSE` 文件（含 `Copyright (c) …`） | **不放**；建仓后 `license` 应为 `null` |
| git author = `<账号>@users.noreply.github.com` | 换**中性身份**，且只用 `git config --local`（不碰全局） |
| README 双语镜像 + Releases/Issues 外链 | 中文单语 + 一句「本仓库为私有仓库，仅供内部使用，不对外分发」 |

> **`check_readme.py` 只适用于公开版**：它强制要求双语镜像、八徽章、作者/许可证段，而私有版正相反。
> 私有仓库改 README 时**跳过自检**，改用下方「提交前必扫」的 grep 兜底。

**硬性额外动作：源码里不得残留任何具体名字的字面量。**
最隐蔽的坑 —— 构建/校验脚本里把用户名硬编码成扫描关键字（如 `grep -E "banqiu|Copyright"`），**这本身就是一条可被搜索到的痕迹**。正确做法是让关键字可配置、仓库内只留通用词：

```bash
GUARD_WORDS="${GUARD_WORDS:-}"
PAT_TEXT="Copyright|版权|作者|©|rights reserved|All rights reserved"
[ -n "$GUARD_WORDS" ] && PAT_TEXT="$PAT_TEXT|$GUARD_WORDS"
```

**提交前必扫一遍**（命中即改，不要提交）：

```bash
grep -rn -E "真实用户名|GitHub账号名|/Users/|Copyright|版权|作者|邮箱样式" .
```

**推送后仍要扫交付物**：挂载 DMG 再扫一次（构建脚本的自检只能覆盖 App bundle 内的文本文件）。

**收尾提醒用户**：PAT 若曾在对话里明文出现过，应到 GitHub 撤销重建；本地临时令牌文件用完即删。

## Workflow
1. **Author docs** (only commit source, not binaries):
   - `README.md` — **直接使用下方「README 模板 V3.1（完整内嵌）」章节生成**（模板全文已内嵌本 skill，无需外部文件存在）：复制 → 替换全部 `{占位符}`/`{{占位符}}` → 删除填写提示注释 → 存为仓库根目录 README.md → **跑 `python3 scripts/check_readme.py README.md` 必须全绿**（见「发布前自检」）。
   - `LICENSE` — MIT, `Copyright (c) 2026 banqiu`.
   - `.gitignore` — exclude `build/`, `*.dmg`, verification PNGs, `.app/`, icon 中间产物（`iconset/`、`new_icon*`）。**注意不要排除 `app-icon.png`**（README 头部引用它，必须入库）。
2. **图标 `app-icon.png`** — 按下方「图标规范」产出 256×256 PNG 放仓库根目录。
3. **git init + commit** only `Sources/ README.md LICENSE app-icon.png AppIcon.icns`（icns 可选，png 必须）。
4. **Create repo** (if absent): `curl -H "Authorization: Bearer $TOKEN" -X POST https://api.github.com/user/repos -d '{"name":"REPO","public":true,"auto_init":false}'`.
   - 私有仓库把 `"public":true` 换成 `"private":true`（见下方「私有仓库变体」）。用 `scripts/publish_release.py` 时加 `--private`。
5. **Push**: `git remote add origin https://$TOKEN@github.com/OWNER/REPO.git` → `git push -u origin main` → strip token from remote URL.
   - **Fallback（git 协议被代理/防火墙拦截，但 `api.github.com` 可达时）**：直接走 **Git Database REST API** 推送源码，无需 `git` 协议。步骤（均用 `Authorization: Bearer $TOKEN` 走 `https://api.github.com`，token 仅环境变量）：
     1. `GET /repos/{owner}/{repo}/git/refs/heads/main` 取 base commit SHA → `GET /git/commits/{sha}` 取 base tree SHA。
     2. 对每个待提交文件 `POST /git/blobs`（`{"content": <base64>, "encoding":"base64"}`）。
     3. `POST /git/trees`（`{"base_tree": <tree>, "tree":[{path,mode:"100644",type:"blob",sha}]}`）。
     4. `POST /git/commits`（`{"message","tree","parents":[base_sha],"author"/"committer":{name,email,date}}`）。
     5. `PATCH /git/refs/heads/main`（`{"sha":<new_commit>,"force":false}`）快进 main。
     6. 打 tag：`POST /git/tags` 建 annotated tag 对象 → `POST /git/refs`（`{"ref":"refs/tags/vX.Y.Z","sha":<tag_obj_sha>}`）。
     - 判活：`curl -sI https://api.github.com` 返回 200 即 API 通道通；`curl -sI https://github.com` 若 502 则 git 协议被拦，用本 fallback。
     - 注意：`src` 目录路径含空格/中文时，python 用 `os.path.join` 绝对路径读取文件，勿在 shell 里手动拼路径。
6. **Release + asset**: use `scripts/publish_release.py` (idempotent: checks-then-creates release, checks-then-uploads asset). **Always use python stdlib for JSON** — do NOT inline JSON in shell with `\n` (causes `Invalid control character` parse errors).

## 图标规范（app-icon.png · README 头部引用的入库图标）
- **README 模板的 `{{ICON_PATH}}` 固定填 `app-icon.png`**（仓库根目录相对路径），`<img width="128">` 显示，转 256×256 保证 2x Retina 清晰。
- **源图标定位**（按优先级）：① 项目目录 / `.app/Contents/Resources/` 下的 `AppIcon.icns`；② 已有的 1024×1024 图标 PNG。找不到源图标 → 先按 DMG 图标美化规则生成（去白边 → 拉伸填满 → Apple 圆角），**禁止用占位图发布**。
- **转换命令**（macOS 自带 sips，零依赖）：
  ```bash
  sips -s format png --resampleHeightWidth 256 256 AppIcon.icns --out app-icon.png
  ```
- **入库规则**：`app-icon.png` 必须提交到仓库根目录；`iconset/` 等中间产物不入库。

## 上传资产的三个硬坑（2026-11-05 实跑踩到并已修入脚本）

**① 资产名不支持非 ASCII —— 服务器会静默剥离中文**

GitHub Release asset 的 `name` 只接受 ASCII。实测：

| 请求名 | 服务器实际保存 |
|---|---|
| `12-数码兽全属性图鉴-1.4.15-universal.dmg` | `12-.-1.4.15-universal.dmg` |
| `测试 中文 文件名.txt` | `default.txt` |

不会报错，直接改名，事后很难发现。脚本现在会：
- 上传前自动 ASCII 安全化并打印「原名 → 上传名」
- 上传后校验服务器返回的 `name` 是否等于请求值，不等即判失败
- 想精确控制名字用 `--asset-name "DigimonDex-1.4.15-universal.dmg"`
- **发布前最好直接把本地 DMG 命名成英文**，别依赖兜底

**② 大文件 POST 在内网代理下必被 broken pipe 截断**

实测环境：`uploads.github.com` 解析到 `172.19.0.95`（内网透明代理），
**>16–59MB 的 POST 会随机断开**，报 `curl: (55) Send failure: Broken pipe`。
试过全部无效：`--noproxy`（直连不通）、HTTP/2、关 `Expect: 100-continue`。

唯一解药是**限速**，让发送速度低于代理缓冲区消化能力：

```bash
curl -sS --http1.1 -H "Expect:" -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/octet-stream" \
  --data-binary @"$FILE" --limit-rate 900k \
  "https://uploads.github.com/repos/$OWNER/$REPO/releases/$RID/assets?name=X.dmg"
```

实测 214MB @900KB/s → **237 秒完成，HTTP 201**。
脚本已内置：文件 >50MB 自动限速，失败按 900k → 600k → 400k 阶梯重试 3 次。
需要手动指定时用 `--limit-rate 600`（单位 KB/s，`0` = 不限速）。

**③ 删除资产绝不能硬编码 asset id**

同一次会话里先传 DMG 又传测试文件时，硬编码上一次看到的 id 极易删错
（本项目曾把刚传完的 214MB 主资产误删，重传又花 237 秒）。
一律**按名字查 id 再删**：

```python
assets = GET /repos/{repo}/releases/{rid}/assets
for a in assets:
    if a["name"] == target_name:
        DELETE /repos/{repo}/releases/assets/{a["id"]}
```



## README 模板 V3.1（完整内嵌 · 独立可用，不依赖外部文件）

以下为当前正式版发布 README 模板全文（V3.1 · 2026-11-05 按样板仓库 SSHAppInstaller 逐项对齐，居中头部 + 两行八徽章）。使用：复制下方代码块内容 → 替换占位符 → 删除 `<!-- -->` 注释 → 存为 README.md → 跑 `scripts/check_readme.py` 自检。要点：仅源码入库，DMG 走 Release 附件；Release 命名 `支持最低版本-软件英文名-版本-架构`；徽章转义 空格→%20、`-`→`--`、`|`→%7C、`+`→%2B。

````markdown
<!--
═══════════════════════════════════════════════════════════════
  项目发布 README 模板 v3.1（居中头部 + 两行八徽章版 · 全项目通用）
  v3 变化（2026-09-06 用户定稿）：徽章升级为两行八枚制——
  第一行·规格（静态）：platform 黑 / arch 蓝 / engine 橙 / license 绿
  第二行·状态：network 紫(offline 100%) / released 蓝(静态具体日期，发版时更新) /
  last commit 黄(动态) / release 灰绿(动态版本号，可点击跳 Releases)。
  released 不用动态端点的原因：shields release-date 对超一个月日期只显示月份。
  v3.1 变化（2026-11-05 按样板仓库 SSHAppInstaller 对齐）：① 简介改为**一个 blockquote
  内合并单行**「中文 / English」，空 `>` 行后接作者+许可证行（不再拆成两个 blockquote、
  也不再中文英文各占一行）；② 徽章第二行顺序固定 network → released → last commit →
  release（注释与代码曾不一致，已统一）；③ 新增 scripts/check_readme.py 机器校验。
  使用方法：
  1. 复制本文件到项目仓库根目录，重命名为 README.md
  2. 将所有 {占位符} / {{占位符}} 替换为实际内容（清单见文末注释）
  3. 删除所有本注释块及各章节内的 <!-- --> 填写提示
  规范要点：
  - 头部五件套全部居中：图标(128px) → 标题 → 语言锚点 → 徽章两行（规格行 platform/arch/engine/license + 状态行 network/released/last commit/release）→ 下载/Issues 行
  - 简介用**一个** blockquote：中文与英文用 ` / ` 合并成一行，空 `>` 行，再接作者/许可证行
  - 正文「## 中文」「## English」整块镜像 → 收尾公共区段落级混排
  - 仅源码入库；DMG/包体走 GitHub Releases 附件；应用图标 PNG 需入库（icns 用
    sips -s format png --resampleHeightWidth 256 256 xx.icns --out app-icon.png 转出）
  - Release 命名格式：{最低macOS版本}-{软件英文名}-{版本}-{架构}
═══════════════════════════════════════════════════════════════
-->



<p align="center">
  <img src="{{ICON_PATH}}" width="128" alt="{{APP_NAME}}">
</p>

<h1 align="center">{软件英文名} / {软件中文名}</h1>

<p align="center">
  <b>中文</b> | <a href="#english">English</a>
</p>


<!-- 徽章两行标准（shields.io flat 默认样式 = 深灰 label 段 + 彩色 value 段）：
     第一行·规格（静态）：platform 黑 | arch 蓝 | engine 橙 | license 绿
     第二行·状态：network 紫(静态) → released 蓝(静态日期) → last commit 黄(动态) → release 灰绿(动态,可点击跳 Releases)
       ↑ 这四枚的顺序是样板仓库的固定口径，不要调换（校验脚本按此顺序判定）
     released 徽章 = 静态具体日期（如 badge/released-2026--08--17-0969da，日期中的 - 要写成 --）。
       为什么不用动态端点 github/release-date：它对超过一个月的日期只显示月份（如 "august"），不显示具体日期。
       维护成本：仅发版时随 Release 更新一次日期（发布流程本来就要改 README，零额外成本）。
     last commit 徽章 = 动态端点 github/last-commit/...，每次 push 自动更新；
       显示为相对时间（"3 days ago"；超过一个月显示月份如 "august"，属 shields 的 timeago 风格，并非失效）。
     release 徽章 = 动态端点 github/v/release/...?sort=semver，发新版自动变；外包 <a> 跳转 Releases 页。
     network 徽章：offline 100% 固定写法 badge/network-offline%20100%25-8250df；联网型工具可改为 online-... 并换色。
     值含特殊字符需转义：空格 → %20，短横线 - → --（分隔歧义），竖线 | → %7C，加号 → %2B。
     例：arch 值 "Intel | Apple Silicon" → arch-Intel%20%7C%20Apple%20Silicon-blue
         platform 值 "macOS 12+" → platform-macOS%2012%2B-black -->
<p align="center">
  <img src="https://img.shields.io/badge/platform-{{PLATFORM}}-black" alt="platform">
  <img src="https://img.shields.io/badge/arch-{{ARCH}}-blue" alt="arch">
  <img src="https://img.shields.io/badge/engine-{{ENGINE}}-orange" alt="engine">
  <img src="https://img.shields.io/badge/license-{{LICENSE}}-green" alt="license">
</p>
<p align="center">
  <img src="https://img.shields.io/badge/network-offline%20100%25-8250df" alt="network">
  <img src="https://img.shields.io/badge/released-{发布日期YYYY--MM--DD}-0969da" alt="released">
  <img src="https://img.shields.io/github/last-commit/{GitHub用户名}/{软件英文名}" alt="last commit">
  <a href="{GitHub仓库地址}/releases/latest"><img src="https://img.shields.io/github/v/release/{GitHub用户名}/{软件英文名}?sort=semver" alt="release"></a>
</p>


---

<p align="center">
  <a href="{GitHub仓库地址}/releases/latest">下载最新版 / Download</a>
  ·
  <a href="{GitHub仓库地址}/issues">问题反馈 / Issues</a>
</p>

<!-- 简介 blockquote：一个 blockquote 内写完 —— 第 1 行「中文 / English」合并成一行；空 `>` 行；第 2 段作者+许可证。
     一句话讲清「是什么 + 核心特性 + 类比参照物」，类比知名产品可快速建立认知（如「类似火绒断网修复」）。
     不要拆成两个 blockquote，也不要中文英文各占一行。 -->

> {中文一句话简介：是什么 + 核心特性 + 类比参照物。} / {English one-liner: what it is + core features + familiar analogy.}
>
> **作者 Author：banqiu** **许可证 License：MIT**（详见 LICENSE）。可自由使用、修改与再分发，须保留版权与许可声明。



## 中文

<!-- 按递进逻辑写 5~7 条 bullet：界面展示 → 核心能力 → 智能判断 → 操作方式 → 安全授权 → 技术形态。可用「场景化疑问句」引出卖点，关键结论加粗。 -->

### 主要功能

- {功能 1：界面/状态展示类，写清用户第一眼能看到什么}
- {功能 2：核心检测/处理能力，写清分层判定或分类逻辑}
- {功能 3：智能判断/自动定位，用场景化疑问句引出}
- {功能 4：操作方式，写清交互路径}
- {功能 5：安全/授权机制，写清权限边界}
- {功能 6：技术形态（原生/离线/零依赖等）}

> **平台说明 Platform Note：本工具为 macOS 原生应用（{技术栈，如 SwiftUI + AppKit / Python + PySide6}，打包为 `.app` / `.dmg`），暂无 Windows / Linux 版本。**

### 快速开始

<!-- 4 步编号：下载 → 安装 → 首启放行 → 使用。首启放行写右键打开或 xattr 命令。之后接源码构建与打包 DMG 的代码块，每段前用括号标注前置依赖。 -->

1. 在 [Releases]({GitHub仓库地址}/releases/latest) 下载对应系统的 DMG（见下方「macOS 版本选择」）。
2. 打开 DMG，把 `{软件英文名}.app` 拖入「应用程序」。
3. 首次打开：右键 → 打开（或终端执行 `xattr -dr com.apple.quarantine /Applications/{软件英文名}.app`）。
4. {第 4 步：产品主操作入口的一句话使用说明}。

从源码构建（需 {构建环境要求，如 macOS 12+ 与 Swift 工具链}）：

```
{构建命令，逐行可复制执行}
```

打包 DMG（需 {打包工具依赖}）：

```
{打包命令，产物名遵循命名格式，如 {最低macOS版本}-{软件英文名}-{版本}-universal.dmg}
```

### macOS 版本选择

<!-- 每个 DMG 变体一条 bullet，内嵌「推荐 / 最小体积」等选购指引。末尾 blockquote 补充签名与 Gatekeeper 说明，再单独一行说明命名规则。 -->

- **{机型/场景 1，如 Apple Silicon（M1 及更新）}— 推荐**：下载 `{最低macOS版本}-{软件英文名}-{版本}-universal.dmg`（{适配说明}）。
- **{机型/场景 2}**：下载 `{最低macOS版本}-{软件英文名}-{版本}-arm64.dmg`（纯 arm64，{适配系统范围}）。
- **{机型/场景 3，如 Intel Mac（含老系统）}**：下载 `{最低macOS版本}-{软件英文名}-{版本}-x86_64.dmg`（纯 x86_64，{适配系统范围}）。

> 各档 DMG 均为 ad-hoc 签名、**未公证（notarized）**，首次打开请右键「打开」放行 Gatekeeper；{其他兼容性说明}。各档均由同一套源码构建，源码零改动。

> 仓库「发行版 / Releases」的命名格式为：`支持最低版本-{软件英文名}-版本-架构`（如 `{最低macOS版本}-{软件英文名}-{版本}-universal.dmg`）。第一段数字为该包实际支持的最低 macOS 版本号。

<!-- 功能目录表格：三列（类别 / 项目 / 说明），类别列重复出现形成自然分组（2~5 组），说明列写明具体判定标准或输出物。按产品性质把「检测项」替换为「支持格式 / 支持功能 / 处理项」等。 -->

### {支持的功能 / 支持的格式 / 支持的检测项}

| 类别 | {项目} | 说明 |
|------|--------|------|
| {类别 1} | {项目名} | {具体做什么 + 判定标准 / 输出物} |
| {类别 1} | {项目名} | {说明} |
| {类别 2} | {项目名} | {说明} |
| {类别 3} | {项目名} | {说明} |

<!-- 卖点清单：5~7 条，每条 = 一个 emoji + 加粗短语标题 + 冒号 + 详细说明。emoji 与卖点语义对应；短语口语化、有记忆点。 -->

### 差异化亮点

- {emoji} **{短语标题}**：{详细说明}
- {emoji} **{短语标题}**：{详细说明}
- {emoji} **{短语标题}**：{详细说明}
- {emoji} **{短语标题}**：{详细说明}
- {emoji} **{短语标题}**：{详细说明}
- {emoji} **{短语标题}**：{详细说明}

<!-- 坦诚说明：2~3 条。每条先描述现象、再澄清「并非故障」、最后给解决办法；明确划定功能边界（什么不做/不修）。 -->

### 已知限制

- {限制 1：现象 → 原因澄清 → 解决办法}
- {限制 2：功能边界说明，明确什么不在覆盖范围内}

## English

<!-- 英文区块与中文区块章节一一对应；标题可意译（如「差异化亮点」→ "Why this tool"）；不是逐字翻译，而是镜像重构。保留中文界面按钮名并在英文中标注。 -->

### Highlights

- {对应中文「主要功能」第 1 条}
- {对应第 2 条}
- {对应第 3 条}
- {对应第 4 条}
- {对应第 5 条}
- {对应第 6 条}

> **Platform Note: this is a native macOS app ({tech stack}, packaged as `.app` / `.dmg`). There is no Windows / Linux build.**

### Quick start

1. Download the DMG for your system from [Releases]({GitHub仓库地址}/releases/latest) (see "Choose a macOS build" below).
2. Open the DMG and drag `{软件英文名}.app` into "Applications".
3. First launch: right-click → Open (or run `xattr -dr com.apple.quarantine /Applications/{软件英文名}.app`).
4. {Step 4 in English}.

Build from source (requires {build environment requirements}):

```
{build commands — same as Chinese block}
```

Package the DMG (requires {packaging tool dependency}):

```
{packaging command — same as Chinese block}
```

### Choose a macOS build

- **{machine/scenario 1} — Recommended**: download `{最低macOS版本}-{软件英文名}-{版本}-universal.dmg` ({macOS range}).
- **{machine/scenario 2}**: download `{最低macOS版本}-{软件英文名}-{版本}-arm64.dmg` (arm64 only, {macOS range}).
- **{machine/scenario 3}**: download `{最低macOS版本}-{软件英文名}-{版本}-x86_64.dmg` (x86_64 only, {macOS range}).

> All DMGs are ad-hoc signed and **not notarized**. Right-click → Open on first launch to pass Gatekeeper. All variants are built from the same source with zero modification.

> Release naming format: `minimum-macOS-version-{软件英文名}-version-arch` (e.g. `{最低macOS版本}-{软件英文名}-{版本}-universal.dmg`).

### {Supported features / Supported formats}

| Category | {Item} | Description |
|----------|--------|-------------|
| {Category 1} | {item} | {description with concrete criteria} |
| {Category 2} | {item} | {description} |
| {Category 3} | {item} | {description} |

### Why this tool

- {emoji} **{phrase title}**: {description}
- {emoji} **{phrase title}**: {description}
- {emoji} **{phrase title}**: {description}
- {emoji} **{phrase title}**: {description}
- {emoji} **{phrase title}**: {description}
- {emoji} **{phrase title}**: {description}

### Known limitations

- {limitation 1: symptom → clarification → workaround}
- {limitation 2: scope boundary}

## 隐私与安全 / Privacy and security

<!-- 3 条 bullet：本地运行承诺 → 权限与透明度 → 未公证提醒。隐私敏感类工具必写。中英混排：中文句后接 / 英文句。 -->

- {本地运行 / 不上传数据的承诺，写清哪些数据不外传} / {English version}
- {权限机制说明：需要什么授权、执行过程是否透明可见} / {English version}
- {应用未公证（notarized），请仅从你信任的来源获取，并在首次打开时右键放行} / {English version}

## 许可证 / License

> **MIT License** — 版权归 **banqiu** 所有（{年份}）。
>
> - 允许个人与商业免费使用、修改、再分发，须保留版权与许可声明。
> - 完整条款见 [LICENSE]({GitHub仓库地址}/blob/main/LICENSE)。
>
> {如项目含第三方依赖/组件：第三方组件遵循其各自许可证，详见 THIRD_PARTY_LICENSES.md。无则删除本行。}

## 支持 / Support

<!-- 收尾：中英文各一段自然衔接（非逐句对照），语气「纯自愿、不施压」。 -->

{软件中文名} 是一款免费开源工具，基于 MIT 许可发布{，按实际情况补：离线、无广告}。如果你觉得好用，欢迎在 GitHub 上点个 Star，或反馈问题 / 提交 PR 帮它变得更好 —— 纯自愿。 {Software name} is free, open-source, and ad-free. If it helps you, a GitHub Star or an issue/PR is warmly welcome — entirely optional.

<!--
═══════════════════════════════════════════════════════════════
占位符清单（替换完成后删除本注释）：
  {{ICON_PATH}}    仓库内的应用图标相对路径，通常 app-icon.png（需入库）
  {{APP_NAME}}     图标 alt 文本，一般同 {软件英文名}
  {{PLATFORM}}     徽章平台，如 macOS
  {{ARCH}}         徽章架构，如 arm64 / universal / x86_64
  {{ENGINE}}       徽章技术栈，如 SwiftUI / AppKit / PySide6 / Electron
  {{LICENSE}}      徽章许可证，一般 MIT
  {GitHub用户名}   GitHub 用户名，如 hwl513782273（last commit / release 动态徽章用）
  {发布日期YYYY--MM--DD} 最近一次 Release 的具体日期，如 2026--08--17（注意：日期里的 - 每个都要写成 --）；发版时随 Release 更新
  {软件英文名}     产品英文名，如 SSHAppInstaller
  {软件中文名}     中文别名，如 SSH 应用安装器
  {版本}           语义化版本号，如 1.2 / 1.38-beta
  {最低macOS版本}  该包实际支持的最低 macOS 版本号（数字）；刚构建=当前系统主版本，发布前按指示下调
  {架构}           universal / arm64 / x86_64
  {GitHub仓库地址} 如 https://github.com/hwl513782273/SSHAppInstaller
  {年份}           版权年份，如 2026
  其余 {中文说明}   为该处应写内容的填写指引，替换为实际文案
═══════════════════════════════════════════════════════════════
-->
````

## 发布前自检（必跑 · 把「格式」变成可判定）

写完 README.md 一定先跑，**退出码 0 才允许 commit**：

```bash
python3 scripts/check_readme.py README.md
# 仓库根目录有图标/LICENSE/.gitignore 时可加 --strict-files，缺失按 error 处理
python3 scripts/check_readme.py README.md --strict-files
```

它按样板仓库逐项判定（24 条，✅/⚠️/❌ 三档输出）：

| 组 | 判定内容 |
|---|---|
| 头部 | 居中图标 128px / `<h1>` 英文名 + ` / ` + 中文名 / 语言锚点 `#english` |
| 徽章 | 必须两个 `<p>` 块；第一行 platform→arch→engine→license；**第二行 network→released→last-commit→release（调序即报错）**；release 徽章须外包 `<a>` 跳 Releases |
| 简介 | blockquote 内中英合并成一行；作者/许可证行必须同一块内（拆成两块报错） |
| 章节 | 顶层 `中文 → English → 隐私 → 许可证 → 支持`；中文/English 各六节齐全且顺序正确 |
| 内容 | 平台说明 blockquote；中英功能表格表头；隐私 3 条；MIT 许可证段；支持段 Star 邀请 |
| 安全 | `/Users/`、`/home/`、`ghp_`、`github_pat_`、私钥头、真实邮箱（noreply 除外）命中即报错 |
| 残留 | `{{占位符}}`、`{中文占位符}`、`<!-- -->` 注释未删（行内代码里的字面量会先剔除，不误报） |
| 转义 | 徽章值裸空格 / 裸 `|` / 裸 `+`（`|` 报错，空格与 `+` 警告） |
| 文件 | `app-icon.png` 是否存在、`LICENSE` 是否存在、`.gitignore` 是否排除了 `*.dmg` 却又没误排图标 |

实测基线（2026-11-05）：样板仓库 SSHAppInstaller 的 README = **18 项通过 / 0 错误**；
旧格式仓库 SocialPreviewMaker 的 README = **16 项错误**（正好可用于确认脚本没写虚）。

## Asset naming
`支持最低版本-软件名(英文)-版本-架构` e.g. `12-SocialPreviewMaker-1.4.10-universal.dmg`.

## Script usage
```bash
# ① 先自检 README 格式（0 错误才继续）
python3 scripts/check_readme.py README.md

# ② 再发版 + 传资产
export TOKEN="ghp_xxx"
python3 scripts/publish_release.py \
  --repo hwl513782273/SocialPreviewMaker \
  --tag v1.4.10 --name "v1.4.10" \
  --dmgs "12-SocialPreviewMaker-1.4.10-universal.dmg" \
  --notes "$(printf 'line1\nline2')"
```
Script reads `TOKEN` from env, is idempotent, prints final asset list + html_url.
