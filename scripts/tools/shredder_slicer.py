import cv2
import numpy as np
import math
import os
import sys
import argparse

def read_image_utf8(path, flags=cv2.IMREAD_UNCHANGED):
    if not os.path.exists(path):
        return None
    data = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(data, flags)

def write_image_utf8(path, img):
    ext = os.path.splitext(path)[1].lower()
    if not ext:
        ext = '.png'
    success, encoded = cv2.imencode(ext, img)
    if success:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        encoded.tofile(path)
        return True
    return False

def shredder_slice(
    input_path,
    output_path,
    strips=None,
    strip_width=6,
    displacement=35,
    bg_path=None,
    wave_freq=3.5,
    paper_edges=True
):
    """
    河村康辅式垂直切片位移碎纸机拼贴特效：
    1. 支持单图纯切片位移（垂直细条错位、波浪流动与交错抖动）；
    2. 支持前景 + 背景双图交织碎纸混合（如人物 + 宇宙星空、双重人像交替）；
    3. 条带左右边缘物理微光影（模拟剪裁纸条侧切面反光与厚度阴影）。
    """
    img = read_image_utf8(input_path)
    if img is None:
        print(f"Error: Could not read input image: {input_path}")
        sys.exit(1)

    h, w = img.shape[:2]
    has_alpha = (img.ndim == 3 and img.shape[2] == 4)
    if not has_alpha:
        img_rgba = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    else:
        img_rgba = img.copy()

    # 处理可选背景
    bg_rgba = None
    if bg_path and os.path.exists(bg_path):
        bg_raw = read_image_utf8(bg_path)
        if bg_raw is not None:
            if bg_raw.shape[:2] != (h, w):
                bg_raw = cv2.resize(bg_raw, (w, h), interpolation=cv2.INTER_LANCZOS4)
            if bg_raw.ndim == 3 and bg_raw.shape[2] == 4:
                bg_rgba = bg_raw
            else:
                bg_rgba = cv2.cvtColor(bg_raw, cv2.COLOR_BGR2BGRA)

    # 确定条带宽度与数量
    if strips is not None and strips > 0:
        actual_strip_w = max(1, w // strips)
        num_strips = strips
    else:
        actual_strip_w = max(1, strip_width)
        num_strips = math.ceil(w / actual_strip_w)

    output = np.zeros((h, w, 4), dtype=np.uint8)

    for i in range(num_strips):
        x0 = i * actual_strip_w
        x1 = min((i + 1) * actual_strip_w, w)
        cur_w = x1 - x0
        if cur_w <= 0:
            continue

        norm_i = i / float(max(1, num_strips))
        # 复合波动位移：宏观低频正弦波 + 高频偶次谐波 + 奇偶交替微抖动 + 4周期阶梯偏移
        macro_wave = displacement * math.sin(norm_i * wave_freq * math.pi) + (displacement * 0.4) * math.cos(norm_i * wave_freq * 2.0 * math.pi)
        alt_shift = (displacement * 0.35) if (i % 2 == 0) else -(displacement * 0.35)
        tier_shift = ((i % 4) - 1.5) * (displacement * 0.12)
        dy = int(round(macro_wave + alt_shift + tier_shift))

        strip_main = img_rgba[:, x0:x1].copy()
        disp_main = np.zeros_like(strip_main)

        if dy > 0:
            disp_main[dy:, :] = strip_main[:h - dy, :]
        elif dy < 0:
            disp_main[:h + dy, :] = strip_main[-dy:, :]
        else:
            disp_main = strip_main

        if bg_rgba is not None:
            strip_bg = bg_rgba[:, x0:x1].copy()
            disp_bg = np.zeros_like(strip_bg)
            dy_bg = int(round(dy * 1.15 - (displacement * 0.4)))
            if dy_bg > 0:
                disp_bg[dy_bg:, :] = strip_bg[:h - dy_bg, :]
            elif dy_bg < 0:
                disp_bg[:h + dy_bg, :] = strip_bg[-dy_bg:, :]
            else:
                disp_bg = strip_bg

            # 双图切片穿插融合
            p_rgb = disp_main[:, :, :3].astype(np.float32)
            p_a = disp_main[:, :, 3].astype(np.float32) / 255.0
            g_rgb = disp_bg[:, :, :3].astype(np.float32)
            g_a = disp_bg[:, :, 3].astype(np.float32) / 255.0

            out_rgb = np.zeros((h, cur_w, 3), dtype=np.float32)
            out_a = np.zeros((h, cur_w), dtype=np.float32)

            for y in range(h):
                norm_y = y / float(h)
                # 顶部更多背景，底部更多前景主体
                if norm_y < 0.45:
                    if i % 2 == 1:
                        w_bg, w_main = 0.92, 0.08
                    elif i % 4 == 0:
                        w_bg, w_main = 0.65, 0.35
                    else:
                        w_bg, w_main = 0.20, 0.90
                elif norm_y < 0.65:
                    if i % 2 == 1:
                        w_bg, w_main = 0.45, 0.75
                    else:
                        w_bg, w_main = 0.10, 1.00
                else:
                    w_bg, w_main = 0.0, 1.0

                eff_pa = p_a[y, :] * w_main
                eff_ga = g_a[y, :] * w_bg
                tot_a = eff_pa + eff_ga * (1.0 - eff_pa)
                denom = np.where(tot_a > 1e-4, tot_a, 1.0)[:, None]
                c = (p_rgb[y, :] * eff_pa[:, None] + g_rgb[y, :] * (eff_ga * (1.0 - eff_pa))[:, None]) / denom

                out_rgb[y, :] = c
                out_a[y, :] = tot_a

            strip_res = np.zeros((h, cur_w, 4), dtype=np.uint8)
            strip_res[:, :, :3] = np.clip(out_rgb, 0, 255).astype(np.uint8)
            strip_res[:, :, 3] = np.clip(out_a * 255.0, 0, 255).astype(np.uint8)
        else:
            strip_res = disp_main

        # 模拟真实剪纸/切片物理边缘（左侧受光增亮，右侧背光微暗）
        if paper_edges and cur_w >= 2:
            left_mask = strip_res[:, 0, 3] > 15
            strip_res[left_mask, 0, :3] = np.clip(strip_res[left_mask, 0, :3].astype(np.int16) + 24, 0, 255).astype(np.uint8)
            right_mask = strip_res[:, -1, 3] > 15
            strip_res[right_mask, -1, :3] = (strip_res[right_mask, -1, :3].astype(np.float32) * 0.75).astype(np.uint8)

        output[:, x0:x1] = strip_res

    write_image_utf8(output_path, output)
    print(f"Shredder Slicer Success: {output_path} ({w}x{h}, strips={num_strips}, strip_w={actual_strip_w}, disp={displacement})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kosuke Kawamura-style Vertical Shredder Slicer Collage Effect")
    parser.add_argument("--input", "-i", required=True, help="Path to input image (subject or composite)")
    parser.add_argument("--output", "-o", required=True, help="Path to output image (PNG/JPG)")
    parser.add_argument("--strips", "-s", type=int, default=None, help="Total number of vertical strips (overrides --strip-width)")
    parser.add_argument("--strip-width", "-w", type=int, default=6, help="Width of each strip in pixels (default: 6)")
    parser.add_argument("--displacement", "-d", type=int, default=35, help="Maximum vertical displacement in pixels (default: 35)")
    parser.add_argument("--background", "-bg", default=None, help="Optional background image for alternating interlaced shredder collage")
    parser.add_argument("--wave-freq", type=float, default=3.5, help="Frequency of macro wave displacement (default: 3.5)")
    parser.add_argument("--no-paper-edges", dest="paper_edges", action="store_false", help="Disable physical cut edge highlight and shadow")
    parser.set_defaults(paper_edges=True)

    args = parser.parse_args()
    shredder_slice(
        input_path=args.input,
        output_path=args.output,
        strips=args.strips,
        strip_width=args.strip_width,
        displacement=args.displacement,
        bg_path=args.background,
        wave_freq=args.wave_freq,
        paper_edges=args.paper_edges
    )