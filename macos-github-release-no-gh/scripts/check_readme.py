#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""README 格式自检（对齐样板仓库 SSHAppInstaller）。

用途：
    发布前校验 README.md 是否严格符合「模板 V3.1」的排版口径，避免人工目测漏项。
    判定项覆盖：居中头部五件套、两行八徽章（含第二行顺序）、简介 blockquote 写法、
    中英镜像章节顺序、功能表格、隐私条款、许可证段落，以及占位符残留 / 本地路径 /
    令牌 / 真实邮箱等泄漏。

调用时机：
    生成或改写 README.md 之后、git commit 之前跑一次；
    退出码 0 = 全绿可发布，1 = 有 error 必须先修。

用法：
    python3 scripts/check_readme.py README.md
    python3 scripts/check_readme.py README.md --strict-files   # 图标/LICENSE 缺失也算 error
"""
import argparse
import os
import re
import sys

# ---------------------------------------------------------------------------
# 常量：样板仓库口径
# ---------------------------------------------------------------------------
ROW1 = ["platform", "arch", "engine", "license"]
# 第二行顺序是固定口径（样板仓库实测顺序），调换即报错
ROW2 = ["network", "released", "last-commit", "release"]

CN_SUBS = ["主要功能", "快速开始", "macOS 版本选择", "支持的功能", "差异化亮点", "已知限制"]
EN_SUBS = ["Highlights", "Quick start", "Choose a macOS build", "Supported features",
           "Why this tool", "Known limitations"]
TOP_SECTIONS = ["## 中文", "## English", "## 隐私与安全", "## 许可证", "## 支持"]

# 泄漏特征：命中即 error
LEAK_PATTERNS = [
    (r"/Users/[A-Za-z0-9_.-]+", "本机绝对路径 /Users/<用户名>"),
    (r"/home/[A-Za-z0-9_.-]+", "本机绝对路径 /home/<用户名>"),
    (r"ghp_[A-Za-z0-9]{10,}", "GitHub 个人访问令牌"),
    (r"github_pat_[A-Za-z0-9_]{10,}", "GitHub fine-grained 令牌"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "私钥内容"),
    (r"\b[A-Za-z0-9._%+-]+@(?!users\.noreply\.github\.com)[A-Za-z0-9.-]+\.(?:com|cn|net|org|io|me)\b",
     "真实邮箱（应使用 GitHub noreply 邮箱）"),
]

# 占位符残留：命中即 error
PLACEHOLDER_PATTERNS = [
    (r"\{\{", "未替换的 {{占位符}}"),
    (r"\{(?:软件英文名|软件中文名|GitHub用户名|GitHub仓库地址|最低macOS版本|发布日期|版本|年份|架构|"
     r"中文一句话简介|English one-liner|emoji|类别|项目|Category|item|description)\}",
     "未替换的 {中文占位符}"),
]


class Report:
    """收集检查结果：error 阻断发布，warn 只提示。"""

    def __init__(self):
        self.errors = []
        self.warns = []
        self.passes = []

    def err(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warns.append(msg)

    def ok(self, msg):
        self.passes.append(msg)


def badge_labels(block):
    """按出现顺序抽出 shields 徽章的语义标签，用于校验两行八徽章。"""
    labels = []
    for src in re.findall(r'<img[^>]+src="([^"]+)"', block):
        if "img.shields.io/badge/network-" in src:
            labels.append("network")
        elif "img.shields.io/badge/released-" in src:
            labels.append("released")
        elif "github/last-commit" in src:
            labels.append("last-commit")
        elif "github/v/release" in src:
            labels.append("release")
        elif "img.shields.io/badge/platform-" in src:
            labels.append("platform")
        elif "img.shields.io/badge/arch-" in src:
            labels.append("arch")
        elif "img.shields.io/badge/engine-" in src:
            labels.append("engine")
        elif "img.shields.io/badge/license-" in src:
            labels.append("license")
        elif "img.shields.io/badge/" in src:
            labels.append("other")
    return labels


def p_blocks(lines):
    """返回所有 <p ...> ... </p> 区块的 (起始行号, 文本)。"""
    out, buf, start = [], [], None
    for i, line in enumerate(lines):
        if start is None and "<p" in line:
            start = i
            buf = [line]
            if "</p>" in line:
                out.append((start, "\n".join(buf)))
                start = None
        elif start is not None:
            buf.append(line)
            if "</p>" in line:
                out.append((start, "\n".join(buf)))
                start = None
    return out


def find_heading(lines, prefix):
    """找第一个以 prefix 开头的标题行号，找不到返回 -1。"""
    for i, line in enumerate(lines):
        if line.strip().startswith(prefix):
            return i
    return -1


def strip_code(text):
    """去掉围栏代码块与行内代码 span。

    用途：占位符检查只针对「正文里忘了替换的内容」。
    样板 README 的命名格式说明里本来就会写 `支持最低版本-{软件英文名}-版本-架构`
    这种带花括号的字面量，不剔掉必然误报。
    """
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", "", text)
    return text


def check(text, strict_files=False, base_dir="."):
    r = Report()
    lines = text.splitlines()
    prose = strip_code(text)   # 正文（已剔代码），用于占位符检查

    # ---- 1. 居中头部五件套 -------------------------------------------------
    blocks = p_blocks(lines)
    icon = next((b for _, b in blocks if "<img" in b and "shields.io" not in b), None)
    if icon and 'width="128"' in icon and "<p" in icon and 'align="center"' in icon:
        r.ok("① 居中图标（128px）")
        if 'alt="' not in icon:
            r.warn("图标 <img> 缺 alt 属性")
    else:
        r.err("① 缺居中图标块：应为 <p align=\"center\"><img src=\"app-icon.png\" width=\"128\" alt=\"...\"></p>")

    h1 = next((l for l in lines if l.strip().startswith("<h1")), "")
    if h1 and 'align="center"' in h1 and " / " in h1:
        r.ok("② 居中标题「英文名 / 中文名」")
    else:
        r.err("② 标题不合规：应为 <h1 align=\"center\">{英文名} / {中文名}</h1>（英文在左、中文在右）")

    if re.search(r"<b>中文</b>\s*\|\s*<a href=\"#english\">English</a>", text):
        r.ok("③ 语言锚点「中文 | English」")
    else:
        r.err("③ 缺语言锚点：应为 <b>中文</b> | <a href=\"#english\">English</a>")

    # ---- 2. 两行八徽章 -----------------------------------------------------
    badge_blocks = [b for _, b in blocks if "shields.io" in b]
    if len(badge_blocks) < 2:
        r.err(f"④ 徽章应分两行（两个 <p> 块），实际找到 {len(badge_blocks)} 个")
    else:
        got1 = badge_labels(badge_blocks[0])
        got2 = badge_labels(badge_blocks[1])
        if got1 == ROW1:
            r.ok("④ 徽章第一行顺序 platform → arch → engine → license")
        else:
            r.err(f"④ 徽章第一行应为 {ROW1}，实际 {got1}")
        if got2 == ROW2:
            r.ok("⑤ 徽章第二行顺序 network → released → last-commit → release")
        else:
            r.err(f"⑤ 徽章第二行应为 {ROW2}（顺序固定），实际 {got2}")
        if not re.search(r'<a href="[^"]*/releases/latest"><img[^>]*github/v/release', badge_blocks[1]):
            r.err("⑤b release 徽章须外包 <a href=\"{仓库}/releases/latest\">，可点击跳转")

    # ---- 3. 分隔线与下载/Issues 行 -----------------------------------------
    hr = next((i for i, l in enumerate(lines) if l.strip() == "---"), -1)
    if hr > 0:
        r.ok("⑥ 徽章后分隔线 ---")
        tail = "\n".join(lines[hr:hr + 14])
        if "下载最新版 / Download" in tail and "问题反馈 / Issues" in tail:
            r.ok("⑦ 居中「下载最新版 / 问题反馈」行")
        else:
            r.err("⑦ 分隔线后缺居中下载/Issues 行（文案：下载最新版 / Download · 问题反馈 / Issues）")
    else:
        r.err("⑥ 徽章后缺分隔线 ---")

    # ---- 4. 简介 blockquote（V3.1：合并单行 + 作者行同块） ------------------
    intro_idx = next((i for i, l in enumerate(lines) if l.startswith(">") and " / " in l), -1)
    if intro_idx < 0:
        r.err("⑧ 简介 blockquote 缺失或未把中英文合并成一行（应为「> 中文 / English」）")
    else:
        r.ok("⑧ 简介 blockquote 中英合并单行")
        # 作者行必须在同一个 blockquote 内（中间只允许空 `>` 行，不允许空行断开）
        j, same_block, author_found = intro_idx + 1, True, False
        while j < len(lines):
            l = lines[j]
            if l.strip() == "":
                same_block = False          # 空行 = blockquote 断开
                j += 1
                continue
            if not l.startswith(">"):
                break
            if not same_block and "作者 Author" in l:
                break                       # 作者行落到了另一个 blockquote
            if "作者 Author" in l:
                author_found = True
                break
            j += 1
        if author_found:
            r.ok("⑨ 作者/许可证行与简介同块")
        else:
            r.err("⑨ 作者/许可证行须在简介同一个 blockquote 内（空 `>` 行分隔，不要用空行新起 blockquote）")

    # ---- 5. 顶层章节顺序 ---------------------------------------------------
    pos = []
    for sec in TOP_SECTIONS:
        idx = find_heading(lines, sec)
        if idx < 0:
            r.err(f"⑩ 缺章节「{sec}」")
        pos.append((sec, idx))
    valid = [(s, i) for s, i in pos if i >= 0]
    if len(valid) == len(TOP_SECTIONS) and all(valid[k][1] < valid[k + 1][1] for k in range(len(valid) - 1)):
        r.ok("⑩ 顶层章节顺序 中文 → English → 隐私 → 许可证 → 支持")
    elif len(valid) == len(TOP_SECTIONS):
        r.err("⑩ 顶层章节顺序不对，应为：" + " → ".join(s.replace("## ", "") for s in TOP_SECTIONS))

    # ---- 6. 中英镜像子章节 ------------------------------------------------
    cn_start = find_heading(lines, "## 中文")
    en_start = find_heading(lines, "## English")
    cn_txt = "\n".join(lines[cn_start:en_start]) if cn_start >= 0 and en_start > cn_start else ""
    en_txt = "\n".join(lines[en_start:]) if en_start >= 0 else ""

    def sub_order(body, subs, tag):
        idxs = [find_heading(body.splitlines(), "### " + s) for s in subs]
        found = [s for s, i in zip(subs, idxs) if i >= 0]
        if len(found) == len(subs) and idxs == sorted(idxs):
            r.ok(f"⑪ {tag} 六节齐全且顺序正确")
        else:
            miss = [s for s, i in zip(subs, idxs) if i < 0]
            if miss:
                r.err(f"⑪ {tag} 缺子章节：{', '.join(miss)}")
            else:
                r.err(f"⑪ {tag} 子章节顺序不对（应按 {' → '.join(subs)}）")

    sub_order(cn_txt, CN_SUBS, "中文")
    sub_order(en_txt, EN_SUBS, "English")

    # ---- 7. 平台说明 / 功能表格 / 隐私 / 许可证 / 支持 ----------------------
    if "平台说明 Platform Note" in text:
        r.ok("⑫ 平台说明（Platform Note）")
    else:
        r.err("⑫ 缺「平台说明 Platform Note」blockquote")
    if re.search(r"\|\s*类别\s*\|", text) and re.search(r"\|\s*说明\s*\|", text):
        r.ok("⑬ 中文功能表格（类别 / 项目 / 说明）")
    else:
        r.err("⑬ 缺中文功能表格，表头应为 | 类别 | 项目 | 说明 |")
    if re.search(r"\|\s*Category\s*\|", text) and re.search(r"\|\s*Description\s*\|", text):
        r.ok("⑭ 英文功能表格（Category / Item / Description）")
    else:
        r.err("⑭ 缺英文功能表格，表头应为 | Category | Item | Description |")

    priv = re.search(r"## 隐私与安全.*?(?=\n## )", text, re.S)
    if priv and len(re.findall(r"^- ", priv.group(0), re.M)) >= 3:
        r.ok("⑮ 隐私与安全 3 条")
    else:
        r.err("⑮ 「隐私与安全」应为 3 条 bullet（本地运行 / 权限透明 / 未公证提醒）")

    if "**MIT License**" in text and "版权归" in text:
        r.ok("⑯ 许可证段落（MIT + 版权归属）")
    else:
        r.err("⑯ 缺许可证段落：> **MIT License** — 版权归 **banqiu** 所有（年份）")

    if re.search(r"Star", text):
        r.ok("⑰ 支持段落（Star / PR 邀请）")
    else:
        r.warn("⑰ 支持段落未见 Star 邀请语")

    # ---- 8. 泄漏与残留 -----------------------------------------------------
    for pat, desc in LEAK_PATTERNS:
        for m in re.finditer(pat, text):
            r.err(f"⑱ 疑似泄漏（{desc}）：{m.group(0)}")
    for pat, desc in PLACEHOLDER_PATTERNS:
        if re.search(pat, prose):
            r.err(f"⑲ {desc}")
    if "<!--" in text:
        r.err("⑳ 残留 HTML 注释 <!-- -->（模板填写提示未删除）")

    # ---- 9. 徽章转义 -------------------------------------------------------
    for src in re.findall(r'https://img\.shields\.io/badge/[^"\s]+', text):
        value = src.split("/badge/", 1)[1].rsplit("-", 1)[0]
        if " " in value:
            r.warn(f"㉑ 徽章值含裸空格（应写 %20）：{src}")
        if "|" in value:
            r.err(f"㉑ 徽章值含裸竖线（应写 %7C）：{src}")
        if "+" in value:
            r.warn(f"㉑ 徽章值含裸加号（应写 %2B）：{src}")

    # ---- 10. 配套文件 ------------------------------------------------------
    lvl = r.err if strict_files else r.warn
    icon_src = ""
    if icon:
        m = re.search(r'<img[^>]+src="([^"]+)"', icon)
        icon_src = m.group(1) if m else ""
    if icon_src and not icon_src.startswith("http"):
        if not os.path.exists(os.path.join(base_dir, icon_src)):
            lvl(f"㉒ 图标文件不存在：{os.path.join(base_dir, icon_src)}（README 头部会破图）")
        else:
            r.ok("㉒ 图标文件在仓库内")
    if not os.path.exists(os.path.join(base_dir, "LICENSE")):
        lvl("㉓ 缺 LICENSE 文件（README 引用了它）")
    else:
        r.ok("㉓ LICENSE 存在")
    gi = os.path.join(base_dir, ".gitignore")
    if os.path.exists(gi):
        body = open(gi, encoding="utf-8", errors="ignore").read()
        if "*.dmg" not in body:
            r.warn("㉔ .gitignore 未排除 *.dmg（包体不应入库）")
        elif "app-icon.png" in body:
            r.err("㉔ .gitignore 排除了 app-icon.png —— README 头部必须引用它，会破图")
        else:
            r.ok("㉔ .gitignore 正确（排除 dmg、保留图标）")
    else:
        r.warn("㉔ 无 .gitignore")
    return r


def main():
    ap = argparse.ArgumentParser(description="README 格式自检（对齐样板仓库 SSHAppInstaller）")
    ap.add_argument("readme", nargs="?", default="README.md", help="README 路径，默认 ./README.md")
    ap.add_argument("--strict-files", action="store_true", help="图标/LICENSE 缺失也算 error")
    args = ap.parse_args()

    path = args.readme
    if not os.path.isfile(path):
        print(f"❌ 文件不存在：{path}")
        return 1

    text = open(path, encoding="utf-8").read()
    r = check(text, strict_files=args.strict_files, base_dir=os.path.dirname(path) or ".")

    for m in r.passes:
        print(f"  ✅ {m}")
    for m in r.warns:
        print(f"  ⚠️  {m}")
    for m in r.errors:
        print(f"  ❌ {m}")

    print("-" * 62)
    print(f"通过 {len(r.passes)} 项 / 警告 {len(r.warns)} 项 / 错误 {len(r.errors)} 项")
    if r.errors:
        print("❌ 未达发布标准：先修上面的 error 再 commit。")
        return 1
    print("✅ README 符合模板 V3.1（样板仓库 SSHAppInstaller）格式。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
