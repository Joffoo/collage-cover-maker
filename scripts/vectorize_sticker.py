import cv2
import numpy as np
import os
import sys

def vectorize_rgba(rgba_path, out_svg_path, k_colors=14):
    rgba = cv2.imread(rgba_path, cv2.IMREAD_UNCHANGED)
    if rgba is None:
        print("Error reading", rgba_path)
        return False
        
    h, w = rgba.shape[:2]
    bgr = rgba[:, :, :3]
    alpha = rgba[:, :, 3]
    
    fg_mask = alpha > 128
    
    # 1. Bilateral filter to smooth diffusion noise while preserving sharp edges
    flat = cv2.bilateralFilter(bgr, d=7, sigmaColor=40, sigmaSpace=40)
    
    # 2. Lab color space K-means color quantization (Screenprint / risograph quantization)
    lab = cv2.cvtColor(flat, cv2.COLOR_BGR2Lab)
    pts = lab[fg_mask].astype(np.float32)
    
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5)
    _, labels, centers = cv2.kmeans(pts, k_colors, None, criteria, 10, cv2.KMEANS_PP_CENTERS)
    centers_bgr = cv2.cvtColor(np.array([centers], dtype=np.uint8), cv2.COLOR_Lab2BGR)[0]
    
    label_map = np.full((h, w), -1, dtype=np.int32)
    label_map[fg_mask] = labels.flatten()
    
    # 3. Outer boundary path (for die-cut stroke & clip-path)
    # Morphological closing on foreground mask to get smooth outer boundary
    outer_closed = cv2.morphologyEx(fg_mask.astype(np.uint8)*255, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    outer_cnts, _ = cv2.findContours(outer_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    clip_paths = []
    for cnt in outer_cnts:
        arc = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.001 * arc, True)
        pts = approx.reshape(-1, 2)
        if len(pts) >= 3:
            d = f"M {pts[0][0]} {pts[0][1]} " + " ".join([f"L {p[0]} {p[1]}" for p in pts[1:]]) + " Z"
            clip_paths.append(d)
    clip_path_d = " ".join(clip_paths)
    
    # 4. Extract polygons for each color layer
    all_polys = []
    for c_idx in range(k_colors):
        col = centers_bgr[c_idx]
        c_mask = (label_map == c_idx).astype(np.uint8) * 255
        c_mask = cv2.dilate(c_mask, np.ones((2, 2), np.uint8))
        
        cnts, hierarchy = cv2.findContours(c_mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts or hierarchy is None:
            continue
        hierarchy = hierarchy[0]
        
        for i, cnt in enumerate(cnts):
            if hierarchy[i][3] != -1:
                continue
            area = cv2.contourArea(cnt)
            if area < 10:
                continue
            arc = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.0008 * arc, True)
            pts_poly = approx.reshape(-1, 2)
            if len(pts_poly) < 3:
                continue
                
            d_poly = f"M {pts_poly[0][0]} {pts_poly[0][1]} " + " ".join([f"L {p[0]} {p[1]}" for p in pts_poly[1:]]) + " Z"
            hex_col = f"#{int(col[2]):02x}{int(col[1]):02x}{int(col[0]):02x}"
            all_polys.append({
                'area': area,
                'd': d_poly,
                'hex': hex_col
            })
            
    # Sort largest area first (background layers underneath)
    all_polys.sort(key=lambda p: p['area'], reverse=True)
    
    svg_body = []
    for p in all_polys:
        svg_body.append(f'    <path d="{p["d"]}" fill="{p["hex"]}" stroke="{p["hex"]}" stroke-width="0.3" />')
        
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
  <defs>
    <filter id="sticker-shadow" x="-10%" y="-10%" width="130%" height="130%">
      <feDropShadow dx="0" dy="12" stdDeviation="16" flood-color="rgba(0,0,0,0.18)" />
    </filter>
    <clipPath id="subject-clip">
      <path d="{clip_path_d}" />
    </clipPath>
  </defs>
  <!-- Die-cut white backing with drop shadow -->
  <path d="{clip_path_d}" fill="#FFFFFF" stroke="#FFFFFF" stroke-width="14" stroke-linejoin="round" stroke-linecap="round" filter="url(#sticker-shadow)" />
  <!-- Vectorized photographic artwork -->
  <g clip-path="url(#subject-clip)">
{chr(10).join(svg_body)}
  </g>
</svg>
'''
    os.makedirs(os.path.dirname(os.path.abspath(out_svg_path)), exist_ok=True)
    with open(out_svg_path, 'w', encoding='utf-8') as f:
        f.write(svg_content)
    print("Vectorized SVG saved to", out_svg_path)
    return True

if __name__ == '__main__':
    if len(sys.argv) > 2:
        k = int(sys.argv[3]) if len(sys.argv) > 3 else 14
        vectorize_rgba(sys.argv[1], sys.argv[2], k_colors=k)
    else:
        print("Usage: python vectorize_sticker.py <input_png> <output_svg> [k_colors]")
