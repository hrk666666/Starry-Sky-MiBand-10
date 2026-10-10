#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert_starry.py — 《星空列车与白的旅行》starry-rw5 内容包 → Sanoba VN 引擎 v1.1 内容包转换器

输入：
  - starry-rw5 仓库的 src/common/story/1.txt … 17.txt（JSON 节点数组，op 格式）
  - starry-rw5 仓库的 src/common/images/（背景 / 立绘 / 事件图）

输出（写入本项目 src/）：
  - src/common/scn/chunk001.txt … chunk017.txt   剧本（节点 v1.1，JSON 数组）
  - src/common/game.txt                          内容包配置
  - src/common/bg/ src/common/ch/ src/common/ev/ 资源（按引用分类复制）

节点映射：
  - background(event=false)  → 节点 2（bg 目录）
  - background(event=true)   → 节点 5（ev 目录，全屏事件图）
  - restoreBackground        → 节点 2（恢复最近非 event 背景，转换期静态模拟）
  - body(image!="")          → 节点 7 立绘 center/change
  - body(image="")           → 节点 7 立绘 center/fadeout（清空）
  - text                     → 节点 3 对白
  - choice                   → 节点 4 选项（目标行插入 label）
  - jump                     → 节点 6（同章 label / 跨章 scnId@label）
  - end                      → 节点 6 跳 gameend_starry（引擎统一结束处理）
"""

import glob
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STARRY = os.path.abspath(os.path.join(ROOT, "..", "starry-rw5"))

STORY_DIR = os.path.join(STARRY, "src", "common", "story")
IMG_DIR = os.path.join(STARRY, "src", "common", "images")

OUT_SCN = os.path.join(ROOT, "src", "common", "scn")
OUT_BG = os.path.join(ROOT, "src", "common", "bg")
OUT_CH = os.path.join(ROOT, "src", "common", "ch")
OUT_EV = os.path.join(ROOT, "src", "common", "ev")
OUT_GAME = os.path.join(ROOT, "src", "common", "game.txt")

CHAPTERS = 17

# 该内容包不携带音频资源（上游 rw5 版即无声）
MUSIC = False

def load_chapters():
    """读取 1..17.txt 为 dict {章号: 节点数组}"""
    chapters = {}
    for ch in range(1, CHAPTERS + 1):
        p = os.path.join(STORY_DIR, f"{ch}.txt")
        with open(p, encoding="utf-8") as f:
            chapters[ch] = json.load(f)
    return chapters

def collect_targets(chapters):
    """收集所有 jump/choice 的目标 [章, 行]"""
    targets = set()
    for ch, data in chapters.items():
        for i, node in enumerate(data):
            op = node.get("op")
            if op == "jump":
                targets.add(tuple(node["to"]))
            elif op == "choice":
                for item in node.get("items", []):
                    targets.add(tuple(item["to"]))
    return targets

def label_name(ch, line):
    """生成 label 名：s{章}_{行}"""
    return f"s{ch}_{line}"

def jump_target(ch, line, cur_ch=None):
    """生成节点 6 的跳转目标：同章 label，跨章 scnId@label"""
    if cur_ch is None or ch == cur_ch:
        return label_name(ch, line)
    return f"{ch:03d}@{label_name(ch, line)}"

def convert_chapter(ch, data, targets):
    """单章转换，返回节点数组 + 引用的资源 set"""
    out = []
    refs = {"bg": set(), "ch": set(), "ev": set()}
    regular_bg = None   # 最近非 event 背景（restoreBackground 恢复目标）
    cur_bg = None       # 当前画面

    for i, node in enumerate(data):
        op = node.get("op")
        # 目标行：先插 label
        if (ch, i) in targets:
            out.append([0, label_name(ch, i)])

        if op == "background":
            img = node["image"]
            event = node.get("event", False)
            if event:
                # 全屏事件图（evcg*/aban*/large_evcg*）
                out.append([5, img])
                refs["ev"].add(img)
                cur_bg = img
            else:
                out.append([2, img])
                refs["bg"].add(img)
                cur_bg = img
                regular_bg = img
            if node.get("clearBody"):
                out.append([7, "", "center", "fadeout"])
        elif op == "restoreBackground":
            # 恢复最近非 event 背景（starry 的 regularBackground 语义）
            if regular_bg is not None:
                out.append([2, regular_bg])
                cur_bg = regular_bg
            # 无 regular 背景时静默（首个节点前 restore 无意义）
        elif op == "body":
            img = node.get("image", "")
            if img:
                out.append([7, img, "center", "change"])
                refs["ch"].add(img)
            else:
                out.append([7, "", "center", "fadeout"])
        elif op == "text":
            out.append([3, node.get("speaker", "") or "", node.get("text", "") or ""])
        elif op == "choice":
            items = []
            for item in node.get("items", []):
                tch, tline = item["to"]
                items.append([item["text"], jump_target(tch, tline, ch)])
            out.append([4, items])
        elif op == "jump":
            tch, tline = node["to"]
            out.append([6, jump_target(tch, tline, ch)])
        elif op == "end":
            out.append([6, "gameend_starry"])
        else:
            print(f"WARN 未知 op: {op} @ {ch}.txt:{i}")
    return out, refs

def write_resources(refs):
    """按引用复制资源：body→ch/，background→bg/，event→ev/"""
    import shutil
    missing = []
    for kind, names in refs.items():
        out_dir = {"bg": OUT_BG, "ch": OUT_CH, "ev": OUT_EV}[kind]
        os.makedirs(out_dir, exist_ok=True)
        for name in sorted(names):
            src = os.path.join(IMG_DIR, name + ".png")
            if not os.path.exists(src):
                missing.append(f"{kind}/{name}")
                continue
            shutil.copy2(src, os.path.join(out_dir, name + ".png"))
    if missing:
        print("WARN 缺失资源:", missing)

def write_game_txt():
    game = {
        "id": "starry-sky",
        "title": "星空列车与白的旅行",
        "version": "1.0.0",
        "engine": {"format": "vn-1.1", "minRuntime": "1.0"},
        "initialState": {"flags": {}},
        "resources": {
            "base": "/common",
            "dirs": {"bg": "bg", "sd": "sd", "ev": "ev", "ch": "ch", "audio": "audio"},
        },
        "scenarios": {"main": []},
        "routes": {},
    }
    for ch in range(1, CHAPTERS + 1):
        game["scenarios"]["main"].append({
            "id": f"{ch:03d}",
            "path": f"chunk{ch:03d}.txt",
        })
    with open(OUT_GAME, "w", encoding="utf-8") as f:
        json.dump(game, f, ensure_ascii=False, indent=2)

def main():
    os.makedirs(OUT_SCN, exist_ok=True)
    chapters = load_chapters()
    targets = collect_targets(chapters)
    print(f"章节: {len(chapters)}  target行数: {len(targets)}")

    all_refs = {"bg": set(), "ch": set(), "ev": set()}
    stats = {}
    for ch in range(1, CHAPTERS + 1):
        data = chapters[ch]
        out, refs = convert_chapter(ch, data, targets)
        for k in all_refs:
            all_refs[k] |= refs[k]
        p = os.path.join(OUT_SCN, f"chunk{ch:03d}.txt")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False)
        stats[ch] = len(out)
        print(f"chunk{ch:03d}: {len(data)} 源节点 → {len(out)} 引擎节点")

    write_resources(all_refs)
    write_game_txt()
    print("资源引用: bg=%d ch=%d ev=%d" % (len(all_refs["bg"]), len(all_refs["ch"]), len(all_refs["ev"])))
    print("完成")

if __name__ == "__main__":
    main()
