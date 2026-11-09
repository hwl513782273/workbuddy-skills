#!/usr/bin/env python3
"""batch_make_previews.py — 批量为 11 个项目生成 social-preview.png"""
import colorsys
import os
import subprocess
import sys

from PIL import Image

# 用途：批量项目的根路径——下面 PROJECTS 里的 icon / outdir 都相对它拼接。
# 调用时机：main() 逐个项目算图标绝对路径与输出目录时读取。
# 取值优先级：环境变量 PREVIEW_BASE > 脚本所在仓库根目录（<repo>/social-preview-generator/scripts/ 往上两级）。
BASE = os.environ.get("PREVIEW_BASE") or os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
# 用途：单张生成器路径，固定取同目录下的 make_social_preview.py，不依赖外部工程。
# 调用时机：main() 组装子进程命令行时。
GEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "make_social_preview.py")
# 用途：子进程用的 Python 解释器，沿用当前解释器以保证 Pillow 等依赖一致。
PY = sys.executable

# 用途：批量任务清单（示例配置，按自己的项目改写即可）。
# 每个项目：repo=仓库名（仅用于日志）、name=标题、subtitle=副标题、tagline=标语、
#           tags=恰好 3 个短标签、icon=相对 BASE 的图标路径、outdir=相对 BASE 的输出目录。
PROJECTS = [
    dict(repo="WBMemoryMigrator", name="WBMemoryMigrator",
         subtitle="记忆迁移器 · 换机一键备份恢复",
         tagline="macOS 原生 · 记忆对话技能项目一个包带走 · 纯本地零上传",
         tags=["一键备份", "路径重映射", "双架构"],
         icon="WBMemoryMigrator/Resources/AppIcon.png", outdir="WBMemoryMigrator"),
    dict(repo="SkillLocalizer", name="SkillLocalizer",
         subtitle="技能本地化器 · AI 批量中文化",
         tagline="macOS 原生 · 名称解释面板一键翻译 · 凭证隔离存钥匙串",
         tags=["AI 批量翻译", "多接口兼容", "英文检测"],
         icon="social-preview-batch/icons/SkillLocalizer.png", outdir="SkillLocalizer-skill 中文化"),
    dict(repo="AppScheduler", name="AppScheduler",
         subtitle="定时启动器 · 到点自动打开指定 App",
         tagline="macOS 原生 · 沉浸式全屏倒计时 · 开机自启",
         tags=["每日定时", "倒计时", "一键测试"],
         icon="定时启动AppScheduler/AppIcon.png", outdir="定时启动AppScheduler",
         outname="social-preview-v2.png"),
    dict(repo="IPAAnalyzer", name="IPAAnalyzer",
         subtitle="IPA 分析器 · 拖入即读安装包",
         tagline="macOS 原生 · 名称版本账号秒读 · 重打包橙色预警",
         tags=["拖入即读", "下载账号", "改包预警"],
         icon="IPAAnalyzer/AppIcon_1024.png", outdir="IPAAnalyzer"),
    dict(repo="QuarkCloudDriveBlocker", name="QuarkCloudDriveBlocker",
         subtitle="夸克网盘屏蔽器 · 一键阻止升级",
         tagline="macOS 原生 · 锁定目录权限阻断 4.X · 可恢复零副作用",
         tags=["一键屏蔽", "清理待更新", "状态透明"],
         icon="social-preview-batch/icons/QuarkCloudDriveBlocker.png", outdir="夸克网盘屏蔽器"),
    dict(repo="GoogleChromeUpdateBlocker", name="GoogleChromeUpdateBlocker",
         subtitle="Chrome 屏蔽器 · 告别后台偷偷升级",
         tagline="macOS 原生 · 同名冲突原理锁死更新 · 一键恢复可逆",
         tags=["一键屏蔽", "状态检测", "启动项管理"],
         icon="Google Chrome更新屏蔽器/AppIcon_1024.png", outdir="Google Chrome更新屏蔽器"),
    dict(repo="WorkBuddyUpdateBlocker", name="WorkBuddyUpdateBlocker",
         subtitle="更新屏蔽器 · 阻断强制自动升级",
         tagline="macOS 原生 · hosts 域名屏蔽加目录锁 · 双保险可恢复",
         tags=["双层阻断", "备份更新包", "一键还原"],
         icon="workbuddy 屏蔽更新器/icon.png", outdir="workbuddy 屏蔽更新器"),
    dict(repo="StarClock", name="StarClock",
         subtitle="星球时钟 · 星战字幕桌面常驻",
         tagline="macOS 原生 · 真透视玻璃字透壁纸 · 多屏沉浸遮罩",
         tags=["五种透视", "玻璃字", "多显示器"],
         icon="social-preview-batch/icons/StarClock.png", outdir="social-preview-batch"),
    dict(repo="MacInspect", name="MacInspect",
         subtitle="Mac 验机 · 二手交易一键全检",
         tagline="macOS 原生 · 15 大项检测加风险评分 · 110 型号参数库",
         tags=["风险评分", "企业锁检测", "HTML 报告"],
         icon="Macinspect/AppIcon.png", outdir="Macinspect"),
    dict(repo="silent-launcher", name="silent-launcher",
         subtitle="静默启动管理器 · 登录自动隐藏窗口",
         tagline="macOS 原生 · LaunchAgent 静默循环 · 兜底强关零联网",
         tags=["登录静默", "图形管理", "开机自启"],
         icon="social-preview-batch/icons/silent-launcher.png", outdir="开机静默"),
    dict(repo="NetFix", name="NetFix",
         subtitle="网络急救 · 断网故障一键诊断修复",
         tagline="macOS 原生 · 代理 DNS 网关精准定位 · 修复透明可审计",
         tags=["一键诊断", "分层判定", "一键修复"],
         icon="NetFix/AppIcon_1024.png", outdir="NetFix"),
]


