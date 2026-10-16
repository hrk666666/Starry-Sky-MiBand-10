#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
align_resources.py — 资源对齐到 hrk 引擎项目规格（v2 裁剪版）
  - bg / ev / title_bg : 源横图 432×243 → 旋转 90° → 243×432 → 放大到 336 宽
                         → 居中裁剪 336×480 JPEG（纯裁剪，无渐变补全）
  - ch（立绘）        : 保持现有裁剪尺寸（212×286 等）JPEG
压缩：bg/ev/title_bg quality 70，ch 保持现有文件不动
"""
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMON = os.path.join(ROOT, "src", "common")
SRC_IMG = os.path.abspath(os.path.join(ROOT, "..", "starry-rw5", "src", "common", "images"))
TARGET = (336, 480)

def rotate_crop_336x480(name, out_path, quality=70):
    """源横图 432×243 → 旋转90° → 放大到 336 宽 → 居中裁 336×480"""
    src = os.path.join(SRC_IMG, name + ".png")
    if not os.path.exists(src):
        return False
    im = Image.open(src).convert("RGB")
    im = im.transpose(Image.ROTATE_90)          # 243×432
    scale = TARGET[0] / im.size[0]              # 336/243 ≈ 1.38
    im2 = im.resize((TARGET[0], int(round(im.size[1] * scale))), Image.LANCZOS)
    h2 = im2.size[1]                            # ≈ 597
    top = (h2 - TARGET[1]) // 2
    im2 = im2.crop((0, top, TARGET[0], top + TARGET[1]))
    im2.save(out_path, "JPEG", quality=quality, optimize=True)
    return True

def main():
    stats = {"bg": 0, "ev": 0, "title": 0}
    total = 0
    # bg
    for f in sorted(os.listdir(os.path.join(COMMON, "bg"))):
        if f.lower().endswith(".jpg"):
            name = os.path.splitext(f)[0]
            out = os.path.join(COMMON, "bg", f)
            if rotate_crop_336x480(name, out):
                stats["bg"] += 1
                total += os.path.getsize(out)
    # ev
    for f in sorted(os.listdir(os.path.join(COMMON, "ev"))):
        if f.lower().endswith(".jpg"):
            name = os.path.splitext(f)[0]
            out = os.path.join(COMMON, "ev", f)
            if rotate_crop_336x480(name, out):
                stats["ev"] += 1
                total += os.path.getsize(out)
    # title_bg（源在 starry-rw5/src/common/title_bg.png）
    tb_src = os.path.abspath(os.path.join(ROOT, "..", "starry-rw5", "src", "common", "title_bg.png"))
    tb_out = os.path.join(COMMON, "title_bg.jpg")
    if os.path.exists(tb_src) and os.path.exists(tb_out):
        im = Image.open(tb_src).convert("RGB").transpose(Image.ROTATE_90)
        scale = TARGET[0] / im.size[0]
        im2 = im.resize((TARGET[0], int(round(im.size[1] * scale))), Image.LANCZOS)
        top = (im2.size[1] - TARGET[1]) // 2
        im2 = im2.crop((0, top, TARGET[0], top + TARGET[1]))
        im2.save(tb_out, "JPEG", quality=70, optimize=True)
        stats["title"] = 1
        total += os.path.getsize(tb_out)
    # ch 计入总体积（文件不动）
    for f in os.listdir(os.path.join(COMMON, "ch")):
        if f.lower().endswith(".jpg"):
            total += os.path.getsize(os.path.join(COMMON, "ch", f))
    print("旋转+裁剪完成:", stats, "总体积", total // 1024, "KB")

if __name__ == "__main__":
    main()
