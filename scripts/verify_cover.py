import cv2
import numpy as np
import sys
import os
import re
import argparse

def verify_html_source(html_path):
    """
    对拼贴 HTML 源码执行严谨的结构与美学文本断言：
    1. 检查是否存在 z-index 空间穿插（严禁文字全部置顶，必须有物理层叠深度）；
    2. 检查是否禁用了二次元贴纸风格的白色描边、外发光或模切白边；
    3. 检查是否杜绝了无意义的小英文、期号标签卡片、致敬字条与补白印章（防元指令与视觉杂质铁律）。
    """
    if not os.path.exists(html_path):
        print(f"INFO: HTML file {html_path} not found, skipping DOM source assertions.")
        return True
        
    with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
        html_content = f.read()
        
    lower_html = html_content.lower()
    
    # 1. 空间拓扑穿插断言（至少包含 2 级以上的不同 z-index 层叠）
    z_indices = re.findall(r'z-index\s*:\s*(-?\d+)', lower_html)
    unique_z = set(int(z) for z in z_indices)
    if len(unique_z) < 2:
        print(f"FAIL: HTML source '{html_path}' lacks topological z-index interleaving (found z-indices: {unique_z}).")
        print("      Collage art strictly requires physical interleaving (e.g. text pedestal z-index: 20, subject z-index: 40).")
        return False
    else:
        print(f"PASS: Topological z-index interleaving verified (layers found: {sorted(list(unique_z))}).")
        
    # 2. 禁用白色描边与人工发光断言
    forbidden_white_patterns = [
        (r'drop-shadow\([^)]*(?:#fff\b|#ffffff\b|white\b|rgba\(\s*255\s*,\s*255\s*,\s*255)[^)]*\)', "White drop-shadow sticker outline"),
        (r'stroke\s*:\s*(?:#fff\b|#ffffff\b|white\b|rgba\(\s*255\s*,\s*255\s*,\s*255)', "White SVG stroke outline"),
        (r'text-stroke\s*:[^;]*(?:#fff\b|#ffffff\b|white\b)', "White text stroke outline"),
    ]
    
    for pattern, desc in forbidden_white_patterns:
        match = re.search(pattern, lower_html)
        if match:
            print(f"FAIL: HTML source '{html_path}' contains forbidden sticker effect: {desc}!")
            print(f"      Matched pattern snippet: '{match.group(0)}'")
            print("      Collage art strictly forbids artificial white borders, die-cut outlines, and sticker glow.")
            return False
            
    print("PASS: Verified no artificial white sticker borders or drop-shadow halos in HTML source.")

    # 3. 禁用无意义小英文、期号膏药标签与伪装饰注脚断言
    forbidden_clutter_patterns = [
        (r'vol\.\s*\d+', "Forbidden volume/issue tag (e.g. VOL. 0219)"),
        (r'archive\s*no\.', "Forbidden archive number label (e.g. ARCHIVE NO.)"),
        (r'homage\b', "Forbidden meta homage text"),
        (r'collaboration\b', "Forbidden collaboration subtitle"),
        (r'archival-seal', "Forbidden faux decorative seal/stamp"),
        (r'archival-left-stamp', "Forbidden faux typewriter margin label"),
        (r'archival-right-index', "Forbidden faux typewriter index label"),
        (r'tag-text', "Forbidden metadata tag text container"),
    ]

    for pattern, desc in forbidden_clutter_patterns:
        match = re.search(pattern, lower_html)
        if match:
            print(f"FAIL: HTML source '{html_path}' contains forbidden visual clutter/meta text: {desc}!")
            print(f"      Matched pattern snippet: '{match.group(0)}'")
            print("      Master collage covers strictly forbid decorative tags, issue pills, English typewriter margin notes, and stamps.")
            return False

    print("PASS: Verified no forbidden meta tags, faux stamps, or tiny typewriter clutter in HTML source.")
    return True

