#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_starry.py — 校验 starry 转换产物
- 所有 NEXT/SELECT 跳转目标 label 存在（同章 chunk 内 / 跨章目标 chunk 内）
- gameend 目标合法
- 节点结构（类型 0-10、字段长度）合法
- 剧本引用的 bg/ch/ev 资源文件存在
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCN = os.path.join(ROOT, "src", "common", "scn")
GAME = os.path.join(ROOT, "src", "common", "game.txt")
BG = os.path.join(ROOT, "src", "common", "bg")
CH = os.path.join(ROOT, "src", "common", "ch")
EV = os.path.join(ROOT, "src", "common", "ev")

TYPE_NAMES = {0: "LABEL", 1: "CHAPTER", 2: "BG", 3: "TEXT", 4: "SELECT",
              5: "EV", 6: "NEXT", 7: "CHAR", 8: "MUSIC", 9: "FX", 10: "VAR"}

def load_chunks():
    chunks = {}
    for f in sorted(os.listdir(SCN)):
        if not f.endswith(".txt"):
            continue
        sid = f[5:8] if f.startswith("chunk") else f[:-4]
        with open(os.path.join(SCN, f), encoding="utf-8") as fh:
            chunks[sid] = json.load(fh)
    return chunks

def labels_of(chunk):
    return {n[1] for n in chunk if n[0] == 0}

def main():
    game = json.load(open(GAME, encoding="utf-8"))
    chunks = load_chunks()
    errors = []
    warnings = []

    # 1. game.txt scenarios 与 chunk 文件对应
    main_scn = game["scenarios"]["main"]
    for s in main_scn:
        sid, path = s["id"], s["path"]
        if sid not in chunks:
            errors.append(f"scenario {sid} 缺少 chunk")
        # path 应为 chunk{sid}.txt
        if path != f"chunk{sid}.txt":
            warnings.append(f"scenario {sid} path 不一致: {path}")

    # 2. 逐 chunk 校验节点与跳转
    total_nodes = 0
    for sid, chunk in chunks.items():
        labels = labels_of(chunk)
        total_nodes += len(chunk)
        for i, n in enumerate(chunk):
            if not isinstance(n, list) or not n:
                errors.append(f"{sid}[{i}] 非法节点: {n!r}")
                continue
            t = n[0]
            if t not in TYPE_NAMES:
                errors.append(f"{sid}[{i}] 未知类型 {t}")
                continue
            if t == 6:  # NEXT
                target = str(n[1] if len(n) > 1 else "")
                if "@" in target:
                    scn_id, lab = target.split("@", 1)
                    if scn_id not in chunks:
                        errors.append(f"{sid}[{i}] 跨章跳转目标场景不存在: {target}")
                    elif lab not in labels_of(chunks[scn_id]):
                        errors.append(f"{sid}[{i}] 跨章跳转 label 不存在: {target}")
                elif "gameend" in target.lower() or "endrecollection" in target.lower():
                    pass  # 合法结束标记
                elif target not in labels:
                    errors.append(f"{sid}[{i}] 同章跳转 label 不存在: {target}")
            elif t == 4:  # SELECT
                for j, opt in enumerate(n[1]):
                    if not isinstance(opt, list) or len(opt) < 2:
                        errors.append(f"{sid}[{i}] 选项 {j} 格式错误: {opt!r}")
                        continue
                    target = str(opt[1])
                    if "@" in target:
                        scn_id, lab = target.split("@", 1)
                        if scn_id not in chunks:
                            errors.append(f"{sid}[{i}] 选项跨章目标场景不存在: {target}")
                        elif lab not in labels_of(chunks[scn_id]):
                            errors.append(f"{sid}[{i}] 选项跨章 label 不存在: {target}")
                    elif target not in labels:
                        errors.append(f"{sid}[{i}] 选项同章 label 不存在: {target}")
            elif t in (2, 5):  # BG / EV 资源
                name = str(n[1] if len(n) > 1 else "")
                base = BG if t == 2 else EV
                if name and not os.path.exists(os.path.join(base, name + ".png")):
                    errors.append(f"{sid}[{i}] 背景/事件图缺失: {name}")
            elif t == 7:  # CHAR
                name = str(n[1] if len(n) > 1 else "")
                if name and not os.path.exists(os.path.join(CH, name + ".png")):
                    errors.append(f"{sid}[{i}] 立绘缺失: {name}")

    # 3. 资源目录统计
    nbg = len(os.listdir(BG)); nch = len(os.listdir(CH)); nev = len(os.listdir(EV))
    print(f"chunk 数: {len(chunks)}  节点总数: {total_nodes}")
    print(f"资源: bg={nbg} ch={nch} ev={nev}")
    print(f"跳转/label 校验: {'PASS' if not errors else 'FAIL'}")
    for e in errors[:40]:
        print("  ERR", e)
    for w in warnings[:10]:
        print("  WARN", w)
    if errors:
        print(f"共 {len(errors)} 个错误")
        sys.exit(1)
    print("校验通过")

if __name__ == "__main__":
    main()
