---
name: "[dmg] macos-dmg-build"
description: macOS 原生 App 构建 + DMG 交付通用流水线（不限源码框架：SwiftUI/AppKit swiftc 直编、PyInstaller、Electron 等均可）→ 图标自动生成（SwitchLink 风格）→ 品牌头 → 用 hdiutil 打 DMG（新命名规则）→ 安装/更新到 /Applications（规避 cp -R 嵌套坑）→ 启动冒烟验证 → 关于界面。适用于任意 macOS 桌面 App 项目。
---
# macOS App 通用流水线：构建 + DMG + 安装

**不限源码框架**——SwiftUI/AppKit（swiftc 直编）、PyInstaller、Electron、Tauri 等任意技术栈产出的 macOS `.app`，交付 DMG 时都用本流程。编译环节按各自技术栈走，其余环节（图标、品牌头、命名、打包、安装、验证）完全通用。

## 技术栈选择规则（新建项目时）
- **从零新建 macOS 原生 App 且用户未指定技术栈 → 默认 SwiftUI/AppKit（swiftc 直编）**：零运行时依赖、产物最轻、最贴合系统视觉，DMG 交付最快。
- **项目已存在** → 沿用项目现有技术栈（Python 项目走 PyInstaller、跨平台项目走 Electron 等），不迁移重写。
- **用户点名技术栈** → 一切以用户指定为准。
- 各技术栈只影响「编译/打包出 .app」这一步；`.app` 产出后，图标、品牌头、DMG、安装、验证环节完全同流程。

## 何时用
- 需要产出 `.app` + 可安装 `.dmg`（拖入 /Applications 即用）。
- SwiftUI/AppKit 直编工程结构：`Sources/*.swift` + `Resources/Info.plist` + `build.sh` + `make_dmg.sh`（见「SwiftUI 编译路径」）；其他框架用各自的打包产物 `.app`，从「图标生成」章节起进入本流程。
- 本机需 Xcode 命令行工具（`xcodebuild` / `swift` / `xcrun` 可用）。

## SwiftUI/AppKit 编译路径（swiftc 直编；其他框架跳过本节）

## 工程骨架（SwiftUI/AppKit 直编最小可用）
- `Sources/`：SwiftUI 源码。`@main App` 用 `WindowGroup` + 可选 `MenuBarExtra`。
- `Resources/Info.plist`：必须含 `CFBundleExecutable`、`CFBundleIdentifier`、`CFBundleShortVersionString`、`LSMinimumSystemVersion`、`NSHumanReadableCopyright`。
- `build.sh`：用 `swiftc -O -framework SwiftUI -framework AppKit -o build/FocusTrain.app/Contents/MacOS/FocusTrain Sources/*.swift`，再 `mkdir -p build/FocusTrain.app/Contents/{MacOS,Resources}`、拷贝 Info.plist、最后 `codesign --force --deep --sign - build/FocusTrain.app`（ad-hoc）。
- `make_dmg.sh`：`hdiutil create -volname "软件名" -srcfolder staging -ov -format UDZO "<最低macOS版本>-软件名-<版本>-<架构>.dmg"`（命名规则见下文「版本与产物命名」），staging 内放 `.app` + `ln -s /Applications Applications`。
  - ⚠️ **staging 绝不要用 `rm -rf` 清理**：本环境 safe-delete 钩子会拦（阈值 50 项，**即使目录已不存在也拦**，`set -e` 下脚本直接中断）。推荐写法：
    ```bash
    STAGING=$(mktemp -d "${TMPDIR:-/tmp}/App-dmg.XXXXXX")   # 每次全新目录，天然无残留
    cp -R "build/App.app" "$STAGING/"
    ln -s /Applications "$STAGING/Applications"
    hdiutil create -volname "App" -srcfolder "$STAGING" -ov -format UDZO "$DMG"
    mv "$STAGING" "$HOME/.Trash/App-dmg-staging-$(date +%s)"  # 走废纸篓收尾
    ```
    固定目录名 + `rm -rf` 的老写法还会让 `cp -R` 二次拷贝变成 `staging/App.app/App.app` 嵌套，`mktemp` 方案一并规避。

