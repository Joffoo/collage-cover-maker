#!/usr/bin/env python3
"""封面装配：build（layers.json → cover.html）/ edit（本地编辑器）/ render（出图 + 验收）。

layers.json 是唯一真相源；cover.html、编辑器、PNG 都由它生成。

用法（在项目目录 _inbox/<slug>_assets/ 下）：
  python cover.py build
  python cover.py edit  [--port 8765]
  python cover.py render [--mockup mockup.png]
"""
import argparse
import base64
import http.server
import json
import mimetypes
import os
import sys
import threading
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
FORMATS = json.load(open(os.path.join(HERE, "formats.json"), encoding="utf-8"))
OUT_NAME = {"wechat": "cover_2115x900.png", "wide": "cover_1920x1080.png", "xhs": "cover_1440x1920.png"}


def load_layers(root):
    path = os.path.join(root, "layers.json")
    if not os.path.exists(path):
        sys.exit(f"FAIL: {path} 不存在")
    return json.load(open(path, encoding="utf-8-sig"))


def build(root):
    layers = load_layers(root)
    assets = {}
    for l in layers.get("layers", []):
        src = l.get("src")
        if src and l.get("kind") != "tape":
            p = os.path.join(root, src)
            if os.path.exists(p):
                mime = "image/svg+xml" if p.lower().endswith(".svg") else (mimetypes.guess_type(p)[0] or "image/png")
                assets[src] = f"data:{mime};base64," + base64.b64encode(open(p, "rb").read()).decode("ascii")
    font_path = os.path.join(HERE, "SmileySans-Oblique.woff2")
    if os.path.exists(font_path):
        smiley_font = "data:font/woff2;base64," + base64.b64encode(open(font_path, "rb").read()).decode("ascii")
    else:
        smiley_font = "https://cdn.jsdelivr.net/npm/smiley-sans@2.0.1/SmileySans-Oblique.ttf.woff2"
    html = open(os.path.join(HERE, "cover.template.html"), encoding="utf-8").read()
    html = (html
            .replace("/*LAYERS*/", json.dumps(layers, ensure_ascii=False))
            .replace("/*FORMATS*/", json.dumps(FORMATS))
            .replace("/*ASSETS*/", json.dumps(assets, ensure_ascii=False))
            .replace("/*SMILEY_FONT*/", smiley_font))
    open(os.path.join(root, "cover.html"), "w", encoding="utf-8").write(html)
    return layers


def cmd_edit(a):
    root = os.path.abspath(a.root)
    build(root)

    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(s, *args, **kw):
            super().__init__(*args, directory=root, **kw)

        def do_POST(s):
            if s.path != "/save":
                s.send_error(404)
                return
            body = s.rfile.read(int(s.headers["Content-Length"]))
            json.loads(body)
            tmp = os.path.join(root, "layers.json.tmp")
            open(tmp, "wb").write(body)
            os.replace(tmp, os.path.join(root, "layers.json"))
            s.send_response(204)
            s.end_headers()

        def log_message(s, *args):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", a.port), H)
    url = f"http://127.0.0.1:{a.port}/cover.html"
    print(f"编辑器 {url}  （Ctrl+S 写回 layers.json；Ctrl+C 退出）")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


# ---------------------------------------------------------------- 验收

def check_layers(root, layers):
    import cv2
    import numpy as np
    errs = []
    L = layers["layers"]
    ids = [l["id"] for l in L]
    if len(ids) != len(set(ids)):
        errs.append("图层 id 重复")
    roles = [l.get("role") for l in L]
    if roles.count("subject") != 1:
        errs.append(f"role=subject 必须恰好 1 个（现 {roles.count('subject')}）")
    if roles.count("title") != 1:
        errs.append(f"role=title 必须恰好 1 个（现 {roles.count('title')}）")
    if roles.count("subtitle") > 1:
        errs.append("subtitle 至多 1 个")
    if len({l["z"] for l in L}) < 4:
        errs.append("z 层级少于 4 档，缺少前后穿插")
    for l in L:
        if l.get("kind") == "tape":
            continue
        src = os.path.join(root, l.get("src", ""))
        if not os.path.exists(src):
            errs.append(f"{l['id']}: 文件缺失 {l.get('src')}")
            continue
        o = l.get("origin")
        if o == "gen":
            if not src.lower().endswith(".svg"):
                errs.append(f"{l['id']}: origin=gen 必须是 .svg（先 make_part.py gen 或从 assets/kit 复制）")
            else:
                import re
                svg_txt = open(src, encoding="utf-8", errors="ignore").read()
                cmds = re.findall(r"[MLCQZmlcqz]", svg_txt)
                if len(cmds) < 25:
                    errs.append(f"{l['id']}: SVG 路径节点过少（仅 {len(cmds)} 个），禁止使用简笔画几何形状，请使用 assets/kit/ 母版或 vtracer 矢量化")
        elif o == "real":
            img = cv2.imdecode(np.fromfile(src, np.uint8), cv2.IMREAD_UNCHANGED)
            if img is None or img.ndim < 3 or img.shape[2] != 4:
                errs.append(f"{l['id']}: origin=real 必须是 RGBA 抠图 PNG")
            elif (img[:, :, 3] < 10).mean() < 0.05:
                errs.append(f"{l['id']}: alpha 几乎全不透明，疑似没抠图")
            elif l.get("role") == "subject":
                fg = img[:, :, 3] > 200
                if fg.any():
                    gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
                    ct = float(gray[fg].std())
                    if ct < 38.0:
                        errs.append(f"{l['id']}: 主体人像光影反差过低（std={ct:.1f} < 38），显得灰平呆板，请换高反差影棚照片")
        elif o not in ("gen", "real"):
            errs.append(f"{l['id']}: origin 必须是 real 或 gen")
    return errs


