import cv2
import numpy as np
import sys
import os
import argparse

def read_image_utf8(path):
    if not os.path.exists(path):
        return None
    data = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_UNCHANGED)

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

def is_skin_or_lips(bgr):
    """
    通用人像与角色肤色/唇色高鲁棒性检测：
    1. YCrCb 色彩空间经典人类肤色椭圆判定；
    2. RGB 空间自适应冷白与高光肤色判定；
    3. 唇色与血色红润判定。
    注意：纯白、浅灰与中性无彩区域必须排除（真实肤色均具有基础彩度偏移）。
    """
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    s = hsv[:, :, 1]
    
    r = bgr[:, :, 2].astype(int)
    g = bgr[:, :, 1].astype(int)
    b = bgr[:, :, 0].astype(int)
    
    y = 0.299 * r + 0.587 * g + 0.114 * b
    cr = (r - y) * 0.713 + 128
    cb = (b - y) * 0.564 + 128
    skin_ycrcb = (s >= 18) & (cr >= 132) & (cr <= 180) & (cb >= 70) & (cb <= 135)
    
    skin_rgb = (s >= 18) & (r > 90) & (g > 45) & (r > g) & (g >= b - 10) & ((r - b) >= 4)
    lips = (s >= 22) & (r > 110) & (r > 1.15 * g) & (r > 1.15 * b)
    
    return skin_ycrcb | skin_rgb | lips

