---
name: "[社交预览生成器] social-preview-generator"
description: 为 macOS/GitHub 项目批量生成统一风格的社交预览图（social-preview.png，1280×640）。风格源自 AppScheduler 模板：深色垂直渐变背景 + 左侧 App 图标 + 右侧 Light 细字重大标题/主色短下划线/副标题/标语/描边胶囊标签，accent 色自动从图标采样。触发词：社交预览图、social preview、social-preview、README 头图、仓库预览图、批量生成预览图。
---
# Social Preview Generator（社交预览图生成器）

从一张模板图拆解出可参数化的设计规格，再用 Pillow 脚本批量生成同风格 1280×640 预览图。已在 12 个真实仓库上验证（AppScheduler / NetFix / StarClock 等）。

## 文件说明

- `scripts/make_social_preview.py` — 单张生成器（参数化，含长标题自动缩字号）
- `scripts/batch_make_previews.py` — 批量驱动（含图标自动取色逻辑 `sample_accent()`）
- `references/template_diagram.svg` — 风格规格标注图

## 风格规格（模板拆解结论）

画布 1280×640（GitHub 社交预览 2:1 标准）。全图只允许 3 类颜色：

1. **背景**：accent 同色系的垂直线性渐变，上暗下亮（如 `#0f0c1d → #2a1e52`）
2. **主色 accent**：用于标题下划线、胶囊描边（从 App 图标自动采样）
3. **文字**：标题纯白、副标题近白（如 `#f0edfa`）、标语/胶囊浅色（accent 的淡化版，如 `#b9a7e8`）

布局（左图右文，整体垂直居中）：

| 元素 | 规格 |
|------|------|
| App 图标 | 320×320，x=95，垂直居中，RGBA 透明底直接 alpha_composite |
| H1 产品名 | Helvetica Neue **Light**（ttc index 7）78px，白色。⚠️ UltraLight(index 5) 在 1280 宽成品上笔画过细，已弃用 |
| 下划线 | accent 色，宽≈标题宽 1/4（≥90px），高 5px。⚠️ 纵向位置必须用 `draw.textbbox((x,y),…)` 实际字形底边定位，禁止用 bbox 高度推算（否则横线压住字母） |
| H2 副标题 | PingFang 38px，一句话中文定位「XX器 · 一句话」 |
| H3 标语 | PingFang 29px，「macOS 原生 · 特性 · 特性」 |
| 胶囊 ×3 | 透明底 + accent 描边 2px + 圆角=高/2 + 浅色文字 26px，间距 18px |
| 文字块起点 | x=460，逐行排版后整块垂直居中 |

## 单张生成

```bash
python3 scripts/make_social_preview.py \
  --name "ScrcpyGUI" \
  --subtitle "安卓投屏 · 零依赖开箱即用" \
  --tagline "macOS 原生 · USB / 无线投屏 · 内置 scrcpy 4.1 引擎" \
  --tags "USB 投屏,无线配对,老机型模式" \
  --icon AppIcon.png \
  --accent "#7c52d9" --bg-top "#0f0c1d" --bg-bottom "#2a1e52" \
  --output social-preview.png
```

## 批量生成（多项目）

参照 `scripts/batch_make_previews.py` 的 `PROJECTS` 列表，每个项目填 repo/name/subtitle/tagline/tags/icon/outdir。文案来源：WebFetch 抓仓库 README，提炼「一句话定位 + 标语 + 恰好 3 个 2~6 字功能标签」。accent/bg 用内置 `sample_accent()` 从图标自动采样（饱和色相众数 → accent 亮度 0.82、bg_top 亮度 0.10、bg_bottom 0.32）。

## 关键坑（必读）

1. **标题字重**：`/System/Library/Fonts/HelveticaNeue.ttc` 的 face 索引：0=Regular 5=UltraLight 7=**Light（标题默认用这个）**。UltraLight 在大图好看但缩到成品过细；Regular 又偏粗。
2. **下划线压字**：文字装饰线的纵向位置必须以「实际绘制位置」的 `textbbox` 底边为准；用 bbox 尺寸（`box[3]-box[1]`）推算会漏掉顶部留白，细字重时横线直接叠在字母上（曾翻车）。垂直居中的块高同理要用含顶部留白的字形深度。
2. **长标题裁边**：英文名长（如 GoogleChromeUpdateBlocker）会超出画布。生成器已内置自动缩字号（78→40 每次 -4，可用宽度 = 1280 - text_x - 40）；副标题/标语超宽降为 32/25px。
3. **SVG 转 PNG**（如需渲染标注图/模板图）：
   - ❌ `qlmanage`：沙盒报 "Operation not permitted"
   - ❌ `cairosvg`：macOS 无系统 libcairo，dlopen 失败
   - ✅ Chrome 无头：`"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --no-sandbox --headless=old --disable-gpu --force-device-scale-factor=2 --screenshot=out.png --window-size=680,560 --hide-scrollbars "file:///path/x.svg"`（--no-sandbox 必须，否则 GPU 初始化 FATAL）
4. **Python/Pillow**：装在 managed venv `~/.workbuddy/binaries/python/envs/default`（pillow 已装）。`getdata()` 有 DeprecationWarning，无害。
5. **文件安全**：输出到已有交付文件夹时先检查同名文件，已存在则改名（如 `-v2`），绝不覆盖；批量复制用 `cp -n`。
6. **图标来源**：优先用项目本地 `AppIcon.png`/`iconset` 最大尺寸（512/1024）；仓库没有时从 `raw.githubusercontent.com/<user>/<repo>/main/AppIcon.png` 下载。图标必须是 RGBA（透明角），否则叠不上渐变背景。
7. **上传方式**：成品提交进仓库根目录 + GitHub Settings → Social preview 上传一次。

## 验收方法

拼总览图一次检查全部成品（3 列网格、每格 426×213 + 项目名标签），肉眼核对：标题是否完整不裁边、accent 是否与图标同色系、胶囊是否等高、整块是否垂直居中。
