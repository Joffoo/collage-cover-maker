#!/usr/bin/env python3
"""莫尔拓扑干涉光栅 (Moiré Topological Interference Raster)

将主体明暗灰度场映射为第二层微变形线阵的相位偏移 phi(x,y) = alpha * I(x,y)。
使用 Marching Squares 提取干涉场零位/极值等值线，
输出纯透明底的高精折线/条带 SVG 矢量图形，人物以欧普艺术莫尔波纹浮现。

纯 Python 科学计算栈（numpy, scipy, opencv-python, skimage, shapely）。
输入为带 Alpha 通道的 RGBA 贴纸，输出为纯透明底 SVG。
"""
import argparse
import math
import os
import sys

import cv2
import numpy as np
import skimage.measure
from shapely.geometry import LineString


def imread(path):
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if img is None:
        sys.exit(f"FAIL: 读不到图片 {path}")
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
    elif img.shape[2] == 3:
        alpha = np.full(img.shape[:2], 255, dtype=np.uint8)
        img = np.dstack([img, alpha])
    return img


def moire_topology(input_path, out_svg_path, freq=18.0, alpha_param=4.0, stroke="#111111", stroke_width=1.6, simplify_tol=0.8, dual_color=False):
    """提取莫尔拓扑干涉等值线并生成纯矢量 SVG。"""
    img = imread(input_path)
    orig_h, orig_w = img.shape[:2]
    alpha_full = img[:, :, 3]

    if np.sum(alpha_full > 20) < 500:
        sys.exit("FAIL: 输入图有效主体区域过小")

    # 规范化运算分辨率（兼顾拓扑精度与矢量路径节点量）
    max_res = 1000
    scale = min(1.0, max_res / max(orig_h, orig_w))
    pw = max(1, int(orig_w * scale))
    ph = max(1, int(orig_h * scale))

    small = cv2.resize(img, (pw, ph), interpolation=cv2.INTER_AREA)
    alpha = small[:, :, 3].astype(np.float32) / 255.0

    # 提取主体亮度场 I(x, y) 归一化到 [0, 1]
    bgr = small[:, :, :3].astype(np.float32)
    gray = (0.299 * bgr[:, :, 2] + 0.587 * bgr[:, :, 1] + 0.114 * bgr[:, :, 0]) / 255.0

    # 适度平滑消除噪点锯齿，保留连续相位
    gray = cv2.GaussianBlur(gray, (0, 0), 2.2)

    # 载波空间频率 f0（每像素周期数）
    # freq 18 对应主体跨度内约 45~55 条基波，适合高保真欧普艺术表现
    f0 = (freq * 2.6) / ph

    y, x = np.mgrid[0:ph, 0:pw]

    # 基波栅格（Reference Grating）
    S1 = np.cos(2.0 * np.pi * f0 * y)

    # 相位调制栅格（Phase-modulated Grating）
    # phi(x,y) = alpha * 2pi * I(x,y)
    phi = alpha_param * (2.0 * np.pi) * gray
    S2 = np.cos(2.0 * np.pi * f0 * y + phi)

    # 莫尔干涉波场：两组栅格空间线性叠加干涉
    # M(x, y) = S1 + S2 = 2 * cos(phi/2) * cos(2*pi*f0*y + phi/2)
    M = S1 + S2

    # Marching Squares 提取干涉节点与拓扑折线
    contours = skimage.measure.find_contours(M, level=0.0)

    # 将等值线按照 Alpha 通道分割为仅落在主体内部的连续线段
    segments = []
    sx = orig_w / pw
    sy = orig_h / ph

    for c in contours:
        # c 是 (N, 2) 数组，坐标为 (y, x)
        if len(c) < 3:
            continue

        xs_clip = np.clip(np.round(c[:, 1]).astype(int), 0, pw - 1)
        ys_clip = np.clip(np.round(c[:, 0]).astype(int), 0, ph - 1)
        valid = alpha[ys_clip, xs_clip] >= 0.20

        if not np.any(valid):
            continue

        # 提取连续有效的 True 切片
        changes = np.diff(np.concatenate(([False], valid, [False])).astype(int))
        starts = np.where(changes == 1)[0]
        ends = np.where(changes == -1)[0]

        for s, e in zip(starts, ends):
            sub_c = c[s:e]
            if len(sub_c) < 3:
                continue

            # 映射回原图坐标 (X, Y)
            pts = np.column_stack([sub_c[:, 1] * sx, sub_c[:, 0] * sy])
            ls = LineString(pts)

            # Douglas-Peucker 几何化简，滤除亚像素抖动并压低 SVG 体积
            if simplify_tol > 0:
                ls = ls.simplify(simplify_tol, preserve_topology=True)

            if ls.length >= 6.0 and len(ls.coords) >= 2:
                segments.append(ls)

    if not segments:
        sys.exit("FAIL: 未能在主体区域内生成有效拓扑线条")

    # 构建纯净矢量 SVG
    os.makedirs(os.path.dirname(os.path.abspath(out_svg_path)), exist_ok=True)

    path_data = []
    for ls in segments:
        coords = list(ls.coords)
        d = f"M {coords[0][0]:.1f} {coords[0][1]:.1f} " + " ".join(f"L {p[0]:.1f} {p[1]:.1f}" for p in coords[1:])
        path_data.append(d)

    full_d = " ".join(path_data)

    if dual_color:
        # 双色叠印贴纸模式：基底青蓝 #0047FF + 极值洋红 #FF1E6E
        half = len(segments) // 2
        d1 = " ".join(path_data[:half])
        d2 = " ".join(path_data[half:])
        svg_content = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {orig_w} {orig_h}" width="{orig_w}" height="{orig_h}">\n'
            f'  <g fill="none" stroke="#0047FF" stroke-width="{stroke_width:.1f}" stroke-linecap="round" stroke-linejoin="round" opacity="0.9">\n'
            f'    <path d="{d1}"/>\n'
            f'  </g>\n'
            f'  <g fill="none" stroke="#FF1E6E" stroke-width="{stroke_width:.1f}" stroke-linecap="round" stroke-linejoin="round" opacity="0.9">\n'
            f'    <path d="{d2}"/>\n'
            f'  </g>\n'
            f'</svg>\n'
        )
    else:
        # 单色欧普纯净线条模式
        svg_content = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {orig_w} {orig_h}" width="{orig_w}" height="{orig_h}">\n'
            f'  <path d="{full_d}" fill="none" stroke="{stroke}" stroke-width="{stroke_width:.1f}" stroke-linecap="round" stroke-linejoin="round"/>\n'
            f'</svg>\n'
        )

    with open(out_svg_path, "w", encoding="utf-8") as f:
        f.write(svg_content)

    file_size_kb = len(svg_content) // 1024
    print(f"OK [moire]: {out_svg_path} ({orig_w}x{orig_h}, {len(segments)} 条拓扑曲线, {file_size_kb} KB, freq={freq}, alpha={alpha_param})")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", help="输入 RGBA 贴纸图片")
    p.add_argument("out", help="输出 SVG 矢量路径文件")
    p.add_argument("--freq", type=float, default=18.0, help="莫尔基准载波频率（默认 18.0）")
    p.add_argument("--alpha", type=float, default=4.0, dest="alpha_param", help="亮度相位调制深度 alpha（默认 4.0）")
    p.add_argument("--stroke", default="#111111", help="描边颜色（默认 #111111）")
    p.add_argument("--width", type=float, default=1.6, dest="stroke_width", help="描边粗细像素（默认 1.6）")
    p.add_argument("--simplify", type=float, default=0.8, help="折线化简公差（默认 0.8）")
    p.add_argument("--dual", action="store_true", help="启用双色叠印模式（#0047FF / #FF1E6E）")
    args = p.parse_args()
    moire_topology(args.input, args.out, freq=args.freq, alpha_param=args.alpha_param,
                   stroke=args.stroke, stroke_width=args.stroke_width,
                   simplify_tol=args.simplify, dual_color=args.dual)


if __name__ == "__main__":
    main()