def vectorize_papercut(bgr, alpha, k=10, approx_eps=0.0008, min_contour_area=8):
    """
    分层剪纸多边形矢量化引擎：
    1. 双边滤波保持锐利边界同时平坦化连续渐变；
    2. Lab 空间 K-Means 色阶聚类；
    3. 提取每一色阶的多边形折线轮廓；
    4. 按独立轮廓面积降序分层排序；
    5. 画布初始化为双边滤波平滑底色；
    6. 导出带 alpha 外轮廓与内孔洞的 clipPath 多层 SVG 矢量文件。
    """
    h, w = bgr.shape[:2]
    flat = cv2.bilateralFilter(bgr, d=7, sigmaColor=50, sigmaSpace=50)
    
    fg_mask = alpha > 128
    if not np.any(fg_mask):
        return bgr.copy(), f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}"></svg>'
        
    lab = cv2.cvtColor(flat, cv2.COLOR_BGR2Lab)
    pts = lab[fg_mask].astype(np.float32)
    
    num_pts = len(pts)
    actual_k = min(k, max(2, num_pts // 100))
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5)
    _, labels, centers = cv2.kmeans(pts, actual_k, None, criteria, 10, cv2.KMEANS_PP_CENTERS)
    centers_bgr = cv2.cvtColor(np.array([centers], dtype=np.uint8), cv2.COLOR_Lab2BGR)[0]
    
    label_map = np.full((h, w), -1, dtype=np.int32)
    label_map[fg_mask] = labels.flatten()
    
    all_polygons = []
    for c_idx in range(actual_k):
        col = centers_bgr[c_idx]
        c_mask = (label_map == c_idx).astype(np.uint8) * 255
        c_mask = cv2.dilate(c_mask, np.ones((2, 2), np.uint8))
        
        contours, hierarchy = cv2.findContours(c_mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        if not contours or hierarchy is None:
            continue
        hierarchy = hierarchy[0]
        
        for i, cnt in enumerate(contours):
            if hierarchy[i][3] != -1:
                continue
            area = cv2.contourArea(cnt)
            if area < min_contour_area:
                continue
            arc = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, approx_eps * arc, True)
            pts_poly = approx.reshape(-1, 2)
            if len(pts_poly) < 3:
                continue
            
            hole_polys = []
            child_idx = hierarchy[i][2]
            while child_idx != -1:
                hole_cnt = contours[child_idx]
                hole_area = cv2.contourArea(hole_cnt)
                if hole_area >= min_contour_area:
                    hole_arc = cv2.arcLength(hole_cnt, True)
                    approx_h = cv2.approxPolyDP(hole_cnt, approx_eps * hole_arc, True)
                    pts_h = approx_h.reshape(-1, 2)
                    if len(pts_h) >= 3:
                        hole_polys.append(pts_h)
                child_idx = hierarchy[child_idx][0]
                
            all_polygons.append({
                'area': area,
                'outer_pts': pts_poly,
                'holes': hole_polys,
                'col_bgr': (int(col[0]), int(col[1]), int(col[2])),
                'hex': f"#{int(col[2]):02x}{int(col[1]):02x}{int(col[0]):02x}"
            })
            
    all_polygons.sort(key=lambda p: p['area'], reverse=True)
    canvas = flat.copy()
    svg_paths = []
    
    for poly in all_polygons:
        outer = poly['outer_pts']
        holes = poly['holes']
        cv2.fillPoly(canvas, [outer], poly['col_bgr'])
        
        d_subpaths = [f"M {outer[0][0]} {outer[0][1]} " + " ".join([f"L {p[0]} {p[1]}" for p in outer[1:]]) + " Z"]
        for h_pts in holes:
            d_subpaths.append(f"M {h_pts[0][0]} {h_pts[0][1]} " + " ".join([f"L {p[0]} {p[1]}" for p in h_pts[1:]]) + " Z")
        d_combined = " ".join(d_subpaths)
        svg_paths.append(f'    <path d="{d_combined}" fill="{poly["hex"]}" stroke="{poly["hex"]}" stroke-width="0.4" fill-rule="evenodd" />')
        
    alpha_mask = (alpha > 128).astype(np.uint8) * 255
    alpha_cnts, alpha_hier = cv2.findContours(alpha_mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    clip_d_list = []
    if alpha_cnts and alpha_hier is not None:
        for cnt in alpha_cnts:
            arc = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, approx_eps * arc, True)
            pts = approx.reshape(-1, 2)
            if len(pts) >= 3:
                d = f"M {pts[0][0]} {pts[0][1]} " + " ".join([f"L {p[0]} {p[1]}" for p in pts[1:]]) + " Z"
                clip_d_list.append(d)
    clip_path_d = " ".join(clip_d_list)
    
    svg_content = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">\n'
    svg_content += '  <defs>\n'
    svg_content += '    <clipPath id="papercut-clip">\n'
    svg_content += f'      <path d="{clip_path_d}" clip-rule="evenodd" fill-rule="evenodd" />\n'
    svg_content += '    </clipPath>\n'
    svg_content += '  </defs>\n'
    svg_content += '  <g clip-path="url(#papercut-clip)">\n'
    svg_content += "\n".join(svg_paths) + "\n"
    svg_content += '  </g>\n'
    svg_content += '</svg>\n'
    
    return canvas, svg_content

def apply_hollow_apparel(bgr, alpha, min_apparel_area=500):
    """
    负空间服饰镂空：使用色相/明度掩码将主体内的大块浅色/白色服饰区域置为透明（alpha=0），
    以便在 HTML 装配中让底层的宇宙星空穿透人物服饰。
    保护五官、手脚及肤色/唇色。
    """
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]
    skin_mask = is_skin_or_lips(bgr)
    
    # 候选服饰：在前景有效区域内，低饱和度且较高明度，且严禁覆盖肤色与唇色
    apparel_cand = (alpha > 128) & (s < 55) & (v > 160) & (~skin_mask)
    
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(apparel_cand.astype(np.uint8))
    hollow_mask = np.zeros_like(alpha, dtype=bool)
    
    fg_area = np.sum(alpha > 128)
    effective_min_area = max(min_apparel_area, int(0.015 * fg_area))
    
    for lab in range(1, num_labels):
        area = stats[lab, cv2.CC_STAT_AREA]
        if area >= effective_min_area:
            hollow_mask |= (labels == lab)
            
    if np.any(hollow_mask):
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        hollow_mask_clean = cv2.morphologyEx(hollow_mask.astype(np.uint8), cv2.MORPH_OPEN, kernel)
        alpha[hollow_mask_clean > 0] = 0
        print(f"Hollow Apparel Applied: {np.sum(hollow_mask_clean > 0)} pixels hollowed out for negative space starfield penetration.")
        
    return alpha