## 图标生成（构建时自动做，不待用户吩咐）
每次构建 `.app` / 打 DMG 时，**自动**生成配套图标并拷入 bundle。**风格标准 = SwitchLink 风格（2026-09-06 用户拍板）**：
1. **构图：满铺背景 + 大主体**。背景铺满整个 1024×1024 画布（浅色渐变等），内容主体组合占画布约 **75–80%**（可多层：背景大件 + 前景小件错落，参考 SwitchLink「iMac 背景左上 + Switch 前景右下 1/4」双主体布局）；不预烘焙圆角，让 macOS 唯一套 squircle。
2. **绘制方式**：优先纯代码绘制（PIL：渐变 + `rounded_rectangle`/`ellipse` 图层 + 柔和投影），零外部素材、可复现；有现成源图标则在源图基础上做。
3. **透明角蒙版**：用 `ImageDraw.rounded_rectangle` 硬边蒙版（radius = S×0.225）直接当 alpha 通道——**四角必须 alpha=0**，否则 macOS 按满铺矩形显示方形不套圆角。
4. **逐档独立套蒙版**：11 档 iconset（含 `icon_64x64.png`），每档**先 resize 再套蒙版**（先蒙版后 resize 会让小档透明角失效）；生成后**逐档核对像素尺寸**（不只看文件名）。
5. **转 ICNS**：`iconutil -c icns -o AppIcon.icns AppIcon.iconset`，拷入 `Contents/Resources/`，确认 `Info.plist` 有 `CFBundleIconFile = AppIcon`。
6. 诊断与踩坑（`sips -g hasAlpha` + 四角采样、双层圆角、缓存清除等）见技能 **`[图标] macos-app-icon-squircle`**。
7. ⚠️ **脚本完整性自查**：图标脚本生成后必须**通读一遍确认无截断/语法残缺**（SwitchLink 的 `make_icon.py` 曾因输出截断损坏，产物在、脚本跑不了），并实际跑通一次验证产物与脚本一致。

## git 版本管理（项目创建时必须，非可选）
项目动工第一步（源码初版落地后立即执行，**不是交付时才补**）：
1. `git init`
2. 同步创建 `.gitignore`：排除 `build/`、`staging/`、`*.dmg`、`.DS_Store` 等产物与临时文件——**只跟踪源码**（git 对二进制几乎无压缩收益，不 ignore 会让 `.git` 无限膨胀）。
3. `git add -A` → `git commit`，形成第一条历史；之后**每次改动完成即 commit**，保证可回滚。
4. 汇报时带 git 状态行：`本地git✅/❌，本次修改 commit✅/❌`（如已 push 加 `远程push✅/❌`）。

## 软件内标题栏（顶部品牌头，默认带上）
每个用本流水线构建的 App，主窗口内容区顶部**默认**加品牌头（左上角图标 + 应用名 + 版本号，右上角操作按钮），完整规范与 Swift 代码模板见技能 **`[品牌头] macos-app-header`**，要点：
- 布局：`HStack(spacing: 10)`；图标 `AppIcon` 36×36pt + `cornerRadius(8)`；应用名 `.font(.title2.bold())`；版本号 `.font(.subheadline)` + `.foregroundStyle(.secondary)`（版本从 `CFBundleShortVersionString` 读取，随迭代自动更新）
- 右侧按钮：SF Symbols `gearshape`（设置）/ `info.circle`（关于），`.buttonStyle(.borderless)` + `.help()` 悬停提示
- 内边距：水平 16pt / 垂直 12pt；背景 `Color(NSColor.windowBackgroundColor)`（自动适配深浅色）；头部下方 `Divider()`
- ⚠️ 品牌头是「内容区内的头部」，不替换系统 title bar；「关于」按钮路由到 AppDelegate 的 `showAbout()`——与「OPEN_ABOUT 环境变量自动弹关于」**共用同一个 `showAbout()`**，版权信息只维护一处
- 跨窗口复用：设置/关于窗口如需统一头部，复制同一段 HStack 即可（右侧按钮按需改「完成/关闭」）

