import cv2
import numpy as np
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

def parse_rgb(rgb_str, default=(20, 22, 24)):
    try:
        parts = [float(x.strip()) for x in rgb_str.split(",")]
        if len(parts) == 3:
            return (parts[0], parts[1], parts[2])
    except Exception:
        pass
    return default

def apply_halftone_screen(
    input_path,
    output_path,
    dot_freq=0.55,
    blend=0.72,
    gamma=0.85,
    ink_rgb=(20, 22, 24),
    paper_rgb=(246, 242, 238),
    noise_strength=2.5,
    smooth_alpha=True
):
    """
    通用古典 45 度胶印半色调网点滤镜（Universal 45-degree Offset Lithography Halftone Screen）：
    1. 提取输入主体明度并进行伽马调制；
    2. 生成经典的 45 度正交网点空间图案；
    3. 模拟 1950s 复古胶印：暗部密实，中间调呈现清晰圆网点，高光微露微粒；
    4. 混合连续调保留五官微表情与明暗过渡；
    5. 调配复古油墨冷暖与做旧纸张白度，注入纸浆纤维微观颗粒；
    6. 完美继承并平滑 Alpha 通道。
    """
    img = read_image_utf8(input_path)
    if img is None:
        print(f"Error: Could not read input image: {input_path}")
        sys.exit(1)

    h, w = img.shape[:2]
    has_alpha = (img.ndim == 3 and img.shape[2] == 4)

    bgr = img[:, :, :3]
    if has_alpha:
        alpha = img[:, :, 3]
        if smooth_alpha:
            alpha_float = cv2.GaussianBlur(alpha.astype(np.float32), (3, 3), 0.8)
            alpha_clean = np.clip((alpha_float - 120.0) * 3.5 + 128.0, 0, 255).astype(np.uint8)
        else:
            alpha_clean = alpha.copy()
    else:
        alpha_clean = np.full((h, w), 255, dtype=np.uint8)

    # 1. 转换为灰度明度
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0

    # 2. 经典 45 度正交半色调网点调制图案 (45-degree Screen Angle)
    Y, X = np.mgrid[0:h, 0:w]
    dot_pattern = 0.5 * (np.sin(dot_freq * (X + Y)) * np.cos(dot_freq * (X - Y)) + 1.0)

    # 3. 网点阈值调制：暗部大网点，高光微小网点
    effective_gamma = max(0.1, gamma)
    halftone_mask = (dot_pattern < (1.0 - (gray ** effective_gamma))).astype(np.float32)

    # 4. 连续调与半色调网点混合（保留面部神态与自然过渡）
    effective_blend = np.clip(blend, 0.0, 1.0)
    ink_density = halftone_mask * effective_blend + (1.0 - gray) * (1.0 - effective_blend)
    ink_density = np.clip(ink_density, 0.0, 1.0)

    # 5. 复古印刷油墨调色（OpenCV 为 BGR 格式）
    # ink_rgb: (R, G, B) -> BGR: [B, G, R]
    ink_bgr = np.array([ink_rgb[2], ink_rgb[1], ink_rgb[0]], dtype=np.float32)
    paper_bgr = np.array([paper_rgb[2], paper_rgb[1], paper_rgb[0]], dtype=np.float32)

    halftone_bgr = paper_bgr.reshape(1, 1, 3) * (1.0 - ink_density[:, :, np.newaxis]) + ink_bgr.reshape(1, 1, 3) * ink_density[:, :, np.newaxis]

    # 6. 注入纸质纤维噪点
    if noise_strength > 0:
        noise = np.random.normal(0, noise_strength, (h, w, 1)).astype(np.float32)
        halftone_bgr = np.clip(halftone_bgr + noise, 0, 255)

    halftone_bgr = halftone_bgr.astype(np.uint8)

    # 7. 组装输出
    if has_alpha:
        out_bgra = np.dstack([halftone_bgr, alpha_clean])
    else:
        out_bgra = halftone_bgr

    write_image_utf8(output_path, out_bgra)
    print(f"Halftone Screen Success: {output_path} ({w}x{h}, freq={dot_freq}, blend={blend})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Universal 45-degree Offset Lithography Halftone Screen Filter")
    parser.add_argument("--input", "-i", required=True, help="Path to input image")
    parser.add_argument("--output", "-o", required=True, help="Path to output image (PNG)")
    parser.add_argument("--dot-freq", "-f", type=float, default=0.55, help="Halftone dot spatial frequency (default: 0.55)")
    parser.add_argument("--blend", "-b", type=float, default=0.72, help="Ratio of halftone dot mask vs continuous tone (default: 0.72)")
    parser.add_argument("--gamma", "-g", type=float, default=0.85, help="Gamma power adjustment for brightness curve (default: 0.85)")
    parser.add_argument("--ink-color", default="20,22,24", help="Ink RGB color comma separated (default: '20,22,24')")
    parser.add_argument("--paper-tone", default="246,242,238", help="Paper tone RGB color comma separated (default: '246,242,238')")
    parser.add_argument("--noise", "-n", type=float, default=2.5, help="Paper grain noise standard deviation (default: 2.5)")
    parser.add_argument("--no-smooth-alpha", dest="smooth_alpha", action="store_false", help="Disable alpha edge guided smoothing")
    parser.set_defaults(smooth_alpha=True)

    args = parser.parse_args()
    ink_rgb = parse_rgb(args.ink_color, (20, 22, 24))
    paper_rgb = parse_rgb(args.paper_tone, (246, 242, 238))

    apply_halftone_screen(
        input_path=args.input,
        output_path=args.output,
        dot_freq=args.dot_freq,
        blend=args.blend,
        gamma=args.gamma,
        ink_rgb=ink_rgb,
        paper_rgb=paper_rgb,
        noise_strength=args.noise,
        smooth_alpha=args.smooth_alpha
    )