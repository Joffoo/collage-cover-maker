#!/usr/bin/env python3
"""物理重磅卡纸撕裂切片 (Physical Heavy Paper Shredder Slicing)

将主体切分为 N 条横向切片，加入分形撕裂毛刺（Torn Paper Fuzz）与真实纸芯白毛边，
每条施加交替横向位移与微倾角，并烘焙卡纸投影。
支持单张错位贴纸直出，或通过 `--explode <dir>` 导出完整多图层切片序列。

纯 Python 科学计算栈（numpy, scipy, opencv-python, shapely）。
输入输出恒保透明通道（RGBA），杜绝背景焊死。
"""
import argparse
import math
import os
import sys

import cv2
import numpy as np


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


def imwrite(path, img):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    ext = os.path.splitext(path)[1].lower() or ".png"
    ok, buf = cv2.imencode(ext, img)
    if not ok:
        sys.exit(f"FAIL: 写不出图片 {path}")
    buf.tofile(path)


def generate_torn_curve(w, base_y, rng, amplitude=9.0):
    """合成真实重磅卡纸断裂线：长波起伏 + 分形中波 + 纸浆纤维高频毛刺。"""
    x = np.arange(w, dtype=np.float32)

    # 1. 低频起伏（宏观断裂趋势）
    k1 = rng.uniform(0.003, 0.007)
    k2 = rng.uniform(0.012, 0.025)
    p1 = rng.uniform(0, 2 * math.pi)
    p2 = rng.uniform(0, 2 * math.pi)
    macro = (amplitude * 0.55) * np.sin(k1 * x + p1) + (amplitude * 0.30) * np.cos(k2 * x + p2)

    # 2. 中频分形撕裂（多尺度高斯滤波高斯噪点）
    raw_noise = rng.normal(0, 1, w).astype(np.float32)
    # 尺度 1
    g1 = np.exp(-np.linspace(-2.5, 2.5, 31)**2)
    g1 /= g1.sum()
    mid1 = np.convolve(raw_noise, g1, mode='same') * (amplitude * 0.40)
    # 尺度 2
    g2 = np.exp(-np.linspace(-2.5, 2.5, 11)**2)
    g2 /= g2.sum()
    mid2 = np.convolve(raw_noise, g2, mode='same') * (amplitude * 0.25)

    # 3. 纸浆纤维撕裂毛刺（Torn Paper Fuzz: 高频极值齿状毛边）
    fuzz = rng.uniform(-1.5, 1.5, w).astype(np.float32)

    curve = base_y + macro + mid1 + mid2 + fuzz
    return curve


