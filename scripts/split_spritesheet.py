import cv2
import numpy as np
import os
import sys

def process_spritesheet(sheet_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    img = cv2.imread(sheet_path)
    if img is None:
        print(f"Failed to read {sheet_path}")
        return False
        
    h, w = img.shape[:2]
    print(f"Loaded spritesheet: {w}x{h}")
    
    # Background is white (#FFFFFF)
    # Detect background by thresholding close to white
    diff_white = np.linalg.norm(img.astype(np.float32) - np.array([255, 255, 255]), axis=2)
    fg_mask = (diff_white > 25).astype(np.uint8) * 255
    
    # Morphological close to bridge tiny gaps inside items
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    fg_mask_clean = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel_close)
    
    # Remove small specks
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_mask_clean)
    print(f"Detected {num_labels - 1} raw foreground clusters")
    
    components = []
    min_area = 1500  # Minimum area to be considered an asset
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if area >= min_area:
            x = stats[i, cv2.CC_STAT_LEFT]
            y = stats[i, cv2.CC_STAT_TOP]
            cw = stats[i, cv2.CC_STAT_WIDTH]
            ch = stats[i, cv2.CC_STAT_HEIGHT]
            components.append({
                'id': i,
                'area': area,
                'bbox': (x, y, cw, ch),
                'centroid': centroids[i]
            })
            
    print(f"Kept {len(components)} prominent collage components")
    
    # Sort components by area descending
    components.sort(key=lambda c: c['area'], reverse=True)
    
    for idx, comp in enumerate(components):
        x, y, cw, ch = comp['bbox']
        pad = 24
        x0 = max(0, x - pad)
        y0 = max(0, y - pad)
        x1 = min(w, x + cw + pad)
        y1 = min(h, y + ch + pad)
        
        crop = img[y0:y1, x0:x1].copy()
        crop_mask = (labels[y0:y1, x0:x1] == comp['id']).astype(np.uint8) * 255
        
        # Smooth mask and create die-cut border
        # Morphological closing to seal internal hair/prop voids for die-cut
        outer_mask = cv2.morphologyEx(crop_mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (19, 19)))
        
        # Find external contours only
        cnts, _ = cv2.findContours(outer_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Build die-cut stroke canvas
        die_cut_mask = np.zeros_like(outer_mask)
        cv2.drawContours(die_cut_mask, cnts, -1, 255, thickness=-1)
        
        # Dilate for white border (16px)
        stroke_border = cv2.dilate(die_cut_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (33, 33)))
        
        # Composite transparent sticker
        # Inner is crop, border is white [255, 255, 255], outer is transparent 0
        crop_h, crop_w = crop.shape[:2]
        sticker_rgba = np.zeros((crop_h, crop_w, 4), dtype=np.uint8)
        
        # Fill white die-cut background
        sticker_rgba[stroke_border > 0] = [255, 255, 255, 255]
        
        # Place original crop where original component mask is positive
        inner_fg = (crop_mask > 0)
        sticker_rgba[inner_fg, 0:3] = crop[inner_fg]
        sticker_rgba[inner_fg, 3] = 255
        
        # Save asset
        out_png = os.path.join(out_dir, f"asset_{idx}_{comp['area']}.png")
        cv2.imwrite(out_png, sticker_rgba)
        print(f"Saved asset {idx}: {out_png} ({crop_w}x{crop_h})")
        
    return True

if __name__ == '__main__':
    if len(sys.argv) > 2:
        process_spritesheet(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python split_spritesheet.py <spritesheet_path> <out_dir>")