## 关键步骤
1. **编译**：`./build.sh` → 校验 `build/<App>.app/Contents/MacOS/<App>` 存在、`file` 为 `Mach-O 64-bit arm64`。
2. **打 DMG**：`./make_dmg.sh`。
3. **安装到 /Applications（重点避坑）**：
   - ⚠️ **`cp -R build/Foo.app /Applications/Foo.app` 在目标已存在时会把源嵌套成 `/Applications/Foo.app/Foo.app`，导致旧版未被替换！**
   - 正确做法：先把旧 app 移入**废纸篓**（不硬删）：`mv /Applications/Foo.app "$HOME/.Trash/Foo-$(date +%s).app"`，再 `cp -R build/Foo.app /Applications/Foo.app`。
   - 刷新 LaunchServices：`/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister -f /Applications/Foo.app`。
4. **冒烟验证**：`open /Applications/Foo.app`；`sleep 3`；`pgrep -f "Foo.app"` 确认进程起来。`pkill -f "Foo.app"` 可结束测试实例。

## 版本与产物命名（遵循用户 additive 规则）
- 每次迭代升 `CFBundleShortVersionString`（如 1.0 → 1.0.1）。
- **DMG 命名（2026-09-02 新规则）**：`<最低macOS版本>-软件名-<版本>-<架构>.dmg`，例 `15-OfflineOCR-1.2-universal.dmg`。第一段 = 该 DMG 实际支持的**最低 macOS 版本号（数字）**，刚构建时 = 当前系统版本（本机 macOS 15.7.8 → `15`），发布前按用户指示下调（如降到 `12`）。
- **`.app` / `.apk` 沿用旧规则**：`<应用名>_v<版本号>`（例 `OfflineOCR_v1.2.apk`）；`.app` 拖入 /Applications 后保持原名。
- **不得覆盖旧的带版本号产物**，新版本一律生成新文件，旧文件原样保留（additive-only）。
- 删除旧安装只走废纸篓（`mv` 到 `~/.Trash`），严禁 `rm -rf`。

## 常见坑
- **SwiftUI/AppKit 直编**：`swiftc` 编译报错 `write(to:)` 需 `try?`；macOS 弃用 `onChange(of:)` 旧式 → 用 `.onChange(of:) { }`（无参数，macOS 14+）。
- 强制暗色主题：在根 `TabView`/`WindowGroup` 内容上加 `.preferredColorScheme(.dark)` + `.tint(主色)`。
- 非 GUI 会话里 `launchctl load`/`bootstrap gui/$UID` 会报 I/O error 5，属正常；plist 放 `~/Library/LaunchAgents/` 即可，用户本机真实登录/终端里 load 才生效。
- 公证（需 Developer ID）：`codesign --force --deep --options runtime --sign "Developer ID Application: xxx"` → `xcrun notarytool submit <dmg> --keychain-profile xxx --wait` → `xcrun stapler staple <dmg>`。
- **PyInstaller/Electron 等框架**：产物 `.app` 生成后同样进入本流程的图标/品牌头/DMG/安装/验证环节；PyInstaller 注意 `--windowed`（免控制台窗口）与架构参数（arm64 / universal2）。

## 验证清单（交付前）
- [ ] 项目已 `git init` + `.gitignore` 排除产物，源码已 commit
- [ ] swiftc 编译零错误零警告
- [ ] 图标已生成：ICNS 拷入 Resources、`CFBundleIconFile` 正确、**四角 alpha=0**（采样验证）、11 档像素尺寸逐档核对
- [ ] 主窗口带品牌头（图标+名称+版本+操作按钮），「关于」路由到 `showAbout()`
- [ ] 二进制 `file` 为 arm64 Mach-O（universal 则双架构）
- [ ] `plutil -lint Info.plist` 通过；`codesign -vvv` ad-hoc 有效
- [ ] 启动冒烟 `pgrep` 进程存在、无崩溃
- [ ] /Applications 安装**无嵌套**、版本号正确
- [ ] DMG 文件名符合 `<最低macOS版本>-软件名-<版本>-<架构>.dmg`
- [ ] 旧版 DMG 保留未被覆盖
