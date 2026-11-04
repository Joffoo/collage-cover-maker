#!/usr/bin/env python3
"""元件生产与前卫解构：split / real / gen / synth / fx。

依赖由成熟库承担，本脚本做统一调度与胶水：
  real  → rembg（BiRefNet 系抠图模型）
  gen   → vtracer（彩色位图转 SVG）
  split → OpenCV 连通域
  fx    → numpy, scipy, shapely, skimage（前卫计算视觉与拓扑解构特效）

用法：
  python make_part.py check
  python make_part.py split <sheet.png> <parts_dir>
  python make_part.py real  <photo> <out.png> [--model birefnet-portrait] [--border 14]
  python make_part.py gen   <part.png> <out.svg> [--border 14]
  python make_part.py synth <parts_dir> [--seed 42]
  python make_part.py fx voronoi <input.png> <out.png> [--cells 80] [--jitter 6] [--gap 2]
  python make_part.py fx moire <input.png> <out.svg> [--freq 18] [--alpha 4.0]
  python make_part.py fx slice <input.png> <out.png> [--strips 6] [--shift 18] [--explode <dir>]
  python make_part.py fx photoelastic <input.png> <out.png> [--retardation 1800]
"""
import argparse
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np


def imread(path, flags=cv2.IMREAD_UNCHANGED):
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), flags)
    if img is None:
        sys.exit(f"FAIL: 读不到图片 {path}")
    return img


def imwrite(path, img):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    ok, buf = cv2.imencode(os.path.splitext(path)[1] or ".png", img)
    if not ok:
        sys.exit(f"FAIL: 写不出 {path}")
    buf.tofile(path)


def trim(rgba, pad=0):
    ys, xs = np.where(rgba[:, :, 3] > 8)
    if len(xs) == 0:
        sys.exit("FAIL: 抠图结果全透明")
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    out = rgba[max(0, y0 - pad):y1 + pad, max(0, x0 - pad):x1 + pad]
    return out


def diecut(rgba, px):
    """给主体加纯白模切边：白环垫在主体之下，alpha 取膨胀后的轮廓。"""
    if px <= 0:
        return rgba
    pad = px + 2
    rgba = cv2.copyMakeBorder(rgba, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(0, 0, 0, 0))
    alpha = rgba[:, :, 3]
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * px + 1, 2 * px + 1))
    ring = cv2.dilate((alpha > 8).astype(np.uint8) * 255, k)
    ring = cv2.GaussianBlur(ring, (0, 0), 1.2)
    a = alpha.astype(np.float32)[..., None] / 255.0
    white = np.full(rgba.shape[:2] + (3,), 255, np.float32)
    rgb = rgba[:, :, :3].astype(np.float32) * a + white * (1 - a)
    return np.dstack([rgb.astype(np.uint8), ring])


def need(module, pip_name=None):
    try:
        return importlib.import_module(module)
    except ImportError:
        sys.exit(f"FAIL: 缺少 {module}。安装：pip install {pip_name or module}")


def cmd_check(_):
    ok = True
    for mod, pip in (
        ("rembg", "rembg[cpu]"),
        ("vtracer", "vtracer"),
        ("playwright", "playwright"),
        ("scipy", "scipy"),
        ("shapely", "shapely"),
        ("skimage", "scikit-image"),
    ):
        try:
            importlib.import_module(mod)
            print(f"OK    {mod}")
        except ImportError:
            ok = False
            print(f"MISS  {mod}  ->  pip install {pip}")
    sys.exit(0 if ok else 1)


