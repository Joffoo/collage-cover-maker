import os
import sys
import argparse
import cv2
import numpy as np

def generate_paper_texture(w, h, base_rgb, fiber_density=0.0008, grain_sigma=3.2):
    """
    Synthesize physical cardstock paper texture with multi-scale fiber clouds,
    cellulose strands, micro-pores, and tactile surface tooth.
    Output is in standard OpenCV BGR order.
    """
    # 1. Base color fill (convert RGB to BGR)
    r_val, g_val, b_val = base_rgb
    base_bgr = (float(b_val), float(g_val), float(r_val))
    canvas = np.full((h, w, 3), base_bgr, dtype=np.float32)

    # 2. Multi-scale cloud variations (large-scale pulp density shifts)
    c_large = cv2.resize(np.random.normal(0, 1, (max(4, h // 64) + 1, max(4, w // 64) + 1)), (w, h), interpolation=cv2.INTER_CUBIC)
    c_med = cv2.resize(np.random.normal(0, 1, (max(4, h // 16) + 1, max(4, w // 16) + 1)), (w, h), interpolation=cv2.INTER_CUBIC)
    c_small = cv2.resize(np.random.normal(0, 1, (max(4, h // 4) + 1, max(4, w // 4) + 1)), (w, h), interpolation=cv2.INTER_CUBIC)
    
    pulp_var = (c_large * 4.0 + c_med * 2.5 + c_small * 1.5)
    canvas += np.repeat(pulp_var[:, :, np.newaxis], 3, axis=2)

    # 3. Microscopic paper surface tooth (monochromatic grain)
    tooth = np.random.normal(0, grain_sigma, (h, w, 1))
    canvas += tooth

    # 4. Realistic organic cellulose fibers (random curved strands)
    num_fibers = int(w * h * fiber_density)
    fiber_overlay = np.zeros((h, w, 3), dtype=np.float32)
    fiber_alpha = np.zeros((h, w), dtype=np.float32)

    for _ in range(num_fibers):
        x0 = np.random.randint(0, w)
        y0 = np.random.randint(0, h)
        length = np.random.randint(8, 35)
        angle = np.random.uniform(0, 2 * np.pi)
        curvature = np.random.uniform(-0.08, 0.08)
        
        # Color in BGR: either darker cellulose or lighter bleached cotton strand
        is_light = np.random.rand() > 0.5
        if is_light:
            f_color = np.array([250.0, 255.0, 255.0], dtype=np.float32) # BGR
            f_opacity = np.random.uniform(0.12, 0.28)
        else:
            f_color = np.array([base_bgr[0] * 0.65, base_bgr[1] * 0.70, base_bgr[2] * 0.72], dtype=np.float32) # BGR
            f_opacity = np.random.uniform(0.15, 0.35)

        pts = []
        cx, cy, cur_angle = float(x0), float(y0), angle
        for _ in range(length):
            pts.append([int(cx), int(cy)])
            cx += np.cos(cur_angle)
            cy += np.sin(cur_angle)
            cur_angle += curvature
        
        pts = np.array(pts, dtype=np.int32)
        if len(pts) > 1:
            thickness = 1 if np.random.rand() > 0.15 else 2
            cv2.polylines(fiber_alpha, [pts], isClosed=False, color=f_opacity, thickness=thickness)
            cv2.polylines(fiber_overlay, [pts], isClosed=False, color=f_color.tolist(), thickness=thickness)

    # Blend fibers onto canvas
    f_mask = np.clip(fiber_alpha[:, :, np.newaxis], 0, 1)
    canvas = canvas * (1.0 - f_mask) + fiber_overlay * f_mask
    return np.clip(canvas, 0, 255).astype(np.uint8)

def apply_paper_edge_bevel(mask, light_dir=(-0.6, -0.8)):
    """
    Simulate physical paper cardstock edge bevel:
    Calculates surface normal around cut perimeter to produce natural specular
    highlights on the lit side and micro-crease shadows on the shadow side.
    """
    dist_in = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    sobel_x = cv2.Sobel(dist_in, cv2.CV_32F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(dist_in, cv2.CV_32F, 0, 1, ksize=3)
    norm = np.sqrt(sobel_x**2 + sobel_y**2) + 1e-5
    nx = sobel_x / norm
    ny = sobel_y / norm
    
    lx, ly = light_dir
    l_len = np.sqrt(lx**2 + ly**2)
    lx, ly = lx / l_len, ly / l_len
    
    dot = nx * lx + ny * ly
    edge_zone = (dist_in >= 0.5) & (dist_in <= 3.2)
    
    bevel_layer = np.zeros_like(dist_in, dtype=np.float32)
    bevel_layer[edge_zone] = dot[edge_zone] * 28.0
    return bevel_layer

def generate_fractal_1d_noise(length, octaves=4, persistence=0.5, scale=2.5):
    """
    利用多阶一维分形插值噪点生成自然物理撕裂边缘。
    """
    noise = np.zeros(length, dtype=np.float32)
    freq = 1.0
    amp = scale
    for _ in range(octaves):
        n_pts = max(4, int(length * freq / 35.0))
        pts = np.random.normal(0, 1, n_pts)
        interp = cv2.resize(pts.reshape(1, -1), (length, 1), interpolation=cv2.INTER_CUBIC).flatten()
        noise += interp * amp
        freq *= 2.0
        amp *= persistence
    return noise

def generate_procedural_hubble_nebula(size=1000):
    """
    程序化合成真实感哈勃深空星云与星尘背景（纯本地算法，无需外部素材或联网下载）。
    """
    space = np.zeros((size, size, 3), dtype=np.float32)
    # 深邃宇宙底色：微暗深靛紫 [B, G, R] = [18, 10, 14]
    space[:, :] = [18.0, 10.0, 14.0]
    
    # 1. 多尺度星云气体云团
    # 紫红/品红星云气团
    c1 = cv2.resize(np.random.normal(0, 1, (size // 32, size // 32)), (size, size), interpolation=cv2.INTER_CUBIC)
    c1 = cv2.GaussianBlur(c1, (61, 61), 25.0)
    c1 = np.clip((c1 - c1.min()) / (c1.max() - c1.min() + 1e-5), 0, 1)
    
    # 碧青/电光蓝星际气体
    c2 = cv2.resize(np.random.normal(0, 1, (size // 48, size // 48)), (size, size), interpolation=cv2.INTER_CUBIC)
    c2 = cv2.GaussianBlur(c2, (81, 81), 35.0)
    c2 = np.clip((c2 - c2.min()) / (c2.max() - c2.min() + 1e-5), 0, 1)
    
    # 琥珀/金黄电离激波带
    c3 = cv2.resize(np.random.normal(0, 1, (size // 24, size // 24)), (size, size), interpolation=cv2.INTER_CUBIC)
    c3 = cv2.GaussianBlur(c3, (41, 41), 18.0)
    c3 = np.clip((c3 - c3.min()) / (c3.max() - c3.min() + 1e-5), 0, 1)
    
    # 气体云团色阶叠加 (BGR)
    space += (c1[:, :, np.newaxis] ** 1.6) * np.array([170.0, 35.0, 200.0], dtype=np.float32)
    space += (c2[:, :, np.newaxis] ** 1.8) * np.array([210.0, 160.0, 30.0], dtype=np.float32)
    space += (c3[:, :, np.newaxis] ** 2.2) * np.array([30.0, 130.0, 220.0], dtype=np.float32)
    
    # 2. 繁星点缀
    num_stars = int(size * size * 0.0018)
    star_layer = np.zeros((size, size, 3), dtype=np.float32)
    for _ in range(num_stars):
        sx = np.random.randint(0, size)
        sy = np.random.randint(0, size)
        brightness = np.random.uniform(120, 255)
        star_layer[sy, sx] = np.array([255.0, 245.0, 235.0]) * (brightness / 255.0)
        
    # 明亮焦点恒星带衍射十字光芒
    for _ in range(12):
        bx = np.random.randint(size // 8, 7 * size // 8)
        by = np.random.randint(size // 8, 7 * size // 8)
        cv2.circle(star_layer, (bx, by), 2, (255, 255, 255), -1)
        arm = np.random.randint(8, 22)
        cv2.line(star_layer, (bx - arm, by), (bx + arm, by), (220, 235, 255), 1)
        cv2.line(star_layer, (bx, by - arm), (bx, by + arm), (220, 235, 255), 1)
        
    star_glow = cv2.GaussianBlur(star_layer, (7, 7), 1.5)
    space += star_layer + star_glow * 0.5
    return np.clip(space, 0, 255).astype(np.uint8)

def make_scissor_cut_circle(center, radius, num_bites=120, jitter=1.4):
    cx, cy = center
    angles = np.linspace(0, 2 * np.pi, num_bites, endpoint=False)
    pts = []
    for a in angles:
        r = radius + np.random.normal(0, jitter)
        if np.random.rand() < 0.08:
            r += np.random.uniform(1.0, 2.5)
        px = cx + r * np.cos(a)
        py = cy + r * np.sin(a)
        pts.append([px, py])
    return np.array(pts, dtype=np.int32)

def make_scissor_cut_arch(x, y, w, h, num_arch_bites=60, jitter=1.3):
    r = w / 2.0
    cx = x + r
    cy = y + r
    
    pts = []
    arch_angles = np.linspace(np.pi, 0, num_arch_bites)
    for a in arch_angles:
        curr_r = r + np.random.normal(0, jitter)
        if np.random.rand() < 0.06:
            curr_r += np.random.uniform(1.0, 2.2)
        px = cx + curr_r * np.cos(a)
        py = cy - curr_r * np.sin(a)
        pts.append([px, py])
        
    right_x = x + w
    for sy in np.linspace(cy, y + h, 20):
        px = right_x + np.random.normal(0, jitter * 0.7)
        pts.append([px, sy])
        
    for sx in np.linspace(right_x, x, 20):
        py = y + h + np.random.normal(0, jitter * 0.7)
        pts.append([sx, py])
        
    for sy in np.linspace(y + h, cy, 20):
        px = x + np.random.normal(0, jitter * 0.7)
        pts.append([px, sy])
        
    return np.array(pts, dtype=np.int32)

def make_scissor_cut_rect(x, y, w, h, num_bites_w=40, num_bites_h=15, jitter=1.2):
    pts = []
    for sx in np.linspace(x, x + w, num_bites_w):
        py = y + np.random.normal(0, jitter * 0.7)
        pts.append([sx, py])
    for sy in np.linspace(y, y + h, num_bites_h):
        px = x + w + np.random.normal(0, jitter * 0.7)
        pts.append([px, sy])
    for sx in np.linspace(x + w, x, num_bites_w):
        py = y + h + np.random.normal(0, jitter * 0.7)
        pts.append([sx, py])
    for sy in np.linspace(y + h, y, num_bites_h):
        px = x + np.random.normal(0, jitter * 0.7)
        pts.append([px, sy])
    return np.array(pts, dtype=np.int32)

def generate_torn_strip(output_path, w=1400, h=320, base_rgb=(248, 244, 236)):
    """
    程序化生成带有纤维毛边的 Toon Joosen 撕边字条纸基：
    1. 基于一维分形插值噪点构建微观凹凸毛边轮廓；
    2. 模拟物理撕纸产生的内部露白纸芯纤维斜切坡口（Torn White Core Bevel）；
    3. 合成带有原木纤维沉淀与纸纹微孔的厚质卡纸。
    """
    print(f"Generating torn paper strip: {output_path} ({w}x{h})...")
    margin_y = 35
    margin_x = 25
    
    # 1. 利用一维分形噪点生成上下与左右撕裂轮廓
    noise_top = generate_fractal_1d_noise(w, octaves=5, persistence=0.55, scale=4.5)
    noise_bot = generate_fractal_1d_noise(w, octaves=5, persistence=0.55, scale=4.5)
    noise_left = generate_fractal_1d_noise(h, octaves=4, persistence=0.5, scale=2.5)
    noise_right = generate_fractal_1d_noise(h, octaves=4, persistence=0.5, scale=2.5)
    
    pts = []
    # 顶部边缘 (从左到右)
    for x in range(margin_x, w - margin_x, 3):
        y = margin_y + noise_top[x]
        pts.append([x, int(y)])
        
    # 右侧边缘 (从上到下)
    for y in range(margin_y, h - margin_y, 4):
        x = (w - margin_x) + noise_right[y]
        pts.append([int(x), y])
        
    # 底部边缘 (从右到左)
    for x in range(w - margin_x, margin_x, -3):
        y = (h - margin_y) + noise_bot[x]
        pts.append([x, int(y)])
        
    # 左侧边缘 (从下到上)
    for y in range(h - margin_y, margin_y, -4):
        x = margin_x + noise_left[y]
        pts.append([int(x), y])
        
    poly_pts = np.array(pts, dtype=np.int32)
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(mask, [poly_pts], 255)
    
    # 2. 合成基础纸张肌理
    paper_bgr = generate_paper_texture(w, h, base_rgb, fiber_density=0.0007, grain_sigma=2.8)
    
    # 3. 模拟物理撕裂露出的内芯白纸纤维坡口 (Torn Core Fiber Bevel)
    dist_in = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    core_zone = (dist_in >= 0.5) & (dist_in <= 4.0)
    
    paper_floated = paper_bgr.astype(np.float32)
    # 在撕裂边缘高光强化露白纤维
    paper_floated[core_zone] = np.clip(
        paper_floated[core_zone] * 0.45 + np.array([252.0, 250.0, 248.0], dtype=np.float32) * 0.55, 
        0, 255
    )
    
    # 4. 微观光影斜切增强
    bevel = apply_paper_edge_bevel(mask, light_dir=(-0.5, -0.85))
    paper_floated += bevel[:, :, np.newaxis]
    final_paper_bgr = np.clip(paper_floated, 0, 255).astype(np.uint8)
    
    bgra = np.dstack([final_paper_bgr, mask])
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    cv2.imwrite(output_path, bgra)
    print(f"-> Saved Torn Paper Strip: {output_path}")

def generate_vintage_paper_canvas(output_path, w=2500, h=2500):
    print(f"Generating vintage paper canvas: {output_path} ({w}x{h})...")
    base_beige_rgb = (245, 239, 235) # #F5EFEB
    paper_bgr = generate_paper_texture(w, h, base_beige_rgb, fiber_density=0.0006, grain_sigma=3.5).astype(np.float32)
    
    # 1. Subtle folding creases
    for _ in range(3):
        p1 = (np.random.randint(0, w), 0)
        p2 = (np.random.randint(0, w), h)
        crease_mask = np.zeros((h, w), dtype=np.float32)
        cv2.line(crease_mask, p1, p2, 1.0, 2)
        crease_blur_light = cv2.GaussianBlur(crease_mask, (15, 15), 3.0)
        crease_blur_dark = cv2.GaussianBlur(crease_mask, (25, 25), 5.0)
        M = np.float32([[1, 0, 2], [0, 1, 2]])
        crease_shifted = cv2.warpAffine(crease_blur_light, M, (w, h))
        paper_bgr += (crease_shifted * 5.0 - crease_blur_dark * 6.0)[:, :, np.newaxis]

    # 2. Tea stain rings (in BGR: -8 B, -5 G, -3 R)
    for _ in range(2):
        sx = np.random.randint(w // 4, 3 * w // 4)
        sy = np.random.randint(h // 4, 3 * h // 4)
        sr = np.random.randint(80, 160)
        stain_canvas = np.zeros((h, w), dtype=np.float32)
        cv2.circle(stain_canvas, (sx, sy), sr, 1.0, -1)
        stain_edge = cv2.Canny((stain_canvas * 255).astype(np.uint8), 50, 150).astype(np.float32) / 255.0
        stain_ring = cv2.GaussianBlur(stain_edge, (21, 21), 6.0)
        stain_tint = np.array([[-8.0, -5.0, -3.0]], dtype=np.float32)
        paper_bgr += stain_ring[:, :, np.newaxis] * stain_tint

    # 3. Oxidation vignette (in BGR: -22 B, -11 G, -4 R)
    Y, X = np.ogrid[:h, :w]
    dist_from_center = np.sqrt(((X - w / 2.0) / (w / 2.0))**2 + ((Y - h / 2.0) / (h / 2.0))**2)
    vignette = np.clip((dist_from_center - 0.5) / 0.8, 0, 1.0)
    vig_shift = np.array([[-22.0, -11.0, -4.0]], dtype=np.float32)
    paper_bgr += (vignette[:, :, np.newaxis] ** 1.8) * vig_shift

    final_paper = np.clip(paper_bgr, 0, 255).astype(np.uint8)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    cv2.imwrite(output_path, final_paper, [int(cv2.IMWRITE_JPEG_QUALITY), 96])
    print(f"-> Saved: {output_path}")

def generate_papercut_arch(output_path, w=1000, h=1450):
    print(f"Generating terracotta red papercut arch: {output_path} ({w}x{h})...")
    margin_x = 50
    margin_top = 50
    margin_bottom = 50
    arch_w = w - 2 * margin_x
    arch_h = h - margin_top - margin_bottom
    
    pts = make_scissor_cut_arch(margin_x, margin_top, arch_w, arch_h, num_arch_bites=80, jitter=1.4)
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(mask, [pts], 255)
    
    # Terracotta Red RGB: [226, 74, 50]
    base_rgb = (226, 74, 50)
    paper_bgr = generate_paper_texture(w, h, base_rgb, fiber_density=0.0006, grain_sigma=3.0)
    
    bevel = apply_paper_edge_bevel(mask, light_dir=(-0.6, -0.8))
    paper_floated = paper_bgr.astype(np.float32) + bevel[:, :, np.newaxis]
    paper_bgr = np.clip(paper_floated, 0, 255).astype(np.uint8)
    
    bgra = np.dstack([paper_bgr, mask])
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    cv2.imwrite(output_path, bgra)
    print(f"-> Saved: {output_path}")

def generate_papercut_disc(output_path, size=1200):
    print(f"Generating slate teal papercut disc: {output_path} ({size}x{size})...")
    margin = 40
    radius = (size - 2 * margin) / 2.0
    center = (size // 2, size // 2)
    
    pts = make_scissor_cut_circle(center, radius, num_bites=140, jitter=1.5)
    mask = np.zeros((size, size), dtype=np.uint8)
    cv2.fillPoly(mask, [pts], 255)
    
    # Slate Teal RGB: [45, 72, 94]
    base_rgb = (45, 72, 94)
    paper_bgr = generate_paper_texture(size, size, base_rgb, fiber_density=0.0005, grain_sigma=2.8)
    
    bevel = apply_paper_edge_bevel(mask, light_dir=(-0.6, -0.8))
    paper_floated = paper_bgr.astype(np.float32) + bevel[:, :, np.newaxis]
    paper_bgr = np.clip(paper_floated, 0, 255).astype(np.uint8)
    
    bgra = np.dstack([paper_bgr, mask])
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    cv2.imwrite(output_path, bgra)
    print(f"-> Saved: {output_path}")

def generate_papercut_portal_galaxy(galaxy_img_path=None, output_path=None, size=1000):
    print(f"Generating Joe Webb cosmic portal: {output_path} ({size}x{size})...")
    if galaxy_img_path and os.path.exists(galaxy_img_path):
        galaxy_src = cv2.imread(galaxy_img_path, cv2.IMREAD_COLOR)
        galaxy_resized = cv2.resize(galaxy_src, (size, size), interpolation=cv2.INTER_LANCZOS4)
        print(f"Using provided galaxy base: {galaxy_img_path}")
    else:
        print("No galaxy base provided or file not found. Synthesizing procedural Hubble deep nebula...")
        galaxy_resized = generate_procedural_hubble_nebula(size)
    
    center = (size // 2, size // 2)
    outer_radius = size * 0.47
    inner_radius = size * 0.39
    
    outer_pts = make_scissor_cut_circle(center, outer_radius, num_bites=120, jitter=1.4)
    outer_mask = np.zeros((size, size), dtype=np.uint8)
    cv2.fillPoly(outer_mask, [outer_pts], 255)
    
    inner_pts = make_scissor_cut_circle(center, inner_radius, num_bites=100, jitter=1.3)
    inner_mask = np.zeros((size, size), dtype=np.uint8)
    cv2.fillPoly(inner_mask, [inner_pts], 255)
    
    rim_mask = cv2.subtract(outer_mask, inner_mask)
    
    # Dark charcoal textured thick cardboard RGB: [28, 32, 38]
    rim_paper = generate_paper_texture(size, size, (28, 32, 38), fiber_density=0.0008, grain_sigma=3.2)
    outer_bevel = apply_paper_edge_bevel(outer_mask, light_dir=(-0.6, -0.8))
    
    dist_from_hole = cv2.distanceTransform(cv2.bitwise_not(inner_mask), cv2.DIST_L2, 5)
    core_zone = (dist_from_hole >= 0.5) & (dist_from_hole <= 3.5) & (rim_mask == 255)
    
    rim_floated = rim_paper.astype(np.float32) + outer_bevel[:, :, np.newaxis]
    rim_floated[core_zone] = np.clip(rim_floated[core_zone] * 0.35 + np.array([215.0, 220.0, 230.0], dtype=np.float32) * 0.65, 0, 255)
    rim_paper = np.clip(rim_floated, 0, 255).astype(np.uint8)
    
    composite_bgr = np.zeros((size, size, 3), dtype=np.uint8)
    galaxy_floated = galaxy_resized.astype(np.float32)
    dist_from_rim = cv2.distanceTransform(inner_mask, cv2.DIST_L2, 5)
    inner_shadow = np.clip(dist_from_rim / 18.0, 0.40, 1.0)[:, :, np.newaxis]
    galaxy_floated *= inner_shadow
    galaxy_final = np.clip(galaxy_floated, 0, 255).astype(np.uint8)
    
    inner_idx = inner_mask == 255
    composite_bgr[inner_idx] = galaxy_final[inner_idx]
    
    rim_idx = rim_mask == 255
    composite_bgr[rim_idx] = rim_paper[rim_idx]
    
    bgra = np.dstack([composite_bgr, outer_mask])
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    cv2.imwrite(output_path, bgra)
    print(f"-> Saved: {output_path}")

def generate_papercut_pedestal(output_path, w=1200, h=320):
    print(f"Generating navy papercut pedestal: {output_path} ({w}x{h})...")
    margin = 30
    pts = make_scissor_cut_rect(margin, margin, w - 2 * margin, h - 2 * margin, num_bites_w=40, num_bites_h=15, jitter=1.2)
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(mask, [pts], 255)
    
    # Navy RGB: [35, 55, 72]
    paper_bgr = generate_paper_texture(w, h, (35, 55, 72), fiber_density=0.0005, grain_sigma=2.6)
    bevel = apply_paper_edge_bevel(mask, light_dir=(-0.6, -0.8))
    paper_floated = paper_bgr.astype(np.float32) + bevel[:, :, np.newaxis]
    paper_bgr = np.clip(paper_floated, 0, 255).astype(np.uint8)
    
    bgra = np.dstack([paper_bgr, mask])
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    cv2.imwrite(output_path, bgra)
    print(f"-> Saved: {output_path}")

def generate_panoramic_strip(output_path, w=2200, h=360, base_rgb=(248, 244, 236)):
    """
    全景横贯撕边地质长台基（用于 2.35:1 与 16:9 全幅地平线支撑）
    """
    return generate_torn_strip(output_path, w=w, h=h, base_rgb=base_rgb)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Procedural Physical Papercut & Torn Paper Generator")
    parser.add_argument("--out-dir", default=r"e:\OBVault\Nexus\_inbox", help="Directory to save generated papercut assets")
    parser.add_argument("--galaxy-src", default=None, help="Optional path to external galaxy image. If omitted or not found, synthesizes procedural Hubble nebula.")
    parser.add_argument("--asset-type", choices=["all", "canvas", "arch", "disc", "portal", "pedestal", "torn-strip", "panoramic-strip"], default="all", help="Asset type to generate (default: all)")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    
    canvas_path = os.path.join(args.out_dir, "canvas_vintage_paper.jpg")
    arch_path = os.path.join(args.out_dir, "papercut_arch_terracotta.png")
    disc_path = os.path.join(args.out_dir, "papercut_disc_slate.png")
    portal_path = os.path.join(args.out_dir, "papercut_portal_galaxy.png")
    pedestal_path = os.path.join(args.out_dir, "papercut_pedestal_navy.png")
    strip_path = os.path.join(args.out_dir, "papercut_torn_strip.png")
    panoramic_path = os.path.join(args.out_dir, "papercut_panoramic_strip.png")
    
    if args.asset_type in ["all", "canvas"]:
        generate_vintage_paper_canvas(canvas_path, 2500, 2500)
    if args.asset_type in ["all", "arch"]:
        generate_papercut_arch(arch_path, 1000, 1450)
    if args.asset_type in ["all", "disc"]:
        generate_papercut_disc(disc_path, 1200)
    if args.asset_type in ["all", "portal"]:
        generate_papercut_portal_galaxy(args.galaxy_src, portal_path, 1000)
    if args.asset_type in ["all", "pedestal"]:
        generate_papercut_pedestal(pedestal_path, 1200, 320)
    if args.asset_type in ["all", "torn-strip"]:
        generate_torn_strip(strip_path, 1400, 320)
    if args.asset_type in ["all", "panoramic-strip"]:
        generate_panoramic_strip(panoramic_path, 2200, 360)
        
    print(f"\nAll requested physical papercut assets successfully generated in: {args.out_dir}")