def verify_cover(image_path, target_width=None, target_height=None, preset=None, html_path=None):
    if not os.path.exists(image_path):
        print(f"FAIL: Image {image_path} does not exist.")
        sys.exit(1)
        
    # 0. 产物落点红线校验（必须位于 _inbox/ 目录下）
    norm_path = os.path.normpath(os.path.abspath(image_path)).lower()
    inbox_marker = os.path.normpath("_inbox").lower()
    if inbox_marker not in norm_path:
        print(f"FAIL: Output path '{image_path}' violates red line! All AI outputs must reside in '_inbox/'.")
        sys.exit(1)

    # 预设尺寸推导
    preset_map = {
        "2.35:1": (2115, 900),
        "wechat": (2115, 900),
        "16:9": (1920, 1080),
        "landscape": (1920, 1080),
        "3:4": (1440, 1920),
        "xhs": (1440, 1920),
        "1:1": (900, 900),
        "crop": (900, 900),
    }

    if preset and preset.lower() in preset_map:
        target_width, target_height = preset_map[preset.lower()]
    elif target_width is None or target_height is None:
        # 自动由文件名识别常见画幅
        if "2115x900" in norm_path:
            target_width, target_height = 2115, 900
        elif "1920x1080" in norm_path:
            target_width, target_height = 1920, 1080
        elif "1440x1920" in norm_path:
            target_width, target_height = 1440, 1920
        elif "900x900" in norm_path or "1x1" in norm_path:
            target_width, target_height = 900, 900
        else:
            target_width, target_height = 2115, 900
        
    # 读取图片（兼容 Windows 中文路径）
    data = np.fromfile(image_path, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        print(f"FAIL: Unable to read image {image_path}")
        sys.exit(1)
        
    h, w = img.shape[:2]
    
    # 1. 物理分辨率硬指标断言
    if (w, h) != (target_width, target_height):
        print(f"FAIL: Dimensions {w}x{h} do not match expected {target_width}x{target_height}")
        sys.exit(1)
        
    # 2. 文件大小与基础熵检查（杜绝全黑/全白死图）
    file_size_kb = os.path.getsize(image_path) / 1024
    if file_size_kb < 50:
        print(f"FAIL: File size too small ({file_size_kb:.1f} KB), likely corrupt or blank.")
        sys.exit(1)
        
    std_dev = np.std(img)
    if std_dev < 15:
        print(f"FAIL: Image has near-zero standard deviation ({std_dev:.2f}), likely blank or single color.")
        sys.exit(1)
        
    # 3. HTML 源码断言（若指定或同名存在）
    if html_path is None:
        candidate_html = os.path.splitext(image_path)[0] + ".html"
        if os.path.exists(candidate_html):
            html_path = candidate_html
            
    if html_path:
        if not verify_html_source(html_path):
            sys.exit(1)
            
    print(f"PASS: Physical dimensions ({w}x{h}), inbox location, and structural assertions verified for {image_path}.")
    print("--------------------------------------------------------------------------------")
    print("[MANDATORY MULTIMODAL NOTICE]:")
    print("Technical scripts only verify resolution and data integrity.")
    print("Aesthetic quality, pureness, and visual impact MUST be visually inspected!")
    print("--------------------------------------------------------------------------------")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collage Cover Physical & Structural Sanity Assertion")
    parser.add_argument("image", help="Path to cover image")
    parser.add_argument("--width", "-w", type=int, default=None, help="Expected width")
    parser.add_argument("--height", "-ht", type=int, default=None, help="Expected height")
    parser.add_argument("--preset", "-p", choices=["2.35:1", "wechat", "16:9", "landscape", "3:4", "xhs", "1:1", "crop"], default=None, help="Preset aspect ratio")
    parser.add_argument("--html", type=str, default=None, help="Optional path to source HTML file for structural assertions")
    
    args = parser.parse_args()
    verify_cover(args.image, target_width=args.width, target_height=args.height, preset=args.preset, html_path=args.html)
