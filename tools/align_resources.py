#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
align_resources.py — 资源对齐到 hrk 引擎项目（魔女夜宴 1.3.5）规格：
  - bg / ev / title_bg : 336×480 JPEG（从现有 212×520 竖版放大居中裁剪）
  - ch（立绘）        : JPEG，保持现有尺寸（212×286 / 172×286 / 153×286）
  - images（UI）      : 保持 PNG（与引擎项目一致）
压缩：bg quality 65、ev 70、ch 80、title_bg 70
"""
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMON = os.path.join(ROOT, "src", "common")
TARGET = (336, 480)

def to_jpeg_336x480(src_path, out_path, quality):
    """212×520 竖版 → 336×480 JPEG：同比例放大后居中裁剪中央区域"""
    im = Image.open(src_path).convert("RGB")
    w, h = im.size
    # 同比例放大到 336 宽（高度随之放大），再居中裁剪 336×480
    scale = TARGET[0] / w
    im2 = im.resize((TARGET[0], int(round(h * scale))), Image.LANCZOS)
    h2 = im2.size[1]
    if h2 >= TARGET[1]:
        top = (h2 - TARGET[1]) // 2
        box = (0, top, TARGET[0], top + TARGET[1])
        im2 = im2.crop(box)
    else:
        # 高度不足：顶部对齐，底部补黑（正常不会发生）
        canvas = Image.new("RGB", TARGET, (0, 0, 0))
        canvas.paste(im2, (0, 0))
        im2 = canvas
    im2.save(out_path, "JPEG", quality=quality, optimize=True)
    return os.path.getsize(out_path)

def to_jpeg_same(src_path, out_path, quality):
    """保持尺寸 PNG → JPEG"""
    im = Image.open(src_path).convert("RGB")
    im.save(out_path, "JPEG", quality=quality, optimize=True)
    return os.path.getsize(out_path)

def main():
    stats = {"bg": 0, "ev": 0, "ch": 0, "title": 0}
    # bg
    for f in sorted(os.listdir(os.path.join(COMMON, "bg"))):
        if f.lower().endswith(".png"):
            src = os.path.join(COMMON, "bg", f)
            out = os.path.join(COMMON, "bg", os.path.splitext(f)[0] + ".jpg")
            sz = to_jpeg_336x480(src, out, 65)
            os.remove(src)
            stats["bg"] += 1
    # ev
    for f in sorted(os.listdir(os.path.join(COMMON, "ev"))):
        if f.lower().endswith(".png"):
            src = os.path.join(COMMON, "ev", f)
            out = os.path.join(COMMON, "ev", os.path.splitext(f)[0] + ".jpg")
            sz = to_jpeg_336x480(src, out, 70)
            os.remove(src)
            stats["ev"] += 1
    # ch
    for f in sorted(os.listdir(os.path.join(COMMON, "ch"))):
        if f.lower().endswith(".png"):
            src = os.path.join(COMMON, "ch", f)
            out = os.path.join(COMMON, "ch", os.path.splitext(f)[0] + ".jpg")
            sz = to_jpeg_same(src, out, 80)
            os.remove(src)
            stats["ch"] += 1
    # title_bg
    tb_png = os.path.join(COMMON, "title_bg.png")
    if os.path.exists(tb_png):
        sz = to_jpeg_336x480(tb_png, os.path.join(COMMON, "title_bg.jpg"), 70)
        os.remove(tb_png)
        stats["title"] = 1
    # 汇总体积
    total = 0
    for sub in ("bg", "ev", "ch"):
        for f in os.listdir(os.path.join(COMMON, sub)):
            p = os.path.join(COMMON, sub, f)
            if f.lower().endswith((".jpg", ".png")):
                total += os.path.getsize(p)
    tb = os.path.join(COMMON, "title_bg.jpg")
    if os.path.exists(tb):
        total += os.path.getsize(tb)
    print("转换完成:", stats, "总体积", total // 1024, "KB")

if __name__ == "__main__":
    main()