def check_zones(fmt, boxes):
    F = FORMATS[fmt]
    errs = []
    for b in boxes:
        role, x0, y0, x1, y1 = b["role"], b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if not (0 <= cx <= F["w"] and 0 <= cy <= F["h"]):
            errs.append(f"{fmt}/{b['id']}: 中心点在画布外")
        if "square" in F and role in ("title", "subtitle", "subject"):
            sx, sy, sw, sh = F["square"]
            inside = (sx <= x0 and x1 <= sx + sw) if role != "subject" else (sx <= cx <= sx + sw)
            if not inside:
                errs.append(f"{fmt}/{b['id']}: {role} 越出 1:1 缩略图安全区 {F['square']}")
        if role in ("title", "subtitle"):
            for ax, ay, aw, ah in F.get("avoid", []):
                if x0 < ax + aw and x1 > ax and y0 < ay + ah and y1 > ay:
                    errs.append(f"{fmt}/{b['id']}: {role} 压到系统避让区 {[ax, ay, aw, ah]}")
            if x0 < 0 or y0 < 0 or x1 > F["w"] or y1 > F["h"]:
                errs.append(f"{fmt}/{b['id']}: {role} 被画布裁切")
    return errs


def cmd_render(a):
    import cv2
    import numpy as np
    from playwright.sync_api import sync_playwright
    root = os.path.abspath(a.root)
    layers = build(root)
    errs = check_layers(root, layers)
    outs = {}
    with sync_playwright() as p:
        br = p.chromium.launch()
        for fmt, F in FORMATS.items():
            pg = br.new_page(viewport={"width": F["w"], "height": F["h"]})
            pg.goto("file:///" + os.path.join(root, "cover.html").replace("\\", "/") + f"?render=1&fmt={fmt}")
            pg.wait_for_selector("body[data-ready='1']", state="attached")
            boxes = pg.evaluate("""() => [...document.querySelectorAll('.layer')].map(e => {
                const r = e.getBoundingClientRect();
                return {id: e.dataset.id, role: e.dataset.role, x: r.x, y: r.y, w: r.width, h: r.height};})""")
            errs += check_zones(fmt, boxes)
            out = os.path.join(root, OUT_NAME[fmt])
            pg.screenshot(path=out, clip={"x": 0, "y": 0, "width": F["w"], "height": F["h"]})
            pg.close()
            img = cv2.imdecode(np.fromfile(out, np.uint8), cv2.IMREAD_COLOR)
            if img.shape[1::-1] != (F["w"], F["h"]):
                errs.append(f"{fmt}: 输出尺寸 {img.shape[1]}×{img.shape[0]} ≠ {F['w']}×{F['h']}")
            if img.std() < 15:
                errs.append(f"{fmt}: 画面近乎空白")
            outs[fmt] = img
        br.close()
    sx, sy, sw, sh = FORMATS["wechat"]["square"]
    sq = outs["wechat"][:, int(round(sx)):int(round(sx)) + sw]
    cv2.imencode(".png", sq)[1].tofile(os.path.join(root, "cover_900x900.png"))
    if a.review:
        # 评审板：效果图 + 四个成品，同一高度并排，供肉眼逐项对照
        tiles = []
        if a.mockup and os.path.exists(os.path.join(root, a.mockup)):
            tiles.append(cv2.imdecode(np.fromfile(os.path.join(root, a.mockup), np.uint8), cv2.IMREAD_COLOR))
        tiles += [outs["wechat"], sq, outs["wide"], outs["xhs"]]
        H = 600
        tiles = [cv2.resize(t, (int(t.shape[1] * H / t.shape[0]), H), interpolation=cv2.INTER_AREA) for t in tiles]
        cv2.imencode(".png", np.hstack(tiles))[1].tofile(os.path.join(root, "review.png"))
    if errs:
        print("FAIL（机器验收未过）：")
        for e in errs:
            print("  -", e)
        sys.exit(1)
    print("PASS（机器验收）：schema、元件出处、画幅尺寸、安全区")
    print("各端封面已生成，对照 SKILL.md 的『目视验收』核对成品图")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for n in ("build", "edit", "render"):
        s = sub.add_parser(n)
        s.add_argument("--root", default=".")
        if n == "edit":
            s.add_argument("--port", type=int, default=8765)
        if n == "render":
            s.add_argument("--mockup", default="mockup.png")
            s.add_argument("--review", action="store_true", help="是否额外生成评审板 review.png")
    a = p.parse_args()
    {"build": lambda a: build(os.path.abspath(a.root)), "edit": cmd_edit, "render": cmd_render}[a.cmd](a)


if __name__ == "__main__":
    main()