def cmd_split(a):
    img = imread(a.sheet, cv2.IMREAD_COLOR)
    h, w = img.shape[:2]
    diff = np.linalg.norm(img.astype(np.float32) - 255.0, axis=2)
    near_white = (diff < a.tol).astype(np.uint8)
    # 只有与画面边缘相连的白才是背景，元件内部的白（衬衫、高光）保留
    n, lab = cv2.connectedComponents(near_white)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    bg = np.isin(lab, [i for i in border if i != 0])
    fg = (~bg).astype(np.uint8) * 255
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    cnt, labels, stats, _ = cv2.connectedComponentsWithStats(fg)
    items = [(stats[i], i) for i in range(1, cnt) if stats[i, cv2.CC_STAT_AREA] >= a.min_area]
    items.sort(key=lambda t: (t[0][cv2.CC_STAT_TOP] // 200, t[0][cv2.CC_STAT_LEFT]))
    os.makedirs(a.parts_dir, exist_ok=True)
    thumbs = []
    for idx, (s, i) in enumerate(items, 1):
        x, y, cw, ch = s[0], s[1], s[2], s[3]
        m = (labels[y:y + ch, x:x + cw] == i).astype(np.uint8) * 255
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
        rgba = np.dstack([img[y:y + ch, x:x + cw], m])
        name = f"p{idx:02d}.png"
        imwrite(os.path.join(a.parts_dir, name), rgba)
        t = np.full((220, 220, 3), 235, np.uint8)
        sc = min(200 / cw, 200 / ch)
        r = cv2.resize(rgba, (max(1, int(cw * sc)), max(1, int(ch * sc))), interpolation=cv2.INTER_AREA)
        oy, ox = (220 - r.shape[0]) // 2, (220 - r.shape[1]) // 2
        al = r[:, :, 3:4] / 255.0
        t[oy:oy + r.shape[0], ox:ox + r.shape[1]] = (r[:, :, :3] * al + t[oy:oy + r.shape[0], ox:ox + r.shape[1]] * (1 - al)).astype(np.uint8)
        cv2.putText(t, name, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
        thumbs.append(t)
    if not thumbs:
        sys.exit("FAIL: 没切出任何元件，检查元件图是否为纯白底")
    cols = 5
    rows = -(-len(thumbs) // cols)
    index = np.full((rows * 220, cols * 220, 3), 235, np.uint8)
    for k, t in enumerate(thumbs):
        index[(k // cols) * 220:(k // cols + 1) * 220, (k % cols) * 220:(k % cols + 1) * 220] = t
    imwrite(os.path.join(a.parts_dir, "_index.png"), index)
    print(f"OK: {len(thumbs)} 个元件 → {a.parts_dir}（看 _index.png 认领：real 抠真实素材 / gen 矢量化）")


def cmd_real(a):
    rembg = need("rembg", "rembg[cpu]")
    session = rembg.new_session(a.model)
    with open(a.photo, "rb") as f:
        out = rembg.remove(f.read(), session=session, post_process_mask=True)
    rgba = cv2.imdecode(np.frombuffer(out, np.uint8), cv2.IMREAD_UNCHANGED)
    rgba = diecut(trim(rgba), a.border)
    imwrite(a.out, rgba)
    print(f"OK: {a.out} {rgba.shape[1]}x{rgba.shape[0]}（模型 {a.model}）")


def silhouette_path(alpha):
    """alpha 轮廓（含孔洞）→ SVG path 数据，用作 clipPath。"""
    cnts, _ = cv2.findContours((alpha > 127).astype(np.uint8) * 255, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    parts = []
    for c in cnts:
        c = cv2.approxPolyDP(c, 0.8, True).reshape(-1, 2)
        if len(c) >= 3:
            parts.append("M" + " L".join(f"{x} {y}" for x, y in c) + " Z")
    return " ".join(parts)


def cmd_gen(a):
    import re
    vtracer = need("vtracer")
    rgba = imread(a.part)
    if rgba.ndim != 3 or rgba.shape[2] != 4:
        sys.exit("FAIL: gen 输入须是 split 产出的 RGBA 元件")
    rgba = diecut(rgba, a.border)
    tmp = os.path.splitext(a.out)[0] + "._tmp.png"
    # vtracer 不识别 alpha：透明区垫白色交给它出 stacked 色块，再用 alpha 轮廓 clipPath 裁出真实外形
    al = (rgba[:, :, 3:4] > 127).astype(np.float32)
    flat = (rgba[:, :, :3] * al + 255 * (1 - al)).astype(np.uint8)
    imwrite(tmp, flat)
    vtracer.convert_image_to_svg_py(
        tmp, a.out, colormode="color", hierarchical="stacked", mode="spline",
        filter_speckle=4, color_precision=6, layer_difference=16,
        corner_threshold=60, length_threshold=4.0, splice_threshold=45, path_precision=3)
    os.remove(tmp)
    svg = open(a.out, encoding="utf-8").read()
    clip = silhouette_path(rgba[:, :, 3])
    svg = re.sub(r"<svg([^>]*)>", lambda m: f'<svg{m.group(1)}><defs><clipPath id="sil"><path clip-rule="evenodd" d="{clip}"/></clipPath></defs><g clip-path="url(#sil)">', svg, count=1)
    svg = svg.replace("</svg>", "</g></svg>")
    open(a.out, "w", encoding="utf-8").write(svg)
    print(f"OK: {a.out}（{len(svg) // 1024} KB）")


def cmd_synth(a):
    """按随机种子现场生成高精细干刷丙烯与手绘马克笔涂鸦 SVG（生图限流时兜底，不囤静态图库）。"""
    import math, random
    rng = random.Random(a.seed)
    os.makedirs(a.parts_dir, exist_ok=True)

    def smear(color, seed_offset):
        r = random.Random(a.seed + seed_offset)
        w, h = 900, 340
        paths = []
        top, bot = [], []
        steps = 28
        for i in range(steps + 1):
            t = i / steps
            x = 55 + t * (w - 110)
            arc = math.sin(t * math.pi) * 26
            top.append((x + r.uniform(-6, 6), 85 - arc * 0.5 + r.uniform(-14, 14)))
            bot.append((x + r.uniform(-6, 6), 255 - arc * 0.3 + r.uniform(-14, 14)))
        right_feathers = []
        for j in range(14):
            fy = top[-1][1] + (bot[-1][1] - top[-1][1]) * (j / 13.0)
            fx = w - 25 + r.uniform(-75, 20) if j % 2 == 0 else w - 95 + r.uniform(-35, 10)
            right_feathers.append((fx, fy + r.uniform(-4, 4)))
        left_feathers = []
        for j in range(12):
            fy = bot[0][1] - (bot[0][1] - top[0][1]) * (j / 11.0)
            fx = 25 + r.uniform(-15, 65) if j % 2 == 0 else 80 + r.uniform(-10, 35)
            left_feathers.append((fx, fy + r.uniform(-4, 4)))
        pts = top + right_feathers + list(reversed(bot)) + left_feathers
        d = f"M {pts[0][0]:.1f} {pts[0][1]:.1f} " + " ".join(f"L {p[0]:.1f} {p[1]:.1f}" for p in pts[1:]) + " Z"
        paths.append(f'<path d="{d}" fill="{color}"/>')
        for _ in range(18):
            y_base = r.uniform(95, 240)
            x0 = r.uniform(70, 500)
            length = r.uniform(90, 360)
            thick = r.uniform(2.5, 7.5)
            s_pts = [(x0 + (k / 8) * length, y_base + r.uniform(-5, 5)) for k in range(9)]
            for k in range(8, -1, -1):
                s_pts.append((s_pts[k][0], s_pts[k][1] + thick * math.sin((k / 8) * math.pi) + r.uniform(-1.5, 1.5)))
            sd = f"M {s_pts[0][0]:.1f} {s_pts[0][1]:.1f} " + " ".join(f"L {p[0]:.1f} {p[1]:.1f}" for p in s_pts[1:]) + " Z"
            paths.append(f'<path d="{sd}" fill="#F7F5F0" opacity="{r.uniform(0.65, 0.95):.2f}"/>')
        for _ in range(14):
            cx, cy, rad = r.uniform(20, w - 20), r.uniform(20, h - 20), r.uniform(3.5, 11.0)
            blob = [(cx + math.cos(k / 8 * 2 * math.pi) * rad * r.uniform(0.7, 1.3),
                     cy + math.sin(k / 8 * 2 * math.pi) * rad * r.uniform(0.7, 1.3)) for k in range(8)]
            bd = f"M {blob[0][0]:.1f} {blob[0][1]:.1f} " + " ".join(f"L {p[0]:.1f} {p[1]:.1f}" for p in blob[1:]) + " Z"
            paths.append(f'<path d="{bd}" fill="{color}"/>')
        return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">' + "".join(paths) + "</svg>"

    for name, col, off in (("smear_blue.svg", "#0047FF", 1), ("smear_yellow.svg", "#FFE600", 2), ("smear_pink.svg", "#FF1E6E", 3)):
        open(os.path.join(a.parts_dir, name), "w", encoding="utf-8").write(smear(col, off))

    # 3 marker doodles: spiral, bolt, burst
    pts_in, pts_out = [], []
    for i in range(95):
        t = i / 94 * 3.3 * 2 * math.pi
        rad = 14 + (i / 94) * 96 + rng.uniform(-2.2, 2.2)
        th = 4.2 + 2.5 * math.sin(i / 94 * math.pi)
        ang = t + rng.uniform(-0.03, 0.03)
        pts_in.append((150 + math.cos(ang) * (rad - th / 2), 150 + math.sin(ang) * (rad - th / 2)))
        pts_out.append((150 + math.cos(ang) * (rad + th / 2), 150 + math.sin(ang) * (rad + th / 2)))
    sp = pts_out + list(reversed(pts_in))
    sd = f"M {sp[0][0]:.1f} {sp[0][1]:.1f} " + " ".join(f"L {p[0]:.1f} {p[1]:.1f}" for p in sp[1:]) + " Z"
    ticks = []
    for k in range(8):
        ang = k * (2 * math.pi / 8) + 0.3
        x0, y0 = 150 + math.cos(ang) * 124, 150 + math.sin(ang) * 124
        x1, y1 = 150 + math.cos(ang) * 142, 150 + math.sin(ang) * 142
        nx, ny = -math.sin(ang) * 3.5, math.cos(ang) * 3.5
        ticks.append(f'<path d="M {x0-nx:.1f} {y0-ny:.1f} L {x1-nx*0.6:.1f} {y1-ny*0.6:.1f} L {x1+nx*0.6:.1f} {y1+ny*0.6:.1f} L {x0+nx:.1f} {y0+ny:.1f} Z" fill="#111111"/>')
    open(os.path.join(a.parts_dir, "doodle_spiral.svg"), "w", encoding="utf-8").write(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300"><path d="{sd}" fill="#111111"/>{"".join(ticks)}</svg>')

    bolt_base = [(125, 12), (42, 138), (105, 138), (68, 268), (185, 116), (118, 116)]
    bolt_pts = []
    for i in range(len(bolt_base)):
        p0, p1 = bolt_base[i], bolt_base[(i + 1) % len(bolt_base)]
        for s in range(5):
            t = s / 5.0
            bolt_pts.append((p0[0] + (p1[0] - p0[0]) * t + rng.uniform(-1.8, 1.8),
                             p0[1] + (p1[1] - p0[1]) * t + rng.uniform(-1.8, 1.8)))
    bd0 = f"M {bolt_pts[0][0]+8:.1f} {bolt_pts[0][1]+8:.1f} " + " ".join(f"L {p[0]+8:.1f} {p[1]+8:.1f}" for p in bolt_pts[1:]) + " Z"
    bd1 = f"M {bolt_pts[0][0]:.1f} {bolt_pts[0][1]:.1f} " + " ".join(f"L {p[0]:.1f} {p[1]:.1f}" for p in bolt_pts[1:]) + " Z"
    open(os.path.join(a.parts_dir, "doodle_bolt.svg"), "w", encoding="utf-8").write(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 280"><path d="{bd0}" fill="#FF1E6E"/><path d="{bd1}" fill="#111111"/></svg>')

    outer, inner = [], []
    spikes = 11
    for i in range(spikes * 2):
        ang = i * math.pi / spikes
        r_o = (118 + rng.uniform(-14, 16)) if i % 2 == 0 else (48 + rng.uniform(-8, 8))
        r_i = r_o * 0.72
        outer.append((130 + math.cos(ang) * r_o, 130 + math.sin(ang) * r_o))
        inner.append((130 + math.cos(ang) * r_i, 130 + math.sin(ang) * r_i))
    od = f"M {outer[0][0]:.1f} {outer[0][1]:.1f} " + " ".join(f"L {p[0]:.1f} {p[1]:.1f}" for p in outer[1:]) + " Z"
    id_ = f"M {inner[0][0]:.1f} {inner[0][1]:.1f} " + " ".join(f"L {p[0]:.1f} {p[1]:.1f}" for p in inner[1:]) + " Z"
    open(os.path.join(a.parts_dir, "doodle_burst.svg"), "w", encoding="utf-8").write(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 260 260"><path d="{od}" fill="#111111"/><path d="{id_}" fill="#FFE600"/></svg>')
    print(f"OK: 已按 seed={a.seed} 现场生成 6 个矢量笔触/涂鸦元件 → {a.parts_dir}")


def cmd_fx_voronoi(a):
    from fx.voronoi_fracture import voronoi_fracture
    voronoi_fracture(a.input, a.out, cells=a.cells, jitter=a.jitter, gap=a.gap, seed=a.seed)


def cmd_fx_moire(a):
    from fx.moire_topology import moire_topology
    moire_topology(a.input, a.out, freq=a.freq, alpha_param=a.alpha_param,
                   stroke=a.stroke, stroke_width=a.stroke_width,
                   simplify_tol=a.simplify, dual_color=a.dual)


def cmd_fx_slice(a):
    from fx.shredder_slice import shredder_slice
    shredder_slice(a.input, a.out, strips=a.strips, shift=a.shift, explode_dir=a.explode_dir, seed=a.seed)


def cmd_fx_kawamura(a):
    from fx.kawamura import kawamura_shred
    kawamura_shred(a.input, a.out, strips=a.strips, amplitude=a.amplitude,
                   freq=a.freq, stagger=a.stagger, jitter=a.jitter,
                   mode=a.mode, slit_relief=not a.no_slit, seed=a.seed)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check").set_defaults(fn=cmd_check)
    s = sub.add_parser("split")
    s.add_argument("sheet"); s.add_argument("parts_dir")
    s.add_argument("--tol", type=float, default=22)
    s.add_argument("--min-area", type=int, default=1500)
    s.set_defaults(fn=cmd_split)
    r = sub.add_parser("real")
    r.add_argument("photo"); r.add_argument("out")
    r.add_argument("--model", default="birefnet-general-lite")
    r.add_argument("--border", type=int, default=14)
    r.set_defaults(fn=cmd_real)
    g = sub.add_parser("gen")
    g.add_argument("part"); g.add_argument("out")
    g.add_argument("--border", type=int, default=14)
    g.set_defaults(fn=cmd_gen)
    sy = sub.add_parser("synth")
    sy.add_argument("parts_dir")
    sy.add_argument("--seed", type=int, default=42)
    sy.set_defaults(fn=cmd_synth)

    # 前卫计算视觉与几何拓扑解构特效
    fx = sub.add_parser("fx", help="前卫计算几何与微分拓扑解构特效算子")
    fx_sub = fx.add_subparsers(dest="fx_cmd", required=True)

    # 1. voronoi
    v = fx_sub.add_parser("voronoi", help="加权质心 Voronoi 晶体热应力碎裂")
    v.add_argument("input", help="输入 RGBA 贴纸图片")
    v.add_argument("out", help="输出 RGBA 碎裂贴纸图片")
    v.add_argument("--cells", type=int, default=80, help="晶胞数量（默认 80）")
    v.add_argument("--jitter", type=float, default=6.0, help="应力刚体位移抖动像素（默认 6.0）")
    v.add_argument("--gap", type=float, default=2.0, help="晶胞缝隙宽度像素（默认 2.0）")
    v.add_argument("--seed", type=int, default=42, help="随机种子（默认 42）")
    v.set_defaults(fn=cmd_fx_voronoi)

    # 2. moire
    m = fx_sub.add_parser("moire", help="莫尔拓扑干涉光栅")
    m.add_argument("input", help="输入 RGBA 贴纸图片")
    m.add_argument("out", help="输出 SVG 矢量路径文件")
    m.add_argument("--freq", type=float, default=18.0, help="莫尔基准载波频率（默认 18.0）")
    m.add_argument("--alpha", type=float, default=4.0, dest="alpha_param", help="亮度相位调制深度 alpha（默认 4.0）")
    m.add_argument("--stroke", default="#111111", help="描边颜色（默认 #111111）")
    m.add_argument("--width", type=float, default=1.6, dest="stroke_width", help="描边粗细像素（默认 1.6）")
    m.add_argument("--simplify", type=float, default=0.8, help="折线化简公差（默认 0.8）")
    m.add_argument("--dual", action="store_true", help="启用双色叠印模式（#0047FF / #FF1E6E）")
    m.set_defaults(fn=cmd_fx_moire)

    # 3. slice
    sl = fx_sub.add_parser("slice", help="物理重磅卡纸撕裂切片")
    sl.add_argument("input", help="输入 RGBA 贴纸图片")
    sl.add_argument("out", help="输出 RGBA 错位切片贴纸图片")
    sl.add_argument("--strips", type=int, default=6, help="卡纸切片数量（默认 6）")
    sl.add_argument("--shift", type=float, default=18.0, help="交替错位横向位移像素（默认 18.0）")
    sl.add_argument("--explode", dest="explode_dir", default=None, help="可选：导出切片序列图层目录")
    sl.add_argument("--seed", type=int, default=42, help="随机种子（默认 42）")
    sl.set_defaults(fn=cmd_fx_slice)

    # 4. kawamura
    kw = fx_sub.add_parser("kawamura", help="河村康辅碎纸机垂直条纹重组")
    kw.add_argument("input", help="输入 RGBA 贴纸图片")
    kw.add_argument("out", help="输出 RGBA 贴纸图片")
    kw.add_argument("--strips", type=int, default=70, help="垂直切条数量（默认 70）")
    kw.add_argument("--amplitude", type=float, default=50.0, help="宏观波浪位移像素（默认 50.0）")
    kw.add_argument("--freq", type=float, default=2.5, help="横向波浪频率周期（默认 2.5）")
    kw.add_argument("--stagger", type=float, default=16.0, help="相邻纸条交替跳跃位移像素（默认 16.0）")
    kw.add_argument("--jitter", type=float, default=10.0, help="随机群组滑移像素（默认 10.0）")
    kw.add_argument("--mode", choices=["wave", "stagger", "glitch"], default="wave")
    kw.add_argument("--no-slit", action="store_true", help="禁用刀口切边微浮雕")
    kw.add_argument("--seed", type=int, default=42, help="随机种子（默认 42）")
    kw.set_defaults(fn=cmd_fx_kawamura)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