def shredder_slice(input_path, out_path, strips=6, shift=18.0, explode_dir=None, seed=42):
    """执行物理重磅卡纸撕裂切片，生成错位贴纸或分层图层。"""
    img = imread(input_path)
    h, w = img.shape[:2]
    alpha = img[:, :, 3]

    ys, xs = np.where(alpha > 20)
    if len(ys) == 0:
        sys.exit("FAIL: 输入图全透明")

    rng = np.random.RandomState(seed)

    y_min, y_max = ys.min(), ys.max() + 1
    sub_h = y_max - y_min
    strip_step = sub_h / float(strips)

    # 生成各切片分界撕裂线
    curves = []
    curves.append(np.zeros(w, dtype=np.float32))  # 顶部基线 0

    cur_base = y_min
    for k in range(1, strips):
        nominal_y = y_min + k * strip_step
        # 振幅随着主体尺寸自适应
        amp = max(4.0, min(14.0, strip_step * 0.12))
        c = generate_torn_curve(w, nominal_y, rng, amplitude=amp)

        # 保证分界线不穿插倒挂
        prev_c = curves[-1]
        c = np.maximum(c, prev_c + 6.0)
        c = np.clip(c, 0, h - 1)
        curves.append(c)

    curves.append(np.full(w, h - 1, dtype=np.float32))  # 底部基线 H-1

    # 初始化画布
    canvas_bgr = np.zeros((h, w, 3), dtype=np.float32)
    canvas_alpha = np.zeros((h, w), dtype=np.float32)
    shadow_alpha = np.zeros((h, w), dtype=np.float32)

    exploded_layers = []

    # 逐层处理每个切片（从上至下压盖）
    for k in range(strips):
        top_curve = curves[k]
        bot_curve = curves[k + 1]

        # 构建闭合多边形外框
        top_pts = np.column_stack([np.arange(w), top_curve])
        bot_pts = np.column_stack([np.arange(w)[::-1], bot_curve[::-1]])
        poly_pts = np.vstack([top_pts, bot_pts]).astype(np.int32)

        # 栅格化该切片掩膜
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask, [poly_pts], 255)

        # 结合原图 Alpha
        strip_a = (mask / 255.0) * (alpha / 255.0)
        if strip_a.sum() < 25.0:
            continue

        strip_bgr = img[:, :, :3].astype(np.float32)

        # 烘焙切口处暴露的重磅卡纸纸浆白毛边（White Fiber Rim）
        if k < strips - 1:
            fiber_mask = np.zeros((h, w), dtype=np.uint8)
            rim_pts = np.column_stack([np.arange(w), bot_curve.astype(np.int32)])
            for px, py in rim_pts[::2]:
                if 0 <= px < w and 0 <= py < h and alpha[py, px] > 20:
                    rad = rng.randint(1, 3)
                    cv2.circle(fiber_mask, (px, py), rad, 255, -1)
            fiber_mask = cv2.GaussianBlur(fiber_mask, (3, 3), 0.8)
            fiber_factor = (fiber_mask / 255.0) * 0.65
            # 卡纸白毛边颜色 #FAF7F2
            strip_bgr = strip_bgr * (1.0 - fiber_factor[:, :, None]) + np.array([242.0, 247.0, 250.0], dtype=np.float32) * fiber_factor[:, :, None]

        # 计算切片质心与交替错位参数
        m_ys, m_xs = np.where(strip_a > 0.1)
        if len(m_xs) == 0:
            continue
        cx = float(np.mean(m_xs))
        cy = float(np.mean(m_ys))

        direction = -1.0 if (k % 2 == 0) else 1.0
        dx = direction * shift * rng.uniform(0.85, 1.18)
        d_angle = direction * rng.uniform(0.6, 1.25) * (shift / 18.0)
        dy = (k - (strips - 1) / 2.0) * 2.2

        # 仿射变换
        M = cv2.getRotationMatrix2D((cx, cy), d_angle, 1.0)
        M[0, 2] += dx
        M[1, 2] += dy

        warped_bgr = cv2.warpAffine(strip_bgr, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        warped_a = cv2.warpAffine(strip_a, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)

        # 如果需要输出切片序列，保存单层 RGBA
        if explode_dir:
            layer_rgba = np.dstack([
                np.clip(warped_bgr, 0, 255).astype(np.uint8),
                np.clip(warped_a * 255.0, 0, 255.0).astype(np.uint8)
            ])
            exploded_layers.append(layer_rgba)

        # 烘焙物理卡纸硬阴影（偏置 +2.0px, +3.5px，深黑微透）
        sh_M = M.copy()
        sh_M[0, 2] += 2.0
        sh_M[1, 2] += 3.5
        strip_shadow = cv2.warpAffine(strip_a, sh_M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        strip_shadow = cv2.GaussianBlur(strip_shadow, (5, 5), 1.2) * 0.40
        shadow_alpha = np.maximum(shadow_alpha, strip_shadow)

        # 合成切片至总图（Alpha Over）
        bg_a = canvas_alpha
        bg_rgb = canvas_bgr
        cur_a = warped_a
        cur_rgb = warped_bgr

        new_a = cur_a + bg_a * (1.0 - cur_a)
        new_rgb = (cur_rgb * cur_a[:, :, None] + bg_rgb * (bg_a * (1.0 - cur_a))[:, :, None]) / (new_a[:, :, None] + 1e-6)

        canvas_alpha = new_a
        canvas_bgr = new_rgb

    # 烘焙阴影到底层
    final_a = canvas_alpha + shadow_alpha * (1.0 - canvas_alpha)
    final_rgb = canvas_bgr * canvas_alpha[:, :, None] + np.array([16.0, 16.0, 22.0], dtype=np.float32) * (shadow_alpha * (1.0 - canvas_alpha))[:, :, None]
    final_rgb = final_rgb / (final_a[:, :, None] + 1e-6)

    out_rgba = np.dstack([
        np.clip(final_rgb, 0, 255).astype(np.uint8),
        np.clip(final_a * 255.0, 0, 255.0).astype(np.uint8)
    ])

    imwrite(out_path, out_rgba)

    # 导出序列切片目录
    if explode_dir:
        os.makedirs(explode_dir, exist_ok=True)
        for idx, layer in enumerate(exploded_layers, 1):
            layer_path = os.path.join(explode_dir, f"strip_{idx:02d}.png")
            imwrite(layer_path, layer)
        print(f"OK [slice]: 已导出 {len(exploded_layers)} 个独立切片图层 → {explode_dir}")

    print(f"OK [slice]: {out_path} ({w}x{h}, strips={strips}, shift={shift}px)")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", help="输入 RGBA 贴纸图片")
    p.add_argument("out", help="输出 RGBA 错位切片贴纸图片")
    p.add_argument("--strips", type=int, default=6, help="卡纸切片数量（默认 6）")
    p.add_argument("--shift", type=float, default=18.0, help="交替错位横向位移像素（默认 18.0）")
    p.add_argument("--explode", dest="explode_dir", default=None, help="可选：导出切片序列图层目录")
    p.add_argument("--seed", type=int, default=42, help="随机种子（默认 42）")
    args = p.parse_args()
    shredder_slice(args.input, args.out, strips=args.strips, shift=args.shift, explode_dir=args.explode_dir, seed=args.seed)


if __name__ == "__main__":
    main()
