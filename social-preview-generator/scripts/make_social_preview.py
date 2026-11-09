#!/usr/bin/env python3
"""make_social_preview.py — 参数化生成 GitHub 社交预览图 (1280x640)

风格复刻自 AppScheduler 的 social-preview：深色渐变背景 + 左图标 + 右文字块
(大标题 + 蓝色短下划线 + 副标题 + 浅色标语 + 描边胶囊标签)。

用法示例：
  python3 make_social_preview.py \
      --name ScrcpyGUI \
      --subtitle "安卓投屏 · 零依赖开箱即用" \
      --tagline "macOS 原生 · USB / 无线投屏 · 内置 scrcpy 4.1 引擎" \
      --tags "USB 投屏,无线配对,老机型模式" \
      --icon AppIcon.png \
      --accent "#7c52d9" \
      --bg-top "#0f0c1d" --bg-bottom "#2a1e52" \
      --output social-preview.png
"""
import argparse
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 640

PINGFANG_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
]
HELVETICA_CANDIDATES = [
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/Library/Fonts/Helvetica Neue.ttc",
]


def load_font(candidates, size, index=0):
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size, index=index)
            except Exception:
                continue
    return ImageFont.load_default()


def chinese_font(size):
    return load_font(PINGFANG_CANDIDATES, size)


def latin_font(size, thin=False):
    # HelveticaNeue.ttc: 0=Regular 5=UltraLight 7=Light
    # thin=True 返回 Light(7)——UltraLight(5) 在 1280 宽成品上过细，已弃用为默认
    for path in HELVETICA_CANDIDATES:
        if not os.path.exists(path):
            continue
        for idx in ([7, 5, 0] if thin else [0]):
            try:
                return ImageFont.truetype(path, size, index=idx)
            except Exception:
                continue
    return load_font(HELVETICA_CANDIDATES, size)


def hex_rgb(s):
    s = s.strip().lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def make_bg(top, bottom):
    base = Image.new("RGB", (W, H), top)
    px = base.load()
    for y in range(H):
        t = y / (H - 1)
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        for x in range(W):
            px[x, y] = (r, g, b)
    return base


def text_w(draw, text, font):
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def draw_pill(draw, x, y, label, font, accent, text_color, pad_x=26, pad_y=13, stroke=2):
    tw, th = text_w(draw, label, font)
    asc, desc = font.getmetrics()
    line_h = asc + desc
    w = tw + pad_x * 2
    h = line_h + pad_y * 2 - 6
    draw.rounded_rectangle(
        [x, y, x + w, y + h], radius=h // 2,
        outline=accent, width=stroke,
    )
    draw.text((x + pad_x, y + (h - line_h) // 2 - 2), label, font=font, fill=text_color)
    return w, h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="ScrcpyGUI")
    ap.add_argument("--subtitle", default="安卓投屏 · 零依赖开箱即用")
    ap.add_argument("--tagline", default="macOS 原生 · USB / 无线投屏 · 内置 scrcpy 4.1 引擎")
    ap.add_argument("--tags", default="USB 投屏,无线配对,老机型模式")
    ap.add_argument("--icon", default="AppIcon.png")
    ap.add_argument("--accent", default="#7c52d9")
    ap.add_argument("--bg-top", default="#0f0c1d")
    ap.add_argument("--bg-bottom", default="#2a1e52")
    ap.add_argument("--title-color", default="#ffffff")
    ap.add_argument("--sub-color", default="#f0edfa")
    ap.add_argument("--tag-color", default="#b9a7e8")
    ap.add_argument("--icon-size", type=int, default=320)
    ap.add_argument("--icon-x", type=int, default=95)
    ap.add_argument("--text-x", type=int, default=460)
    ap.add_argument("--output", default="social-preview.png")
    args = ap.parse_args()

    accent = hex_rgb(args.accent)
    bg_top = hex_rgb(args.bg_top)
    bg_bottom = hex_rgb(args.bg_bottom)
    title_c = hex_rgb(args.title_color)
    sub_c = hex_rgb(args.sub_color)
    tag_c = hex_rgb(args.tag_color)

    img = make_bg(bg_top, bg_bottom).convert("RGBA")
    draw = ImageDraw.Draw(img)

    # 字体（长标题自动缩小：标题可用宽度 = 画布 - 文字起点 - 40 边距）
    avail = W - args.text_x - 40
    t_size = 78
    while t_size > 40:
        f_try = latin_font(t_size, thin=True)
        tw_try, _ = text_w(draw, args.name, f_try)
        if tw_try <= avail:
            break
        t_size -= 4
    f_title = latin_font(t_size, thin=True)
    f_sub = chinese_font(38)
    if text_w(draw, args.subtitle, f_sub)[0] > avail:
        f_sub = chinese_font(32)
    f_tag = chinese_font(29)
    if text_w(draw, args.tagline, f_tag)[0] > avail:
        f_tag = chinese_font(25)
    f_pill = chinese_font(26)

    # 图标（居左垂直居中）
    icon = Image.open(args.icon).convert("RGBA").resize(
        (args.icon_size, args.icon_size), Image.LANCZOS)
    icon_y = (H - args.icon_size) // 2
    img.alpha_composite(icon, (args.icon_x, icon_y))

    # 逐行排版，整块垂直居中
    underline_h = 5
    underline_gap = 10
    gap1, gap2, gap3 = 26, 18, 30
    title_w, _ = text_w(draw, args.name, f_title)
    _tb = draw.textbbox((0, 0), args.name, font=f_title)
    title_h = _tb[3]  # 含顶部留白的字形深度，保证居中计算与下划线定位一致
    sub_w, sub_h = text_w(draw, args.subtitle, f_sub)
    tag_w, tag_h = text_w(draw, args.tagline, f_tag)
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    asc, desc = f_pill.getmetrics()
    pill_h = asc + desc + 26 - 6

    block_h = title_h + underline_h + underline_gap + gap1 + sub_h + gap2 + tag_h + gap3 + pill_h
    y = (H - block_h) // 2 - 10
    x = args.text_x

    # 标题 + 短下划线（约标题宽 1/4）
    # 下划线定位必须用「实际绘制位置」的字形包围盒底边，否则细字重顶部留白大会压住字母
    draw.text((x, y), args.name, font=f_title, fill=title_c)
    bb = draw.textbbox((x, y), args.name, font=f_title)
    y = bb[3] + underline_gap
    uw = max(90, (bb[2] - bb[0]) // 4)
    draw.rectangle([x + 2, y, x + 2 + uw, y + underline_h], fill=accent)
    y += underline_h + gap1

    # 副标题 / 标语
    draw.text((x, y), args.subtitle, font=f_sub, fill=sub_c)
    y += sub_h + gap2
    draw.text((x, y), args.tagline, font=f_tag, fill=tag_c)
    y += tag_h + gap3

    # 胶囊
    px = x
    for label in tags:
        pw, ph = draw_pill(draw, px, y, label, f_pill, accent, tag_c)
        px += pw + 18

    img.convert("RGB").save(args.output, "PNG")
    print(f"OK -> {args.output} ({W}x{H})")


if __name__ == "__main__":
    main()
