"""河村康辅碎纸机垂直条纹解构算子 (Kosuke Kawamura Vertical Shredder Strips)

向日本当代拼贴艺术巨擘河村康辅（Kosuke Kawamura，以《AKIRA》艺术展与碎纸机重组肖像闻名）致敬。
将主体人像/物件通过高密度垂直碎纸机切片，并结合多频谐波波浪位移、拉链式微错动（Zipper Stagger）
与刀口物理微阴影（Slit Shadow & Paper Core Highlight），产生兼具模拟手作胶水拼贴与数字故障张力的前卫质感。
"""
import os
import sys
import math
import cv2
import numpy as np


def imread(path):
    if not os.path.exists(path):
        sys.exit(f"FAIL: 文件不存在 {path}")
    data = np.fromfile(path, np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
    if img is None or img.ndim < 3 or img.shape[2] != 4:
        sys.exit(f"FAIL: 输入图不是有效的 RGBA PNG: {path}")
    return img


def imsave(path, img):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    ext = os.path.splitext(path)[1]
    ok, buf = cv2.imencode(ext, img)
    if not ok:
        sys.exit(f"FAIL: 编码图像失败 {path}")
    buf.tofile(path)


def kawamura_shred(input_path, out_path,
                   strips=70,
                   amplitude=50.0,
                   freq=2.5,
                   stagger=16.0,
                   jitter=10.0,
                   mode="wave",
                   slit_relief=True,
                   seed=42):
    """
    河村康辅垂直碎纸机条纹重组。
    
    参数：
      strips: 垂直切条总数（默认 70 根）
      amplitude: 宏观波浪最大位移量（像素，默认 50.0）
      freq: 横向正弦波周期数（默认 2.5）
      stagger: 相邻纸条交替跳跃位移量（像素，默认 16.0，形成河村标志性的拉链式破碎感）
      jitter: 随机块滑移抖动量（像素，默认 10.0）
      mode: 位移模式 ('wave' | 'stagger' | 'glitch')
      slit_relief: 是否渲染刀口微阴影与切边浮雕质感（默认 True）
      seed: 随机种子
    """
    rng = np.random.RandomState(seed)
    src = imread(input_path)
    h, w = src.shape[:2]

    # 1. 查找内容有效边界 (Bounding Box)
    alpha = src[:, :, 3]
    ys, xs = np.where(alpha > 10)
    if len(xs) == 0:
        sys.exit("FAIL: 输入图全透明")
    min_x, max_x = int(np.min(xs)), int(np.max(xs))
    content_w = max_x - min_x + 1

    # 计算切片边界
    num_strips = max(10, int(strips))
    step = content_w / float(num_strips)
    strip_bounds = []
    for i in range(num_strips):
        x0 = int(round(min_x + i * step))
        x1 = int(round(min_x + (i + 1) * step)) if i < num_strips - 1 else (max_x + 1)
        if x1 > x0:
            strip_bounds.append((x0, x1))

    # 2. 计算每个切条的垂直位移量 dy
    N = len(strip_bounds)
    shifts = np.zeros(N, dtype=np.float32)

    cluster_offset = 0.0
    cluster_rem = 0

    for i in range(N):
        norm_x = float(i) / max(1, N - 1)
        if mode == "wave":
            w1 = math.sin(2.0 * math.pi * freq * norm_x)
            w2 = 0.35 * math.sin(4.0 * math.pi * freq * norm_x + 0.9)
            base_dy = amplitude * (w1 + w2)
        elif mode == "stagger":
            base_dy = amplitude * math.sin(1.0 * math.pi * norm_x)
        elif mode == "glitch":
            base_dy = amplitude * math.sin(1.5 * math.pi * norm_x)
        else:
            base_dy = 0.0

        # 河村标志性交替跳动 (Alternating Zipper Offset)
        alt_dy = stagger * (1.0 if (i % 2 == 0) else -1.0)

        # 连续群组滑移 (Cluster Slippage)
        if cluster_rem <= 0:
            cluster_offset = rng.uniform(-jitter, jitter)
            cluster_rem = rng.randint(2, 5)
        else:
            cluster_rem -= 1

        strip_noise = rng.uniform(-jitter * 0.3, jitter * 0.3)
        shifts[i] = base_dy + alt_dy + cluster_offset + strip_noise

    # 3. 创建目标画布（高度适度扩充）
    max_up = int(math.ceil(max(0.0, -np.min(shifts))))
    max_down = int(math.ceil(max(0.0, np.max(shifts))))
    pad_y = max(max_up, max_down) + 30

    out_h = h + 2 * pad_y
    out_w = w
    canvas_bgr = np.zeros((out_h, out_w, 3), dtype=np.float32)
    canvas_a = np.zeros((out_h, out_w), dtype=np.float32)

    # 4. 逐条拼装
    for i, (x0, x1) in enumerate(strip_bounds):
        dy = int(round(shifts[i]))
        strip = src[:, x0:x1]
        sw = x1 - x0
        sh = h

        dst_y0 = pad_y + dy
        dst_y1 = dst_y0 + sh
        dst_x0 = x0
        dst_x1 = x1

        strip_bgr = strip[:, :, :3].astype(np.float32).copy()
        strip_a = (strip[:, :, 3].astype(np.float32)) / 255.0

        # 刀口微浮雕与物理阴影 (Slit Relief)
        if slit_relief and sw >= 3:
            # 左侧刀口微高光（模拟切口纤维微光）
            strip_bgr[:, 0] = np.clip(strip_bgr[:, 0] * 1.15 + 15.0, 0.0, 255.0)
            # 右侧切刀微暗影（1~2px 阴影深度）
            strip_bgr[:, -1] = strip_bgr[:, -1] * 0.72
            if sw >= 4:
                strip_bgr[:, -2] = strip_bgr[:, -2] * 0.88

        # 叠压纸条到画布
        c_a = canvas_a[dst_y0:dst_y1, dst_x0:dst_x1]
        c_bgr = canvas_bgr[dst_y0:dst_y1, dst_x0:dst_x1]

        out_a = strip_a + c_a * (1.0 - strip_a)
        blend_mask = np.where(out_a > 1e-5, strip_a / np.maximum(out_a, 1e-5), 0.0)[:, :, None]
        new_bgr = strip_bgr * blend_mask + c_bgr * (1.0 - blend_mask)

        canvas_a[dst_y0:dst_y1, dst_x0:dst_x1] = out_a
        canvas_bgr[dst_y0:dst_y1, dst_x0:dst_x1] = new_bgr

    # 5. 裁剪回原图比例，无缝适配既有排版图层
    result_bgr = canvas_bgr[pad_y:pad_y + h, 0:w]
    result_a = canvas_a[pad_y:pad_y + h, 0:w]

    final_rgba = np.dstack([
        np.clip(result_bgr, 0.0, 255.0).astype(np.uint8),
        np.clip(result_a * 255.0, 0.0, 255.0).astype(np.uint8)
    ])

    imsave(out_path, final_rgba)
    print(f"OK (Kawamura Shred): 已生成河村康辅垂直条纹重组贴纸 → {out_path} (strips={num_strips}, amp={amplitude}px, stagger={stagger}px)")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", help="输入 RGBA 贴纸图片")
    p.add_argument("out", help="输出 RGBA 贴纸图片")
    p.add_argument("--strips", type=int, default=70, help="垂直切条数量（默认 70）")
    p.add_argument("--amplitude", type=float, default=50.0, help="波浪最大位移像素（默认 50.0）")
    p.add_argument("--freq", type=float, default=2.5, help="波浪频率周期（默认 2.5）")
    p.add_argument("--stagger", type=float, default=16.0, help="交替跳跃位移像素（默认 16.0）")
    p.add_argument("--jitter", type=float, default=10.0, help="随机滑移抖动像素（默认 10.0）")
    p.add_argument("--mode", choices=["wave", "stagger", "glitch"], default="wave")
    p.add_argument("--seed", type=int, default=42)
    a = p.parse_args()
    kawamura_shred(a.input, a.out, strips=a.strips, amplitude=a.amplitude,
                   freq=a.freq, stagger=a.stagger, jitter=a.jitter, mode=a.mode, seed=a.seed)