def hx(c):
    return "#%02x%02x%02x" % c


def sample_accent(path):
    """取图标中饱和度最高、出现最多的色相，返回 (accent, bg_top, bg_bottom) hex"""
    im = Image.open(path).convert("RGBA").resize((96, 96))
    hues = {}
    for (r, g, b, a) in im.getdata():
        if a < 200:
            continue
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s < 0.30 or v < 0.30:
            continue
        key = round(h * 36)  # 10° 一档
        hues[key] = hues.get(key, 0) + 1
    if not hues:
        return "#7c52d9", "#0f0c1d", "#2a1e52"
    hue = max(hues, key=hues.get) / 36.0
    accent = tuple(round(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.72, 0.82))
    top = tuple(round(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.55, 0.10))
    bot = tuple(round(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.60, 0.32))
    return hx(accent), hx(top), hx(bot)


def main():
    results = []
    for p in PROJECTS:
        icon = os.path.join(BASE, p["icon"])
        outdir = os.path.join(BASE, p["outdir"])
        os.makedirs(outdir, exist_ok=True)
        outname = p.get("outname", "social-preview.png")
        out = os.path.join(outdir, outname)
        if os.path.exists(out):
            out = os.path.join(outdir, outname.replace(".png", "-v2.png"))
        accent, bg_top, bg_bottom = sample_accent(icon)
        cmd = [PY, GEN,
               "--name", p["name"],
               "--subtitle", p["subtitle"],
               "--tagline", p["tagline"],
               "--tags", ",".join(p["tags"]),
               "--icon", icon,
               "--accent", accent,
               "--bg-top", bg_top,
               "--bg-bottom", bg_bottom,
               "--output", out]
        r = subprocess.run(cmd, capture_output=True, text=True)
        status = "OK" if r.returncode == 0 else "FAIL " + r.stderr[-200:]
        results.append((p["repo"], out, accent, bg_bottom, status))
        print(f"{p['repo']:26s} {status:4s} accent={accent} bgbot={bg_bottom} -> {out}")
    fails = [r for r in results if r[4] != "OK"]
    print(f"\n{len(results) - len(fails)}/{len(results)} 生成成功")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
