#!/usr/bin/env python3
"""加权质心 Voronoi 晶体热应力碎裂 (Weighted Centroidal Voronoi Fracture)

基于图像反差/Canny边缘与梯度构建自适应密度场，通过加权 Lloyd 松弛（CVD）
生成非均匀晶胞，沿梯度方向施加微小刚体位移与旋转，保留原图局部高清切片，
并烘焙微小硬阴影与晶体切面白边。

纯 Python 科学计算栈（numpy, scipy, opencv-python, shapely）。
输入输出恒保透明通道（RGBA），杜绝背景焊死。
"""
import argparse
import math
import os
import sys

import cv2
import numpy as np
from scipy.spatial import cKDTree
import shapely.ops
from shapely.geometry import MultiPoint, box, Polygon


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


def compute_density_field(gray, alpha, max_dim=400):
    """根据灰度边缘与反差计算自适应密度场。"""
    h, w = gray.shape[:2]
    scale = min(1.0, max_dim / max(h, w))
    sw, sh = max(1, int(w * scale)), max(1, int(h * scale))

    s_gray = cv2.resize(gray, (sw, sh), interpolation=cv2.INTER_AREA)
    s_alpha = cv2.resize(alpha, (sw, sh), interpolation=cv2.INTER_NEAREST)

    # Canny 边缘与 Sobel 梯度
    canny = cv2.Canny(s_gray, 40, 130).astype(np.float32) / 255.0
    gx = cv2.Sobel(s_gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(s_gray, cv2.CV_32F, 0, 1, ksize=3)
    grad = np.sqrt(gx**2 + gy**2)
    grad = grad / (grad.max() + 1e-6)

    # 局部反差与基础权重
    density = (0.12 + 0.50 * canny + 0.38 * grad) * (s_alpha > 30)
    density = cv2.GaussianBlur(density, (5, 5), 1.2)
    density = density / (density.sum() + 1e-8)
    return density, sw, sh


def weighted_lloyd_relaxation(density, sw, sh, n_cells=80, iters=7, seed=42):
    """加权 Lloyd 迭代松弛，使晶胞自适应聚集在主体细节/轮廓稠密处。"""
    rng = np.random.RandomState(seed)
    flat_p = density.ravel()
    total_p = flat_p.sum()
    if total_p <= 0:
        flat_p = np.ones_like(flat_p) / len(flat_p)
    else:
        flat_p = flat_p / total_p

    # 初始加权采样
    sampled_idx = rng.choice(sw * sh, size=n_cells, p=flat_p)
    sy, sx = np.unravel_index(sampled_idx, (sh, sw))
    seeds = np.column_stack([sx, sy]).astype(np.float64)

    # 离散快速加权 Lloyd 迭代
    ys, xs = np.indices((sh, sw))
    coords = np.column_stack([xs.ravel(), ys.ravel()]).astype(np.float64)
    w_flat = flat_p

    for _ in range(iters):
        tree = cKDTree(seeds)
        labels = tree.query(coords)[1]
        w_sum = np.bincount(labels, weights=w_flat, minlength=n_cells)
        x_sum = np.bincount(labels, weights=w_flat * coords[:, 0], minlength=n_cells)
        y_sum = np.bincount(labels, weights=w_flat * coords[:, 1], minlength=n_cells)

        valid = w_sum > 1e-8
        seeds[valid, 0] = x_sum[valid] / w_sum[valid]
        seeds[valid, 1] = y_sum[valid] / w_sum[valid]

        # 稀疏/空晶胞重新在稠密区注入微扰
        invalid = ~valid
        if np.any(invalid):
            re_idx = rng.choice(sw * sh, size=np.sum(invalid), p=flat_p)
            ry, rx = np.unravel_index(re_idx, (sh, sw))
            seeds[invalid, 0] = rx + rng.uniform(-1, 1, size=np.sum(invalid))
            seeds[invalid, 1] = ry + rng.uniform(-1, 1, size=np.sum(invalid))

    return seeds


def voronoi_fracture(input_path, out_path, cells=80, jitter=6.0, gap=2.0, seed=42):
    """执行加权 Voronoi 晶体应力碎裂，输出保持 Alpha 通道的碎裂贴纸。"""
    img = imread(input_path)
    h, w = img.shape[:2]
    alpha = img[:, :, 3]
    gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)

    if np.sum(alpha > 20) < 500:
        print(f"WARN: 输入图有效像素过少，直接透传原图")
        imwrite(out_path, img)
        return

    rng = np.random.RandomState(seed)

    # 1. 密度场与 Lloyd 松弛
    density, sw, sh = compute_density_field(gray, alpha, max_dim=350)
    seeds_small = weighted_lloyd_relaxation(density, sw, sh, n_cells=cells, iters=7, seed=seed)

    # 映射回原图坐标
    scale_x = w / sw
    scale_y = h / sh
    seeds = seeds_small.copy()
    seeds[:, 0] *= scale_x
    seeds[:, 1] *= scale_y

    # 2. 图像整体梯度场（用于应力方向计算）
    gx = cv2.Sobel(gray.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)

    # 3. Voronoi 空间划分与几何裁剪
    env = box(0, 0, w, h)
    v_diag = shapely.ops.voronoi_diagram(MultiPoint(seeds), envelope=env)

    # 准备画布与图层
    canvas_bgr = np.zeros((h, w, 3), dtype=np.float32)
    canvas_alpha = np.zeros((h, w), dtype=np.float32)

    # 阴影与切片缓冲
    shadow_bgr = np.zeros((h, w, 3), dtype=np.float32)
    shadow_alpha = np.zeros((h, w), dtype=np.float32)

    poly_list = []
    for geom in v_diag.geoms:
        clipped = geom.intersection(env)
        if clipped.is_empty or not isinstance(clipped, Polygon):
            continue
        poly_list.append(clipped)

    # 对晶胞按面积与位置排序，营造自然叠压次序
    poly_list.sort(key=lambda p: (p.centroid.y, p.centroid.x))

    for poly in poly_list:
        cx, cy = poly.centroid.x, poly.centroid.y
        ix, iy = int(np.clip(cx, 0, w - 1)), int(np.clip(cy, 0, h - 1))
        if alpha[iy, ix] < 15:
            # 晶胞中心在透明区域外，且相交面积过小时跳过
            continue

        # 晶胞向内收缩 gap
        shrunk = poly.buffer(-gap / 2.0)
        if shrunk.is_empty:
            continue
        if shrunk.geom_type == 'MultiPolygon':
            # 取面积最大的一块
            shrunk = max(shrunk.geoms, key=lambda g: g.area)
        if shrunk.area < 16:
            continue

        pts = np.array(shrunk.exterior.coords, dtype=np.float32)
        min_x = max(0, int(np.floor(pts[:, 0].min())))
        max_x = min(w, int(np.ceil(pts[:, 0].max())) + 1)
        min_y = max(0, int(np.floor(pts[:, 1].min())))
        max_y = min(h, int(np.ceil(pts[:, 1].max())) + 1)

        if max_x <= min_x or max_y <= min_y:
            continue

        # 提取切片局部掩膜
        local_mask = np.zeros((max_y - min_y, max_x - min_x), dtype=np.uint8)
        local_pts = pts.copy()
        local_pts[:, 0] -= min_x
        local_pts[:, 1] -= min_y
        cv2.fillPoly(local_mask, [np.int32(local_pts)], 255)

        # 结合原图透明通道
        local_alpha = img[min_y:max_y, min_x:max_x, 3]
        shard_alpha = (local_mask / 255.0) * (local_alpha / 255.0)
        if shard_alpha.sum() < 4.0:
            continue

        # 局部高精切片
        shard_bgr = img[min_y:max_y, min_x:max_x, :3].astype(np.float32)

        # 烘焙微小硬晶体白边 (1px bevel highlight)
        edge_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        edge_mask = cv2.morphologyEx((shard_alpha > 0.5).astype(np.uint8) * 255, cv2.MORPH_GRADIENT, edge_kernel)
        white_edge = (edge_mask / 255.0) * 0.45
        shard_bgr = shard_bgr * (1.0 - white_edge[:, :, None]) + 255.0 * white_edge[:, :, None]

        # 沿梯度方向计算应力位移与微旋转
        local_gx = gx[min_y:max_y, min_x:max_x]
        local_gy = gy[min_y:max_y, min_x:max_x]
        mgx = float(np.mean(local_gx[local_mask > 0])) if np.any(local_mask > 0) else 0.0
        mgy = float(np.mean(local_gy[local_mask > 0])) if np.any(local_mask > 0) else 0.0
        grad_angle = math.atan2(mgy, mgx)

        # 微小旋转与刚体平移
        d_angle = rng.uniform(-1.8, 1.8) * (jitter / 6.0)
        jitter_dist = rng.uniform(0.3, 1.0) * jitter
        shift_angle = grad_angle + rng.uniform(-0.6, 0.6)
        dx = math.cos(shift_angle) * jitter_dist
        dy = math.sin(shift_angle) * jitter_dist

        # 刚体仿射变换矩阵
        local_cx = cx - min_x
        local_cy = cy - min_y
        M = cv2.getRotationMatrix2D((local_cx, local_cy), d_angle, 1.0)
        M[0, 2] += dx
        M[1, 2] += dy

        # 变换切片图层
        pad = int(math.ceil(jitter + 4))
        pw = max_x - min_x + 2 * pad
        ph = max_y - min_y + 2 * pad
        M[0, 2] += pad
        M[1, 2] += pad

        warped_bgr = cv2.warpAffine(shard_bgr, M, (pw, ph), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        warped_alpha = cv2.warpAffine(shard_alpha, M, (pw, ph), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)

        # 贴回大图目标区域
        dst_x0 = min_x - pad
        dst_y0 = min_y - pad
        dst_x1 = dst_x0 + pw
        dst_y1 = dst_y0 + ph

        # 边界安全相交裁剪
        clip_x0 = max(0, dst_x0)
        clip_y0 = max(0, dst_y0)
        clip_x1 = min(w, dst_x1)
        clip_y1 = min(h, dst_y1)

        src_x0 = clip_x0 - dst_x0
        src_y0 = clip_y0 - dst_y0
        src_x1 = src_x0 + (clip_x1 - clip_x0)
        src_y1 = src_y0 + (clip_y1 - clip_y0)

        if clip_x1 > clip_x0 and clip_y1 > clip_y0:
            patch_a = warped_alpha[src_y0:src_y1, src_x0:src_x1]
            patch_rgb = warped_bgr[src_y0:src_y1, src_x0:src_x1]

            # 烘焙微小硬阴影 (+1.5px 偏移，深黑微透)
            sh_x0 = min(w, max(0, clip_x0 + 1))
            sh_y0 = min(h, max(0, clip_y0 + 2))
            sh_x1 = min(w, max(0, clip_x1 + 1))
            sh_y1 = min(h, max(0, clip_y1 + 2))
            sw_clip = sh_x1 - sh_x0
            sh_clip = sh_y1 - sh_y0
            if sw_clip > 0 and sh_clip > 0:
                cur_sha = shadow_alpha[sh_y0:sh_y1, sh_x0:sh_x1]
                add_sha = patch_a[:sh_clip, :sw_clip] * 0.35
                shadow_alpha[sh_y0:sh_y1, sh_x0:sh_x1] = np.maximum(cur_sha, add_sha)

            # Alpha Over 正向混合
            bg_a = canvas_alpha[clip_y0:clip_y1, clip_x0:clip_x1]
            bg_rgb = canvas_bgr[clip_y0:clip_y1, clip_x0:clip_x1]

            out_a = patch_a + bg_a * (1.0 - patch_a)
            out_rgb = (patch_rgb * patch_a[:, :, None] + bg_rgb * (bg_a * (1.0 - patch_a))[:, :, None]) / (out_a[:, :, None] + 1e-6)

            canvas_alpha[clip_y0:clip_y1, clip_x0:clip_x1] = out_a
            canvas_bgr[clip_y0:clip_y1, clip_x0:clip_x1] = out_rgb

    # 最终阴影与切片合成
    # 阴影垫在切片之下，但不溢出外部透明背景之外太远
    final_a = canvas_alpha + shadow_alpha * (1.0 - canvas_alpha)
    final_rgb = canvas_bgr * canvas_alpha[:, :, None] + 18.0 * (shadow_alpha * (1.0 - canvas_alpha))[:, :, None]
    final_rgb = final_rgb / (final_a[:, :, None] + 1e-6)

    out_rgba = np.dstack([
        np.clip(final_rgb, 0, 255).astype(np.uint8),
        np.clip(final_a * 255.0, 0, 255.0).astype(np.uint8)
    ])

    imwrite(out_path, out_rgba)
    print(f"OK [voronoi]: {out_path} ({w}x{h}, cells={cells}, jitter={jitter}px, gap={gap}px)")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", help="输入 RGBA 贴纸图片")
    p.add_argument("out", help="输出 RGBA 碎裂贴纸图片")
    p.add_argument("--cells", type=int, default=80, help="晶胞数量（默认 80）")
    p.add_argument("--jitter", type=float, default=6.0, help="应力刚体位移抖动像素（默认 6.0）")
    p.add_argument("--gap", type=float, default=2.0, help="晶胞缝隙宽度像素（默认 2.0）")
    p.add_argument("--seed", type=int, default=42, help="随机种子（默认 42）")
    args = p.parse_args()
    voronoi_fracture(args.input, args.out, cells=args.cells, jitter=args.jitter, gap=args.gap, seed=args.seed)


if __name__ == "__main__":
    main()