def cutout_asset(
    src_path, 
    dst_path, 
    tolerance=25, 
    k_clusters=10, 
    vectorize=False,
    hollow_apparel=False,
    export_svg=None,
    clean_holes=True, 
    min_hole_area=80, 
    shadow_s=30,
    shadow_v=100,
    shadow_peel_iter=50,
    edge_width=1.2,
    tight_crop=True,
    padding=4
):
    """
    复古剪纸无白边抠图引擎：
    1. 纯白背景与边缘杂色精准剔除，彻底清除贴纸白边，紧贴主体真实边缘；
    2. 色彩扩张修复（Color Bleed Inpainting）消除边缘白晕；
    3. 默认保留原始真实胶印微粒与半色调网点（vectorize 默认为 False）；
    4. 可选负空间服饰镂空（hollow_apparel=True），支持 Joe Webb 宇宙穿透；
    5. 紧致包围盒裁切并恢复真实物理比例。
    """
    if not os.path.exists(src_path):
        print(f"Error: Source image {src_path} does not exist.")
        sys.exit(1)
        
    img = read_image_utf8(src_path)
    if img is None:
        print(f"Error: Failed to read {src_path}")
        sys.exit(1)
        
    h, w = img.shape[:2]
    bgr = img[:, :, :3].copy()
    skin_mask = is_skin_or_lips(bgr)
    
    has_alpha = (img.ndim == 3 and img.shape[2] == 4)
    if has_alpha and np.any(img[:, :, 3] < 255):
        alpha_init = img[:, :, 3]
        is_bg = (alpha_init == 0)
        
        white_ref = np.array([255, 255, 255], dtype=np.float32)
        diff_white = np.linalg.norm(bgr.astype(np.float32) - white_ref, axis=2)
        effective_tol = max(tolerance, 30)
        white_cand = (diff_white < effective_tol) & (~is_bg)
        
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(white_cand.astype(np.uint8))
        for lab in range(1, num_labels):
            area = stats[lab, cv2.CC_STAT_AREA]
            mask = (labels == lab).astype(np.uint8)
            dilated = cv2.dilate(mask, np.ones((7, 7), np.uint8))
            ring = (dilated > 0) & (~mask.astype(bool))
            touches_bg = np.any(is_bg[ring])
            
            if touches_bg:
                # 紧贴外围背景的白色碎边一律剔除
                is_bg[labels == lab] = True
            elif clean_holes and area >= min_hole_area:
                skin_neighbors = np.sum(skin_mask[ring])
                if skin_neighbors < 10:
                    is_bg[labels == lab] = True
    else:
        borders = np.vstack([bgr[0, :], bgr[-1, :], bgr[:, 0], bgr[:, -1]])
        bg_color = np.median(borders, axis=0).astype(np.float32)
        
        diff = np.linalg.norm(bgr.astype(np.float32) - bg_color[:3], axis=2)
        is_bg_white = np.all(bg_color >= 240)
        
        if is_bg_white:
            effective_tol = min(tolerance, 20)
        else:
            effective_tol = tolerance
            
        bg_cand = (diff < effective_tol).astype(np.uint8)
        
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(bg_cand)
        perim = np.unique(np.hstack([labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]]))
        perim = perim[perim != 0]
        is_bg = np.isin(labels, perim)
        
        if clean_holes:
            for lab in range(1, num_labels):
                if lab not in perim and stats[lab, cv2.CC_STAT_AREA] >= min_hole_area:
                    mask = (labels == lab).astype(np.uint8)
                    dilated = cv2.dilate(mask, np.ones((7, 7), np.uint8))
                    ring = (dilated > 0) & (~mask.astype(bool))
                    skin_neighbors = np.sum(skin_mask[ring])
                    if skin_neighbors < 10:
                        is_bg[labels == lab] = True
                        
    # 剥离外围浅灰阴影与残存白晕（严禁保留白边，紧贴真实边缘剔除）
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    s, v = hsv[:, :, 1], hsv[:, :, 2]
    effective_shadow_v = max(40, min(shadow_v, 120))
    is_fringe = (s < shadow_s) & (v >= effective_shadow_v) & (~skin_mask)
    for _ in range(shadow_peel_iter):
        dilated_bg = cv2.dilate(is_bg.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        new_bg = is_bg | (dilated_bg & is_fringe)
        if np.array_equal(new_bg, is_bg):
            break
        is_bg = new_bg
        
    fg_mask = (~is_bg).astype(np.uint8) * 255
    n_c, l_c, s_c, _ = cv2.connectedComponentsWithStats((fg_mask > 0).astype(np.uint8))
    if n_c > 1:
        max_area = np.max(s_c[1:, cv2.CC_STAT_AREA])
        cleaned_fg = np.zeros_like(fg_mask)
        min_keep_area = max(min_hole_area, int(max_area * 0.10))
        for i in range(1, n_c):
            if s_c[i, cv2.CC_STAT_AREA] >= min_keep_area:
                cleaned_fg[l_c == i] = 255
        fg_mask = cleaned_fg
        
    if vectorize:
        contours, hierarchy = cv2.findContours(fg_mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        v_mask = np.zeros_like(fg_mask)
        if contours and hierarchy is not None:
            approx_cnts = [cv2.approxPolyDP(cnt, 0.0008 * cv2.arcLength(cnt, True), True) for cnt in contours]
            for i, cnt in enumerate(approx_cnts):
                if hierarchy[0][i][3] == -1:
                    cv2.drawContours(v_mask, [cnt], -1, 255, -1)
            for i, cnt in enumerate(approx_cnts):
                if hierarchy[0][i][3] != -1:
                    cv2.drawContours(v_mask, [cnt], -1, 0, -1)
        v_mask[is_bg] = 0
        fg_mask = v_mask
        
    effective_edge = max(0.5, float(edge_width))
    dist = cv2.distanceTransform(fg_mask, cv2.DIST_L2, 3)
    alpha = np.clip(dist * (255.0 / effective_edge), 0, 255).astype(np.uint8)
    
    # 色彩扩张修复（Defringing Inpainting）彻底消除边缘泛白
    inner_fg = cv2.erode((alpha == 255).astype(np.uint8) * 255, np.ones((5, 5), np.uint8))
    if not np.any(inner_fg == 255):
        inner_fg = cv2.erode((alpha > 200).astype(np.uint8) * 255, np.ones((3, 3), np.uint8))
    if not np.any(inner_fg == 255):
        inner_fg = (alpha > 0).astype(np.uint8) * 255
        
    outer_band = cv2.dilate((alpha > 0).astype(np.uint8) * 255, np.ones((7, 7), np.uint8))
    inpaint_mask = cv2.subtract(outer_band, inner_fg)
    
    if np.any(inpaint_mask):
        clean_bgr = cv2.inpaint(bgr, inpaint_mask, 3, cv2.INPAINT_TELEA)
    else:
        clean_bgr = bgr.copy()
        
    # 紧致包围盒裁切
    if tight_crop:
        nonzero_y, nonzero_x = np.where(alpha > 0)
        if len(nonzero_y) > 0:
            min_y = max(0, int(nonzero_y.min()) - padding)
            max_y = min(h, int(nonzero_y.max()) + 1 + padding)
            min_x = max(0, int(nonzero_x.min()) - padding)
            max_x = min(w, int(nonzero_x.max()) + 1 + padding)
            clean_bgr = clean_bgr[min_y:max_y, min_x:max_x]
            alpha = alpha[min_y:max_y, min_x:max_x]
            
    # 负空间服饰镂空（如果开启）
    if hollow_apparel:
        alpha = apply_hollow_apparel(clean_bgr, alpha)
        
    if vectorize:
        clean_bgr, svg_content = vectorize_papercut(clean_bgr, alpha, k=k_clusters)
        if export_svg:
            os.makedirs(os.path.dirname(os.path.abspath(export_svg)), exist_ok=True)
            with open(export_svg, "w", encoding="utf-8") as f:
                f.write(svg_content)
            print(f"Exported True Multi-Layer Paper-Cut SVG: {export_svg}")
    elif export_svg:
        cur_h, cur_w = clean_bgr.shape[:2]
        contours, _ = cv2.findContours(alpha, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        svg_paths = []
        for cnt in contours:
            arc = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.0015 * arc, True)
            pts = approx.reshape(-1, 2)
            if len(pts) >= 3:
                d = f"M {pts[0][0]} {pts[0][1]} " + " ".join([f"L {p[0]} {p[1]}" for p in pts[1:]]) + " Z"
                svg_paths.append(f'  <path d="{d}" fill="#222" />')
        svg_content = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {cur_w} {cur_h}" width="{cur_w}" height="{cur_h}">\n' + "\n".join(svg_paths) + "\n</svg>\n"
        with open(export_svg, "w", encoding="utf-8") as f:
            f.write(svg_content)
        print(f"Exported Silhouette SVG: {export_svg}")
        
    res = np.dstack([clean_bgr.astype(np.uint8), alpha.astype(np.uint8)])
    write_image_utf8(dst_path, res)
    print(f"Smart Zero-Fringe Cutout Success: {dst_path} (Shape={res.shape}, Tol={tolerance}, Vector={vectorize}, Hollow={hollow_apparel})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Authentic Vintage Zero-Fringe Papercut Extractor")
    parser.add_argument("src", help="Path to source image")
    parser.add_argument("dst", help="Path to destination transparent PNG")
    parser.add_argument("--tolerance", "-t", type=int, default=25, help="Color tolerance for background detection (default: 25)")
    parser.add_argument("--k-clusters", "-k", type=int, default=10, help="Number of Lab K-Means color clusters for paper-cut vectorization (default: 10)")
    parser.add_argument("--vectorize", dest="vectorize", action="store_true", default=False, help="Enable paper-cut polygon vectorization & color flattening (default: False)")
    parser.add_argument("--no-vectorize", dest="vectorize", action="store_false", help="Disable polygon vectorization")
    parser.add_argument("--hollow-apparel", dest="hollow_apparel", action="store_true", default=False, help="Hollow out white/light apparel for negative space starfield penetration (default: False)")
    parser.add_argument("--export-svg", type=str, default=None, help="Optional path to export vectorized SVG file")
    parser.add_argument("--no-clean-holes", dest="clean_holes", action="store_false", help="Disable automatic cleaning of enclosed background holes")
    parser.add_argument("--min-hole-area", type=int, default=80, help="Minimum pixel area for internal background cavities (default: 80)")
    parser.add_argument("--shadow-s", type=int, default=30, help="Maximum saturation threshold for cast shadow peeling (default: 30)")
    parser.add_argument("--shadow-v", type=int, default=100, help="Minimum brightness threshold for cast shadow peeling (default: 100)")
    parser.add_argument("--shadow-peel-iter", type=int, default=50, help="Max iterations for cast shadow peeling (default: 50)")
    parser.add_argument("--edge-width", type=float, default=1.2, help="Inward anti-aliasing edge width in pixels (default: 1.2)")
    parser.add_argument("--no-tight-crop", dest="tight_crop", action="store_false", help="Disable tight bounding box crop")
    parser.add_argument("--padding", type=int, default=4, help="Tight crop safety padding in pixels (default: 4)")
    parser.set_defaults(vectorize=False, hollow_apparel=False, clean_holes=True, tight_crop=True)
    
    args = parser.parse_args()
    cutout_asset(
        args.src, 
        args.dst, 
        tolerance=args.tolerance, 
        k_clusters=args.k_clusters, 
        vectorize=args.vectorize,
        hollow_apparel=args.hollow_apparel,
        export_svg=args.export_svg,
        clean_holes=args.clean_holes, 
        min_hole_area=args.min_hole_area, 
        shadow_s=args.shadow_s,
        shadow_v=args.shadow_v,
        shadow_peel_iter=args.shadow_peel_iter,
        edge_width=args.edge_width,
        tight_crop=args.tight_crop,
        padding=args.padding
    )
