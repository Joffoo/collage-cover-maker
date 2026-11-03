import asyncio
from playwright.async_api import async_playwright
import cv2
import numpy as np
import os
import sys

async def render_and_regrain(html_path, output_png, width=2115, height=900, noise_sigma=4.5):
    """
    无头浏览器高精渲染 + 阶调依从型物理油墨重着色引擎：
    1. 依托 Playwright 渲染高分辨率 DOM 布局；
    2. 阶调依从型油墨颗粒（Tonal-Dependent Ink Pigment Grain）：
       - 暗部与中间调：油墨沉淀聚集与半色调网点交融，噪点增益加权（1.0 ~ 1.35）；
       - 高光纸张基底：油墨消褪，呈现纸张自身的高漫反射原木微纤维（轻透权重衰减至 0.18 ~ 0.35）；
    3. 单色单通道散粒，杜绝数码红绿彩噪，呈现真实的平版与铜版胶印颗粒。
    """
    if not os.path.exists(html_path):
        print(f"Error: {html_path} does not exist.")
        sys.exit(1)
        
    abs_output = os.path.abspath(output_png)
    temp_raw = os.path.splitext(abs_output)[0] + "_raw.png"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--disable-gpu", "--no-sandbox"])
        page = await browser.new_page(viewport={"width": width, "height": height})
        abs_html = os.path.abspath(html_path).replace("\\", "/")
        await page.goto(f"file:///{abs_html}", wait_until="networkidle")
        await page.screenshot(path=temp_raw)
        await browser.close()
        
    if not os.path.exists(temp_raw):
        print(f"Error: Screenshot failed to generate {temp_raw}")
        sys.exit(1)
        
    # 读取原始截图（兼容 Windows 中文路径）
    raw_data = np.fromfile(temp_raw, dtype=np.uint8)
    img = cv2.imdecode(raw_data, cv2.IMREAD_COLOR)
    if img is None:
        print(f"Error: Failed to decode screenshot {temp_raw}")
        sys.exit(1)
        
    h, w = img.shape[:2]
    
    # 阶调依从型油墨颗粒算法
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    
    # 模拟真实印刷：暗调和中间调油墨堆积重，高光纸张底纤维轻透
    # 暗调/中间调(gray 0.0~0.6)加权 1.0~1.35，高光(gray -> 1.0)平滑衰减至 0.2
    ink_weight = np.clip(1.35 * (1.0 - (gray ** 1.3)), 0.20, 1.35)[:, :, np.newaxis]
    
    # 单通道灰度散粒颗粒
    grain_ink = np.random.normal(0, noise_sigma, (h, w, 1)).astype(np.float32)
    grain_paper = np.random.normal(0, noise_sigma * 0.35, (h, w, 1)).astype(np.float32)
    
    total_grain = grain_ink * ink_weight + grain_paper
    noisy_img = np.clip(img.astype(np.float32) + total_grain, 0, 255).astype(np.uint8)
    
    os.makedirs(os.path.dirname(abs_output), exist_ok=True)
    success, encoded = cv2.imencode('.png', noisy_img, [cv2.IMWRITE_PNG_COMPRESSION, 4])
    if success:
        encoded.tofile(abs_output)
    else:
        print(f"Error: Failed to encode image to {abs_output}")
        sys.exit(1)
    
    if os.path.exists(temp_raw):
        try:
            os.remove(temp_raw)
        except Exception:
            pass
            
    print(f"Successfully rendered & re-grained with tonal ink grain: {abs_output} ({width}x{height})")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python render_and_regrain.py <html_path> <output_png> [width] [height]")
        sys.exit(1)
    w = int(sys.argv[3]) if len(sys.argv) > 3 else 2115
    h = int(sys.argv[4]) if len(sys.argv) > 4 else 900
    asyncio.run(render_and_regrain(sys.argv[1], sys.argv[2], w, h))
