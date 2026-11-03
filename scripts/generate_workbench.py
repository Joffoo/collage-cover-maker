#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_workbench.py
---------------------
生成拼贴封面交互式调优工作台 (Collage Cover Workbench)。
输入已有的拼贴装配 HTML (如 <slug>_wechat_2115x900.html)，
输出独立的纯前端交互界面 (<slug>_workbench.html)。

核心特性：
1. 滑杆调优：X/Y 坐标、缩放比例、旋转角度、Z-index、不透明度、阴影偏移/模糊；
2. 实时画布：支持画幅实时缩放适配、微信 1:1 正方形安全视窗覆盖层、画布直接拖拽；
3. 一键复制合适的位置：点击即可将最新微调后的 CSS 坐标与定位代码写入剪贴板；
4. 零外部依赖：纯 HTML/CSS/JS 单文件交付，直接用浏览器本地打开。
"""

import os
import sys
import re
import json
import argparse
import base64
import mimetypes
import urllib.parse
from bs4 import BeautifulSoup


def extract_drop_shadow(text):
    """提取 drop-shadow(...) 内容，正确处理嵌套括号如 rgba(...)"""
    if not text:
        return None
    idx = text.find("drop-shadow(")
    if idx == -1:
        return None
    start = idx + len("drop-shadow(")
    depth = 1
    i = start
    while i < len(text) and depth > 0:
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
        i += 1
    if depth != 0:
        return None
    return text[start:i-1].strip()


def parse_drop_shadow(content):
    """解析 drop-shadow 的 offset-x, offset-y, blur, color"""
    if not content:
        return 0.0, 0.0, 0.0, "rgba(0, 0, 0, 0.25)"
    color_m = re.search(r'(rgba?\(.+?\)|hsla?\(.+?\)|#[0-9a-fA-F]{3,8})', content)
    color = "rgba(0, 0, 0, 0.25)"
    rem = content
    if color_m:
        color = color_m.group(1).strip()
        rem = content[:color_m.start()] + " " + content[color_m.end():]
    parts = rem.split()
    nums = []
    for p in parts:
        m = re.match(r'^([-\d\.]+)(?:px)?$', p)
        if m:
            nums.append(float(m.group(1)))
    ox = nums[0] if len(nums) > 0 else 0.0
    oy = nums[1] if len(nums) > 1 else 0.0
    blur = nums[2] if len(nums) > 2 else 0.0
    return ox, oy, blur, color


def extract_extra_inline_style(inline_style):
    """去除已由滑杆接管的属性，保留其余用户自定义内联样式 (如 object-fit, letter-spacing 等)"""
    managed_props = {'position', 'left', 'top', 'width', 'height', 'z-index', 'transform', 'opacity', 'filter'}
    declarations = [d.strip() for d in inline_style.split(';') if d.strip()]
    extra = []
    for d in declarations:
        if ':' in d:
            prop = d.split(':', 1)[0].strip().lower()
            if prop not in managed_props:
                extra.append(d)
    return '; '.join(extra) + (';' if extra else '')


def parse_assembly_html(html_path):
    """解析装配 HTML，提取画布尺寸与各个图层图元"""
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    soup = BeautifulSoup(content, "html.parser")

    # 提取画布尺寸与背景
    canvas_w = 2115
    canvas_h = 900
    bg_color = "#faefd3"

    style_tag = soup.find("style")
    style_text = style_tag.string if style_tag and style_tag.string else ""

    canvas_rule_m = re.search(r'(?:\.canvas|body)\s*\{([^}]+)\}', style_text)
    if canvas_rule_m:
        c_body = canvas_rule_m.group(1)
        w_m = re.search(r'width:\s*(\d+)px', c_body)
        if w_m:
            canvas_w = int(w_m.group(1))
        h_m = re.search(r'height:\s*(\d+)px', c_body)
        if h_m:
            canvas_h = int(h_m.group(1))
        bg_m = re.search(r'background-color:\s*([^;]+);', c_body)
        if bg_m:
            bg_color = bg_m.group(1).strip()
    else:
        w_m = re.search(r'width:\s*(\d+)px', style_text)
        if w_m:
            canvas_w = int(w_m.group(1))
        h_m = re.search(r'height:\s*(\d+)px', style_text)
        if h_m:
            canvas_h = int(h_m.group(1))

    # 提取所有 CSS 类和 ID 规则 (例如 .subtitle-wrapper { ... } 或 .shadow-arch { ... })
    css_rules = {}
    for match in re.finditer(r'([.#][a-zA-Z0-9_-]+)\s*\{([^}]+)\}', style_text):
        cname = match.group(1).strip()
        cbody = match.group(2).strip()
        css_rules[cname] = cbody

    canvas_div = soup.find("div", class_="canvas")
    if not canvas_div:
        canvas_div = soup.find("body")

    children = [c for c in canvas_div.children if c.name in ["img", "div", "svg", "p"]]

    layers = []
    for idx, elem in enumerate(children):
        classes = elem.get("class", [])
        if isinstance(classes, str):
            classes = classes.split()

        elem_id = elem.get("id", "")
        inline_style = elem.get("style", "")

        # 合并该元素继承的 CSS 属性（优先级：inline_style > id 规则 > class 规则）
        inherited_css = []
        for cls in classes:
            key = f".{cls}"
            if key in css_rules:
                inherited_css.append(css_rules[key])
        if elem_id and f"#{elem_id}" in css_rules:
            inherited_css.append(css_rules[f"#{elem_id}"])

        def find_prop(pattern):
            m = re.search(pattern, inline_style)
            if m:
                return m
            for css_body in reversed(inherited_css):
                m = re.search(pattern, css_body)
                if m:
                    return m
            return None

        # 提取图层名称
        tag_name = elem.name
        src = elem.get("src", "")
        if src:
            layer_name = os.path.basename(src)
        elif "subtitle-wrapper" in classes:
            layer_name = "双行副标题 (文字块)"
        elif elem_id:
            layer_name = f"#{elem_id}"
        elif classes:
            layer_name = f".{classes[0]}"
        else:
            layer_name = f"图层 {idx + 1} ({tag_name})"

        # 解析位置与变换
        left = 0.0
        top = 0.0
        width = None
        height = None
        rotate = 0.0
        scale = 1.0
        z_index = 10 + idx * 4
        opacity = 1.0

        m = find_prop(r'left:\s*([-\d\.]+)px')
        if m:
            left = float(m.group(1))
        m = find_prop(r'top:\s*([-\d\.]+)px')
        if m:
            top = float(m.group(1))
        m = find_prop(r'width:\s*([-\d\.]+)px')
        if m:
            width = float(m.group(1))
        m = find_prop(r'height:\s*([-\d\.]+)px')
        if m:
            height = float(m.group(1))
        m = find_prop(r'z-index:\s*(\d+)')
        if m:
            z_index = int(m.group(1))
        m = find_prop(r'opacity:\s*([-\d\.]+)')
        if m:
            opacity = float(m.group(1))

        # transform
        m = find_prop(r'rotate\(([-\d\.]+)deg\)')
        if m:
            rotate = float(m.group(1))
        m = find_prop(r'scale\(([-\d\.]+)\)')
        if m:
            scale = float(m.group(1))

        # 解析 drop-shadow
        drop_shadow_content = extract_drop_shadow(inline_style)
        if not drop_shadow_content:
            for css_body in reversed(inherited_css):
                drop_shadow_content = extract_drop_shadow(css_body)
                if drop_shadow_content:
                    break

        shadow_ox, shadow_oy, shadow_blur, shadow_rgba = parse_drop_shadow(drop_shadow_content)

        # 提取非位置类的用户自定义内联样式
        extra_style = extract_extra_inline_style(inline_style)

        # 检查是否为背景底纸
        is_background = ("paper" in src.lower() or "canvas" in src.lower() or (idx == 0 and tag_name == "img"))

        # 解析 src 并在本地查找对应文件，生成 dataUri (消除本地 file:// 协议下的 Canvas 跨域污染与加载缺失)
        data_uri = None
        if src:
            src_clean = urllib.parse.unquote(src)
            base_dir = os.path.dirname(os.path.abspath(html_path))
            candidate_paths = [
                os.path.join(base_dir, src_clean),
                os.path.abspath(src_clean),
                os.path.join(base_dir, "..", "_attachments", os.path.basename(src_clean)),
                os.path.join(base_dir, "_attachments", os.path.basename(src_clean)),
            ]
            for cp in candidate_paths:
                if os.path.isfile(cp):
                    try:
                        mime, _ = mimetypes.guess_type(cp)
                        if cp.endswith('.svg'):
                            mime = 'image/svg+xml'
                            with open(cp, 'r', encoding='utf-8', errors='ignore') as svg_f:
                                svg_content = svg_f.read()
                            # 自动补全缺失 width/height 的 SVG viewBox 尺寸，确保各类浏览器下 Canvas 均能正确识别 naturalWidth/naturalHeight
                            svg_tag_m = re.search(r'<svg\b([^>]*)>', svg_content, re.IGNORECASE)
                            if svg_tag_m:
                                attrs = svg_tag_m.group(1)
                                has_w = re.search(r'\bwidth\s*=', attrs)
                                has_h = re.search(r'\bheight\s*=', attrs)
                                if not has_w or not has_h:
                                    vb_m = re.search(r'viewBox\s*=\s*[\'"]\s*([-\d\.]+)\s+([-\d\.]+)\s+([-\d\.]+)\s+([-\d\.]+)[\'"]', attrs)
                                    if vb_m:
                                        vb_w, vb_h = vb_m.group(3), vb_m.group(4)
                                        added = []
                                        if not has_w:
                                            added.append(f'width="{vb_w}"')
                                        if not has_h:
                                            added.append(f'height="{vb_h}"')
                                        new_tag = f'<svg {attrs} {" ".join(added)}>'
                                        svg_content = svg_content[:svg_tag_m.start()] + new_tag + svg_content[svg_tag_m.end():]
                            raw_bytes = svg_content.encode('utf-8')
                        else:
                            if not mime:
                                mime = 'application/octet-stream'
                            with open(cp, 'rb') as img_f:
                                raw_bytes = img_f.read()
                        b64 = base64.b64encode(raw_bytes).decode('utf-8')
                        data_uri = f"data:{mime};base64,{b64}"
                        break
                    except Exception:
                        pass

        # 提取 outerHTML 模板
        outer_html = str(elem)

        layers.append({
            "id": f"layer_{idx}",
            "name": layer_name,
            "tag": tag_name,
            "src": src,
            "dataUri": data_uri,
            "classes": classes,
            "isBackground": is_background,
            "left": left,
            "top": top,
            "width": width,
            "height": height,
            "rotate": rotate,
            "scale": scale,
            "zIndex": z_index,
            "opacity": opacity,
            "shadowOx": shadow_ox,
            "shadowOy": shadow_oy,
            "shadowBlur": shadow_blur,
            "shadowRgba": shadow_rgba,
            "extraStyle": extra_style,
            "outerHtml": outer_html,
            "rawStyle": inline_style
        })

    return {
        "width": canvas_w,
        "height": canvas_h,
        "bgColor": bg_color,
        "styleText": style_text,
        "layers": layers
    }


WORKBENCH_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>拼贴封面调优工作台 · Collage Cover Tuning Workbench</title>
<style>
  :root {
    --bg-base: #121215;
    --bg-surface: #1a1a20;
    --bg-card: #22222b;
    --bg-input: #2a2a36;
    --border-color: #323242;
    --border-active: #4f46e5;
    --text-primary: #f3f4f6;
    --text-secondary: #9ca3af;
    --accent-emerald: #10b981;
    --accent-emerald-hover: #059669;
    --accent-blue: #3b82f6;
    --accent-gold: #f59e0b;
    --danger: #ef4444;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background-color: var(--bg-base);
    color: var(--text-primary);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Source Han Sans CN", sans-serif;
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    user-select: none;
  }

  /* 顶部全局导航栏 */
  .header-bar {
    height: 56px;
    background: var(--bg-surface);
    border-bottom: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 20px;
    z-index: 100;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .logo-tag {
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    color: #fff;
    font-size: 11px;
    font-weight: 800;
    padding: 3px 8px;
    border-radius: 4px;
    letter-spacing: 0.5px;
  }

  .header-title {
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.5px;
  }

  .canvas-meta {
    font-size: 12px;
    color: var(--text-secondary);
    background: var(--bg-card);
    padding: 3px 8px;
    border-radius: 4px;
    border: 1px solid var(--border-color);
  }

  .header-center {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .toggle-btn {
    background: var(--bg-card);
    color: var(--text-secondary);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all 0.15s ease;
  }

  .toggle-btn:hover {
    color: var(--text-primary);
    border-color: #4b5563;
  }

  .toggle-btn.active {
    background: rgba(59, 130, 246, 0.15);
    color: #60a5fa;
    border-color: #3b82f6;
  }

  .toggle-btn.active-gold {
    background: rgba(245, 158, 11, 0.15);
    color: #fbbf24;
    border-color: #f59e0b;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  /* 核心一键复制按钮 */
  .btn-copy-pos {
    background: linear-gradient(135deg, var(--accent-emerald), #059669);
    color: #ffffff;
    font-weight: 700;
    font-size: 13px;
    padding: 8px 18px;
    border-radius: 6px;
    border: none;
    cursor: pointer;
    box-shadow: 0 2px 10px rgba(16, 185, 129, 0.35);
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .btn-copy-pos:hover {
    background: linear-gradient(135deg, #059669, #047857);
    transform: translateY(-1px);
    box-shadow: 0 4px 14px rgba(16, 185, 129, 0.5);
  }

  .btn-copy-pos:active {
    transform: translateY(0);
  }

  .btn-secondary {
    background: var(--bg-card);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    padding: 8px 14px;
    border-radius: 6px;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .btn-secondary:hover {
    border-color: #6b7280;
    background: var(--bg-input);
  }

  /* 主体工作区布局 */
  .workbench-body {
    flex: 1;
    display: flex;
    overflow: hidden;
    position: relative;
  }

  /* 左侧图层面板 */
  .layers-sidebar {
    width: 270px;
    background: var(--bg-surface);
    border-right: 1px solid var(--border-color);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .panel-header {
    height: 42px;
    padding: 0 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 12px;
    font-weight: 700;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 1px solid var(--border-color);
  }

  .layers-list {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .layer-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 10px;
    border-radius: 6px;
    background: var(--bg-card);
    border: 1px solid transparent;
    cursor: pointer;
    font-size: 12px;
    transition: all 0.12s ease;
  }

  .layer-item:hover {
    background: var(--bg-input);
    border-color: #3b3b4f;
  }

  .layer-item.active {
    background: rgba(79, 70, 229, 0.18);
    border-color: #4f46e5;
    color: #fff;
  }

  .layer-info {
    display: flex;
    align-items: center;
    gap: 8px;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
    flex: 1;
  }

  .layer-z-badge {
    font-size: 10px;
    padding: 1px 5px;
    border-radius: 3px;
    background: rgba(255, 255, 255, 0.08);
    color: var(--text-secondary);
    font-family: monospace;
  }

  .layer-name {
    overflow: hidden;
    text-overflow: ellipsis;
    font-size: 12px;
  }

  .layer-actions {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .icon-btn {
    background: transparent;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    font-size: 13px;
    padding: 3px;
    border-radius: 3px;
    line-height: 1;
  }

  .icon-btn:hover {
    color: var(--text-primary);
    background: rgba(255, 255, 255, 0.1);
  }

  .icon-btn.locked {
    color: var(--accent-gold);
  }

  .icon-btn.hidden-layer {
    opacity: 0.35;
  }

  /* 中间画布视窗 */
  .canvas-stage {
    flex: 1;
    background: #09090b;
    background-image: 
      radial-gradient(#1e1e28 1px, transparent 1px),
      radial-gradient(#1e1e28 1px, #09090b 1px);
    background-size: 24px 24px;
    background-position: 0 0, 12px 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: auto;
    position: relative;
    padding: 40px;
  }

  .canvas-container {
    position: relative;
    box-shadow: 0 25px 60px rgba(0, 0, 0, 0.8), 0 0 0 1px rgba(255, 255, 255, 0.08);
    transform-origin: center center;
    transition: transform 0.1s ease-out;
  }

  #canvas-viewport {
    position: relative;
    overflow: hidden;
    user-select: none;
  }

  /* 微信 1:1 安全区遮罩覆盖层 */
  .safe-zone-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 9999;
    display: none;
  }

  .safe-zone-overlay.active {
    display: block;
  }

  .mask-left, .mask-right {
    position: absolute;
    top: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.55);
    backdrop-filter: blur(2px);
  }

  .safe-frame-1x1 {
    position: absolute;
    top: 0;
    border: 2px dashed #f59e0b;
    box-shadow: 0 0 20px rgba(245, 158, 11, 0.3), inset 0 0 20px rgba(245, 158, 11, 0.15);
  }

  .safe-tag {
    position: absolute;
    top: 16px;
    left: 16px;
    background: #f59e0b;
    color: #1a1815;
    font-size: 18px;
    font-weight: 800;
    padding: 6px 14px;
    border-radius: 6px;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.4);
    letter-spacing: 1px;
  }

  /* 十字参考线 */
  .crosshair-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 9998;
    display: none;
  }

  .crosshair-overlay.active {
    display: block;
  }

  .crosshair-h {
    position: absolute;
    top: 50%;
    left: 0;
    right: 0;
    height: 1px;
    background: rgba(59, 130, 246, 0.45);
    border-bottom: 1px dashed rgba(59, 130, 246, 0.8);
  }

  .crosshair-v {
    position: absolute;
    left: 50%;
    top: 0;
    bottom: 0;
    width: 1px;
    background: rgba(59, 130, 246, 0.45);
    border-right: 1px dashed rgba(59, 130, 246, 0.8);
  }

  /* 图元高亮选框 */
  .selection-box {
    position: absolute;
    border: 2px solid #3b82f6;
    pointer-events: none;
    z-index: 9995;
    display: none;
    box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.5);
  }

  /* 右侧滑杆检查器面板 */
  .inspector-sidebar {
    width: 330px;
    background: var(--bg-surface);
    border-left: 1px solid var(--border-color);
    display: flex;
    flex-direction: column;
    overflow-y: auto;
  }

  .inspector-content {
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .control-group {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .group-title {
    font-size: 11px;
    font-weight: 700;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .slider-row {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .slider-label-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
  }

  .slider-label {
    color: var(--text-primary);
    font-weight: 500;
  }

  .slider-val-box {
    width: 68px;
    background: var(--bg-input);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    color: var(--text-primary);
    font-size: 12px;
    font-family: monospace;
    text-align: right;
    padding: 2px 6px;
  }

  .slider-val-box:focus {
    outline: none;
    border-color: #3b82f6;
  }

  .slider-ctrl {
    -webkit-appearance: none;
    appearance: none;
    width: 100%;
    height: 6px;
    border-radius: 3px;
    background: var(--bg-input);
    outline: none;
    cursor: pointer;
  }

  .slider-ctrl::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #3b82f6;
    cursor: pointer;
    border: 2px solid #ffffff;
    box-shadow: 0 1px 4px rgba(0,0,0,0.4);
    transition: transform 0.1s;
  }

  .slider-ctrl::-webkit-slider-thumb:hover {
    transform: scale(1.15);
  }

  /* 底部状态栏 */
  .status-bar {
    height: 28px;
    background: #0e0e11;
    border-top: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 16px;
    font-size: 11px;
    color: var(--text-secondary);
  }

  /* 弹窗与抽屉 */
  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    backdrop-filter: blur(4px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.2s ease;
  }

  .modal-overlay.active {
    opacity: 1;
    pointer-events: auto;
  }

  .modal-card {
    width: 680px;
    max-width: 90vw;
    background: var(--bg-surface);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .modal-header {
    height: 48px;
    padding: 0 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid var(--border-color);
  }

  .modal-title {
    font-size: 14px;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .modal-tabs {
    display: flex;
    background: var(--bg-card);
    border-bottom: 1px solid var(--border-color);
    padding: 0 20px;
  }

  .modal-tab {
    padding: 10px 16px;
    font-size: 12px;
    color: var(--text-secondary);
    border-bottom: 2px solid transparent;
    cursor: pointer;
  }

  .modal-tab.active {
    color: #3b82f6;
    border-bottom-color: #3b82f6;
    font-weight: 600;
  }

  .modal-body {
    padding: 16px 20px;
  }

  .code-preview {
    width: 100%;
    height: 280px;
    background: #09090b;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    color: #e2e8f0;
    font-family: Consolas, Monaco, "Courier New", monospace;
    font-size: 12px;
    line-height: 1.5;
    padding: 12px;
    resize: none;
    white-space: pre;
    overflow: auto;
  }

  .modal-footer {
    padding: 12px 20px;
    background: var(--bg-card);
    border-top: 1px solid var(--border-color);
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }

  /* Toast 提示 */
  .toast {
    position: fixed;
    bottom: 45px;
    left: 50%;
    transform: translateX(-50%) translateY(20px);
    background: #10b981;
    color: #ffffff;
    font-size: 13px;
    font-weight: 700;
    padding: 10px 22px;
    border-radius: 30px;
    box-shadow: 0 8px 24px rgba(16, 185, 129, 0.4);
    opacity: 0;
    pointer-events: none;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    z-index: 100000;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .toast.show {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
</style>
</head>
<body>

<!-- 1. 顶部操作栏 -->
<header class="header-bar">
  <div class="header-left">
    <span class="logo-tag">COLLAGE WORKBENCH</span>
    <span class="header-title">拼贴封面交互式调优工作台</span>
    <span class="canvas-meta" id="meta-resolution">2115 × 900 (2.35:1)</span>
  </div>

  <div class="header-center">
    <button class="toggle-btn active-gold" id="btn-toggle-safe" title="切换微信 1:1 抓取区遮罩">
      <span>👁️ 微信 1:1 安全视窗</span>
    </button>
    <button class="toggle-btn" id="btn-toggle-cross" title="切换居中十字线">
      <span>📐 居中参考线</span>
    </button>
    <div style="width: 1px; height: 18px; background: var(--border-color); margin: 0 4px;"></div>
    <button class="toggle-btn" id="btn-zoom-fit"><span>🔍 自适应大小</span></button>
    <button class="toggle-btn" id="btn-zoom-100"><span>100% 原始尺寸</span></button>
  </div>

  <div class="header-right">
    <button class="btn-secondary" id="btn-reset-layer" title="将当前选中零件重置为原始参数">↺ 重置选中零件</button>
    <button class="btn-copy-pos" id="btn-copy-main" title="将所有零件的最新绝对坐标和样式复制到剪贴板">
      <span>📋 一键复制合适的位置</span>
    </button>
    <button class="btn-export-img" id="btn-export-full-png" title="直接将微调后的全画幅画面导出为高清 PNG 文件" style="background: #0284c7; color: #fff; font-weight: 700; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; display: flex; align-items: center; gap: 6px; font-size: 13px;">
      <span>📸 导出高清封面 (PNG)</span>
    </button>
    <button class="btn-export-img" id="btn-export-crop-png" title="直接导出微信公众号 1:1 正方形缩略视窗图片" style="background: #0f766e; color: #fff; font-weight: 700; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; display: flex; align-items: center; gap: 6px; font-size: 13px;">
      <span>🔲 导出 1:1 方图</span>
    </button>
  </div>
</header>

<!-- 2. 主体工作区 -->
<div class="workbench-body">
  <!-- 左侧：图层层级列表 -->
  <aside class="layers-sidebar">
    <div class="panel-header">
      <span>图层列表 (从顶至底)</span>
      <span id="layer-count">0 个零件</span>
    </div>
    <div class="layers-list" id="layers-list-container">
      <!-- 动态注入 -->
    </div>
  </aside>

  <!-- 中间：实时渲染舞台 -->
  <main class="canvas-stage" id="canvas-stage">
    <div class="canvas-container" id="canvas-container">
      <!-- 真实画布视窗 -->
      <div id="canvas-viewport">
        <!-- 动态注入原始装配元素 -->
      </div>

      <!-- 微信 1:1 正方形安全视窗覆盖层 (居中 900x900) -->
      <div class="safe-zone-overlay active" id="safe-zone-overlay">
        <div class="mask-left" id="mask-left"></div>
        <div class="safe-frame-1x1" id="safe-frame-1x1">
          <div class="safe-tag">微信 1:1 抓取安全区 (900×900)</div>
        </div>
        <div class="mask-right" id="mask-right"></div>
      </div>

      <!-- 十字居中辅助线 -->
      <div class="crosshair-overlay" id="crosshair-overlay">
        <div class="crosshair-h"></div>
        <div class="crosshair-v"></div>
      </div>

      <!-- 图元选框 -->
      <div class="selection-box" id="selection-box"></div>
    </div>
  </main>

  <!-- 右侧：精细微调滑杆检查器 -->
  <aside class="inspector-sidebar">
    <div class="panel-header">
      <span id="inspector-layer-name">选择一个零件以调整</span>
      <button class="icon-btn" id="btn-lock-current" title="锁定/解锁当前零件">🔓</button>
    </div>

    <div class="inspector-content" id="inspector-controls">
      <!-- 坐标与尺寸 -->
      <div class="control-group">
        <div class="group-title">
          <span>几何坐标与定位</span>
          <span style="font-size:10px; color:#6b7280;">支持画布直接拖拽 / 方向键微调</span>
        </div>

        <div class="slider-row">
          <div class="slider-label-row">
            <span class="slider-label">水平位移 (X / Left)</span>
            <input type="number" class="slider-val-box" id="num-left" step="1">
          </div>
          <input type="range" class="slider-ctrl" id="slide-left" min="-500" max="2500" step="1">
        </div>

        <div class="slider-row">
          <div class="slider-label-row">
            <span class="slider-label">垂直位移 (Y / Top)</span>
            <input type="number" class="slider-val-box" id="num-top" step="1">
          </div>
          <input type="range" class="slider-ctrl" id="slide-top" min="-500" max="1500" step="1">
        </div>
      </div>

      <!-- 尺寸、旋转与图层 -->
      <div class="control-group">
        <div class="group-title"><span>形态变换与层级</span></div>

        <div class="slider-row">
          <div class="slider-label-row">
            <span class="slider-label">尺寸缩放 (Scale)</span>
            <input type="number" class="slider-val-box" id="num-scale" step="0.01" min="0.1" max="3">
          </div>
          <input type="range" class="slider-ctrl" id="slide-scale" min="0.1" max="2.5" step="0.01">
        </div>

        <div class="slider-row">
          <div class="slider-label-row">
            <span class="slider-label">旋转角度 (Rotate)</span>
            <input type="number" class="slider-val-box" id="num-rotate" step="0.5" min="-180" max="180">
          </div>
          <input type="range" class="slider-ctrl" id="slide-rotate" min="-90" max="90" step="0.5">
        </div>

        <div class="slider-row">
          <div class="slider-label-row">
            <span class="slider-label">图层层叠 (Z-Index)</span>
            <input type="number" class="slider-val-box" id="num-zindex" step="1" min="1" max="100">
          </div>
          <input type="range" class="slider-ctrl" id="slide-zindex" min="1" max="60" step="1">
        </div>

        <div class="slider-row">
          <div class="slider-label-row">
            <span class="slider-label">不透明度 (Opacity)</span>
            <input type="number" class="slider-val-box" id="num-opacity" step="0.05" min="0" max="1">
          </div>
          <input type="range" class="slider-ctrl" id="slide-opacity" min="0" max="1" step="0.01">
        </div>
      </div>

      <!-- 物理微距纸张投影 -->
      <div class="control-group">
        <div class="group-title"><span>物理纸张微距投影 (Drop-Shadow)</span></div>

        <div class="slider-row">
          <div class="slider-label-row">
            <span class="slider-label">水平投影偏角 (Offset X)</span>
            <input type="number" class="slider-val-box" id="num-shadow-ox" step="1">
          </div>
          <input type="range" class="slider-ctrl" id="slide-shadow-ox" min="-50" max="50" step="1">
        </div>

        <div class="slider-row">
          <div class="slider-label-row">
            <span class="slider-label">垂直落差厚度 (Offset Y)</span>
            <input type="number" class="slider-val-box" id="num-shadow-oy" step="1">
          </div>
          <input type="range" class="slider-ctrl" id="slide-shadow-oy" min="-50" max="60" step="1">
        </div>

        <div class="slider-row">
          <div class="slider-label-row">
            <span class="slider-label">漫反射模糊 (Blur)</span>
            <input type="number" class="slider-val-box" id="num-shadow-blur" step="1" min="0">
          </div>
          <input type="range" class="slider-ctrl" id="slide-shadow-blur" min="0" max="80" step="1">
        </div>
      </div>
    </div>
  </aside>
</div>

<!-- 3. 底部状态栏 -->
<footer class="status-bar">
  <div>快捷键：方向键精准移动 1px (Shift + 方向键移动 10px) · [Space + 拖动] 平移视窗</div>
  <div id="status-selection-info">已选：无</div>
</footer>

<!-- 4. 导出代码弹窗 -->
<div class="modal-overlay" id="export-modal">
  <div class="modal-card">
    <div class="modal-header">
      <div class="modal-title">
        <span>📋</span>
        <span>微调定位代码与装配工程导出</span>
      </div>
      <button class="icon-btn" id="btn-close-modal" style="font-size: 16px;">✕</button>
    </div>
    <div class="modal-tabs">
      <div class="modal-tab active" data-tab="css">CSS 零件定位代码</div>
      <div class="modal-tab" data-tab="html">完整更新后装配 HTML</div>
      <div class="modal-tab" data-tab="json">JSON 状态数据</div>
    </div>
    <div class="modal-body">
      <textarea class="code-preview" id="export-code-area" readonly></textarea>
    </div>
    <div class="modal-footer">
      <button class="btn-secondary" id="btn-download-html">💾 保存为 HTML 文件</button>
      <button class="btn-copy-pos" id="btn-copy-modal-code"><span>复制代码到剪贴板</span></button>
    </div>
  </div>
</div>

<!-- 5. Toast 浮层 -->
<div class="toast" id="toast-notify">
  <span>✅</span>
  <span id="toast-text">已复制合适的位置到剪贴板！</span>
</div>

<script>
// 注入装配工程元数据
const PROJECT_DATA = __PROJECT_DATA_PLACEHOLDER__;

// 动态注入装配工程自定义样式 (确保 .subtitle-wrapper, .subtitle-en, .subtitle-zh 等类完整生效)
if (PROJECT_DATA.styleText) {
  let customStyleElem = document.getElementById("assembly-injected-styles");
  if (!customStyleElem) {
    customStyleElem = document.createElement("style");
    customStyleElem.id = "assembly-injected-styles";
    document.head.appendChild(customStyleElem);
  }
  const filteredStyles = PROJECT_DATA.styleText
    .replace(/body\s*\{[^}]*?\}/gs, "")
    .replace(/\.canvas\s*\{[^}]*?\}/gs, "")
    .replace(/\*\s*\{[^}]*?\}/gs, "");
  customStyleElem.textContent = filteredStyles;
}

// 全局状态管理
let layers = JSON.parse(JSON.stringify(PROJECT_DATA.layers));
const originalLayers = JSON.parse(JSON.stringify(PROJECT_DATA.layers));
let selectedLayerIndex = -1;
let canvasScale = 0.55;
let isSafeZoneVisible = true;
let isCrosshairVisible = false;
let isDragging = false;
let dragStartX = 0;
let dragStartY = 0;
let elemStartLeft = 0;
let elemStartTop = 0;

// 初始化 DOM
const viewport = document.getElementById("canvas-viewport");
const canvasContainer = document.getElementById("canvas-container");
const canvasStage = document.getElementById("canvas-stage");
const layersListContainer = document.getElementById("layers-list-container");
const selectionBox = document.getElementById("selection-box");

viewport.style.width = PROJECT_DATA.width + "px";
viewport.style.height = PROJECT_DATA.height + "px";
viewport.style.backgroundColor = PROJECT_DATA.bgColor;

const ratioText = (PROJECT_DATA.width / PROJECT_DATA.height).toFixed(2);
document.getElementById("meta-resolution").innerText = `${PROJECT_DATA.width} × ${PROJECT_DATA.height} (${ratioText}:1)`;

// 设置微信 1:1 安全区几何尺寸 (自适应居中正方形)
const safeSize = Math.min(PROJECT_DATA.width, PROJECT_DATA.height);
const safeLeft = (PROJECT_DATA.width - safeSize) / 2;
const safeTop = (PROJECT_DATA.height - safeSize) / 2;
const safeRight = safeLeft + safeSize;

const maskLeft = document.getElementById("mask-left");
const safeFrame = document.getElementById("safe-frame-1x1");
const maskRight = document.getElementById("mask-right");

maskLeft.style.left = "0px";
maskLeft.style.top = "0px";
maskLeft.style.width = Math.max(0, safeLeft) + "px";
maskLeft.style.height = PROJECT_DATA.height + "px";

safeFrame.style.left = safeLeft + "px";
safeFrame.style.top = safeTop + "px";
safeFrame.style.width = safeSize + "px";
safeFrame.style.height = safeSize + "px";

maskRight.style.left = safeRight + "px";
maskRight.style.top = "0px";
maskRight.style.width = Math.max(0, PROJECT_DATA.width - safeRight) + "px";
maskRight.style.height = PROJECT_DATA.height + "px";

const safeTag = safeFrame.querySelector(".safe-tag");
if (safeTag) {
  safeTag.innerText = `微信 1:1 安全视窗 (${Math.round(safeSize)}×${Math.round(safeSize)})`;
}

// 构建真实 DOM 图元
function renderCanvasElements() {
  viewport.innerHTML = "";
  layers.forEach((layer, idx) => {
    let elem;
    if (layer.tag === "img") {
      elem = document.createElement("img");
      elem.src = layer.dataUri || layer.src;
    } else {
      const tempDiv = document.createElement("div");
      tempDiv.innerHTML = layer.outerHtml.trim();
      elem = tempDiv.firstElementChild || document.createElement("div");
    }

    elem.id = `canvas-layer-${idx}`;
    elem.dataset.layerIndex = idx;
    elem.dataset.layerId = layer.id;
    elem.style.position = "absolute";
    elem.style.boxSizing = "border-box";
    elem.style.cursor = layer.isBackground ? "default" : "move";

    if (layer.classes && layer.classes.length > 0) {
      elem.className = layer.classes.join(" ");
    }

    if (layer.width) elem.style.width = layer.width + "px";
    if (layer.height) elem.style.height = layer.height + "px";

    if (layer.extraStyle) {
      const decls = layer.extraStyle.split(";");
      decls.forEach(d => {
        if (d.includes(":")) {
          const parts = d.split(":");
          const k = parts[0].trim();
          const v = parts.slice(1).join(":").trim();
          if (k && v) elem.style.setProperty(k, v);
        }
      });
    }

    viewport.appendChild(elem);
    applyLayerStyle(idx);

    // 绑定画布内交互选中与拖拽
    elem.addEventListener("mousedown", (e) => {
      e.stopPropagation();
      selectLayer(idx);
      if (!layer.locked && !layer.isBackground) {
        startDrag(e);
      }
    });
  });
}

// 刷新单个图元的真实样式
function applyLayerStyle(idx) {
  const layer = layers[idx];
  const elem = document.getElementById(`canvas-layer-${idx}`);
  if (!elem) return;

  elem.style.left = layer.left + "px";
  elem.style.top = layer.top + "px";
  elem.style.transform = `rotate(${layer.rotate}deg) scale(${layer.scale})`;
  elem.style.zIndex = layer.zIndex;
  elem.style.opacity = layer.opacity;
  elem.style.display = layer.hidden ? "none" : "";

  // 物理投影
  if (layer.shadowBlur > 0 || layer.shadowOx !== 0 || layer.shadowOy !== 0) {
    elem.style.filter = `drop-shadow(${layer.shadowOx}px ${layer.shadowOy}px ${layer.shadowBlur}px ${layer.shadowRgba})`;
  } else {
    elem.style.filter = "none";
  }

  updateSelectionBox();
}

// 渲染左侧图层列表 (按 zIndex 降序排列展示)
function renderLayersList() {
  layersListContainer.innerHTML = "";
  document.getElementById("layer-count").innerText = `${layers.length} 个零件`;

  // 保持与原数组索引一致，展示反转顺序 (高层在上)
  const displayIndices = layers.map((_, i) => i).sort((a, b) => layers[b].zIndex - layers[a].zIndex);

  displayIndices.forEach((idx) => {
    const layer = layers[idx];
    const item = document.createElement("div");
    item.className = `layer-item ${selectedLayerIndex === idx ? "active" : ""}`;
    item.dataset.layerIndex = idx;

    item.innerHTML = `
      <div class="layer-info">
        <span class="layer-z-badge">Z${layer.zIndex}</span>
        <span class="layer-name" title="${layer.name}">${layer.name}</span>
      </div>
      <div class="layer-actions">
        <button class="icon-btn ${layer.locked ? 'locked' : ''}" title="锁定" onclick="toggleLock(${idx}, event)">
          ${layer.locked ? '🔒' : '🔓'}
        </button>
        <button class="icon-btn ${layer.hidden ? 'hidden-layer' : ''}" title="显示/隐藏" onclick="toggleVisibility(${idx}, event)">
          ${layer.hidden ? '👁️‍🗨️' : '👁️'}
        </button>
      </div>
    `;

    item.addEventListener("click", () => selectLayer(idx));
    layersListContainer.appendChild(item);
  });
}

// 选中图层
function selectLayer(idx) {
  selectedLayerIndex = idx;
  const layer = layers[idx];

  // 更新左侧列表状态
  document.querySelectorAll(".layer-item").forEach(item => {
    item.classList.toggle("active", parseInt(item.dataset.layerIndex) === idx);
  });

  // 更新右侧检查器标题与锁定按钮
  document.getElementById("inspector-layer-name").innerText = layer.name;
  const lockBtn = document.getElementById("btn-lock-current");
  lockBtn.innerText = layer.locked ? "🔒" : "🔓";
  lockBtn.classList.toggle("locked", layer.locked);

  document.getElementById("status-selection-info").innerText = `已选零件：[${layer.name}] (X: ${Math.round(layer.left)}, Y: ${Math.round(layer.top)}, Z: ${layer.zIndex})`;

  // 同步滑杆与数字框
  syncInspectorValues(layer);
  updateSelectionBox();
}

function syncInspectorValues(layer) {
  document.getElementById("slide-left").value = layer.left;
  document.getElementById("num-left").value = Math.round(layer.left);

  document.getElementById("slide-top").value = layer.top;
  document.getElementById("num-top").value = Math.round(layer.top);

  document.getElementById("slide-scale").value = layer.scale;
  document.getElementById("num-scale").value = layer.scale.toFixed(2);

  document.getElementById("slide-rotate").value = layer.rotate;
  document.getElementById("num-rotate").value = layer.rotate.toFixed(1);

  document.getElementById("slide-zindex").value = layer.zIndex;
  document.getElementById("num-zindex").value = layer.zIndex;

  document.getElementById("slide-opacity").value = layer.opacity;
  document.getElementById("num-opacity").value = layer.opacity.toFixed(2);

  document.getElementById("slide-shadow-ox").value = layer.shadowOx;
  document.getElementById("num-shadow-ox").value = layer.shadowOx;

  document.getElementById("slide-shadow-oy").value = layer.shadowOy;
  document.getElementById("num-shadow-oy").value = layer.shadowOy;

  document.getElementById("slide-shadow-blur").value = layer.shadowBlur;
  document.getElementById("num-shadow-blur").value = layer.shadowBlur;
}

// 更新图元选中线框
function updateSelectionBox() {
  if (selectedLayerIndex < 0 || layers[selectedLayerIndex].hidden) {
    selectionBox.style.display = "none";
    return;
  }
  const elem = document.getElementById(`canvas-layer-${selectedLayerIndex}`);
  if (!elem) {
    selectionBox.style.display = "none";
    return;
  }

  const rect = elem.getBoundingClientRect();
  const containerRect = canvasContainer.getBoundingClientRect();

  selectionBox.style.display = "block";
  selectionBox.style.left = (rect.left - containerRect.left) / canvasScale + "px";
  selectionBox.style.top = (rect.top - containerRect.top) / canvasScale + "px";
  selectionBox.style.width = rect.width / canvasScale + "px";
  selectionBox.style.height = rect.height / canvasScale + "px";
}

// 滑杆双向绑定
function setupSliderSync(sliderId, numId, prop, precision = 0) {
  const slider = document.getElementById(sliderId);
  const numInput = document.getElementById(numId);

  slider.addEventListener("input", () => {
    if (selectedLayerIndex < 0) return;
    const val = parseFloat(slider.value);
    layers[selectedLayerIndex][prop] = val;
    numInput.value = precision > 0 ? val.toFixed(precision) : Math.round(val);
    applyLayerStyle(selectedLayerIndex);
    if (prop === "zIndex") renderLayersList();
  });

  numInput.addEventListener("input", () => {
    if (selectedLayerIndex < 0) return;
    const val = parseFloat(numInput.value) || 0;
    layers[selectedLayerIndex][prop] = val;
    slider.value = val;
    applyLayerStyle(selectedLayerIndex);
    if (prop === "zIndex") renderLayersList();
  });
}

setupSliderSync("slide-left", "num-left", "left", 0);
setupSliderSync("slide-top", "num-top", "top", 0);
setupSliderSync("slide-scale", "num-scale", "scale", 2);
setupSliderSync("slide-rotate", "num-rotate", "rotate", 1);
setupSliderSync("slide-zindex", "num-zindex", "zIndex", 0);
setupSliderSync("slide-opacity", "num-opacity", "opacity", 2);
setupSliderSync("slide-shadow-ox", "num-shadow-ox", "shadowOx", 0);
setupSliderSync("slide-shadow-oy", "num-shadow-oy", "shadowOy", 0);
setupSliderSync("slide-shadow-blur", "num-shadow-blur", "shadowBlur", 0);

// 画布直接拖拽逻辑
function startDrag(e) {
  isDragging = true;
  dragStartX = e.clientX;
  dragStartY = e.clientY;
  elemStartLeft = layers[selectedLayerIndex].left;
  elemStartTop = layers[selectedLayerIndex].top;

  window.addEventListener("mousemove", onDragMove);
  window.addEventListener("mouseup", endDrag);
}

function onDragMove(e) {
  if (!isDragging || selectedLayerIndex < 0) return;
  const dx = (e.clientX - dragStartX) / canvasScale;
  const dy = (e.clientY - dragStartY) / canvasScale;

  layers[selectedLayerIndex].left = Math.round(elemStartLeft + dx);
  layers[selectedLayerIndex].top = Math.round(elemStartTop + dy);

  applyLayerStyle(selectedLayerIndex);
  syncInspectorValues(layers[selectedLayerIndex]);
}

function endDrag() {
  isDragging = false;
  window.removeEventListener("mousemove", onDragMove);
  window.removeEventListener("mouseup", endDrag);
}

// 键盘快捷键微调 (1px 或 10px)
window.addEventListener("keydown", (e) => {
  if (selectedLayerIndex < 0 || document.activeElement.tagName === "INPUT" || document.activeElement.tagName === "TEXTAREA") {
    return;
  }
  const step = e.shiftKey ? 10 : 1;
  let handled = false;

  if (e.key === "ArrowLeft") {
    layers[selectedLayerIndex].left -= step;
    handled = true;
  } else if (e.key === "ArrowRight") {
    layers[selectedLayerIndex].left += step;
    handled = true;
  } else if (e.key === "ArrowUp") {
    layers[selectedLayerIndex].top -= step;
    handled = true;
  } else if (e.key === "ArrowDown") {
    layers[selectedLayerIndex].top += step;
    handled = true;
  }

  if (handled) {
    e.preventDefault();
    applyLayerStyle(selectedLayerIndex);
    syncInspectorValues(layers[selectedLayerIndex]);
  }
});

// 缩放适配
function setZoom(scale) {
  canvasScale = scale;
  canvasContainer.style.transform = `scale(${canvasScale})`;
  updateSelectionBox();
}

function fitToScreen() {
  const stageWidth = canvasStage.clientWidth - 80;
  const stageHeight = canvasStage.clientHeight - 80;
  const scaleX = stageWidth / PROJECT_DATA.width;
  const scaleY = stageHeight / PROJECT_DATA.height;
  const fitScale = Math.min(scaleX, scaleY, 0.95);
  setZoom(Math.max(0.2, fitScale));
}

document.getElementById("btn-zoom-fit").addEventListener("click", fitToScreen);
document.getElementById("btn-zoom-100").addEventListener("click", () => setZoom(1.0));

// 安全区与辅助线切换
const btnToggleSafe = document.getElementById("btn-toggle-safe");
btnToggleSafe.addEventListener("click", () => {
  isSafeZoneVisible = !isSafeZoneVisible;
  btnToggleSafe.classList.toggle("active-gold", isSafeZoneVisible);
  document.getElementById("safe-zone-overlay").classList.toggle("active", isSafeZoneVisible);
});

const btnToggleCross = document.getElementById("btn-toggle-cross");
btnToggleCross.addEventListener("click", () => {
  isCrosshairVisible = !isCrosshairVisible;
  btnToggleCross.classList.toggle("active", isCrosshairVisible);
  document.getElementById("crosshair-overlay").classList.toggle("active", isCrosshairVisible);
});

// 重置选中零件
document.getElementById("btn-reset-layer").addEventListener("click", () => {
  if (selectedLayerIndex < 0) return;
  layers[selectedLayerIndex] = JSON.parse(JSON.stringify(originalLayers[selectedLayerIndex]));
  applyLayerStyle(selectedLayerIndex);
  syncInspectorValues(layers[selectedLayerIndex]);
  renderLayersList();
  showToast(`已重置 [${layers[selectedLayerIndex].name}] 到原始坐标`);
});

// 锁定与隐藏
window.toggleLock = function(idx, e) {
  e.stopPropagation();
  layers[idx].locked = !layers[idx].locked;
  renderLayersList();
  if (selectedLayerIndex === idx) {
    document.getElementById("btn-lock-current").innerText = layers[idx].locked ? "🔒" : "🔓";
  }
};

window.toggleVisibility = function(idx, e) {
  e.stopPropagation();
  layers[idx].hidden = !layers[idx].hidden;
  applyLayerStyle(idx);
  renderLayersList();
};

document.getElementById("btn-lock-current").addEventListener("click", () => {
  if (selectedLayerIndex < 0) return;
  layers[selectedLayerIndex].locked = !layers[selectedLayerIndex].locked;
  renderLayersList();
  document.getElementById("btn-lock-current").innerText = layers[selectedLayerIndex].locked ? "🔒" : "🔓";
});

// 生成导出的 CSS / HTML
function generateExportCSS() {
  let cssLines = [];
  cssLines.push(`/* ============================================================== */`);
  cssLines.push(`/* 拼贴封面微调定位结果 (Collage Cover Tuned CSS Coordinates)     */`);
  cssLines.push(`/* 画布画幅：${PROJECT_DATA.width} × ${PROJECT_DATA.height}                                      */`);
  cssLines.push(`/* ============================================================== */\n`);

  layers.forEach((layer, idx) => {
    let selector = "";
    if (layer.classes && layer.classes.length > 0) {
      selector = `.${layer.classes[0]}`;
    } else if (layer.src) {
      const filename = layer.src.split("/").pop();
      selector = `img[src*="${filename}"]`;
    } else if (layer.id) {
      selector = `#${layer.id}`;
    } else {
      selector = `.layer-${idx + 1}`;
    }

    cssLines.push(`/* 图层 ${idx + 1}: ${layer.name} */`);
    let styleRules = [];
    styleRules.push(`  position: absolute;`);
    styleRules.push(`  left: ${Math.round(layer.left)}px;`);
    styleRules.push(`  top: ${Math.round(layer.top)}px;`);
    if (layer.width) styleRules.push(`  width: ${Math.round(layer.width)}px;`);
    if (layer.height) styleRules.push(`  height: ${Math.round(layer.height)}px;`);
    else styleRules.push(`  height: auto;`);
    styleRules.push(`  z-index: ${layer.zIndex};`);

    let transformParts = [];
    if (layer.rotate !== 0) transformParts.push(`rotate(${layer.rotate}deg)`);
    if (layer.scale !== 1) transformParts.push(`scale(${layer.scale})`);
    if (transformParts.length > 0) {
      styleRules.push(`  transform: ${transformParts.join(" ")};`);
    }

    if (layer.opacity !== 1) {
      styleRules.push(`  opacity: ${layer.opacity};`);
    }

    if (layer.shadowBlur > 0 || layer.shadowOx !== 0 || layer.shadowOy !== 0) {
      styleRules.push(`  filter: drop-shadow(${layer.shadowOx}px ${layer.shadowOy}px ${layer.shadowBlur}px ${layer.shadowRgba});`);
    }

    if (layer.extraStyle) {
      styleRules.push(`  ${layer.extraStyle}`);
    }

    cssLines.push(`${selector} {`);
    cssLines.push(styleRules.join("\n"));
    cssLines.push(`}\n`);

    // 同时输出对应内联 style
    let inlineList = [];
    inlineList.push(`position:absolute;`);
    inlineList.push(`left:${Math.round(layer.left)}px;`);
    inlineList.push(`top:${Math.round(layer.top)}px;`);
    if (layer.width) inlineList.push(`width:${Math.round(layer.width)}px;`);
    if (layer.height) inlineList.push(`height:${Math.round(layer.height)}px;`);
    else inlineList.push(`height:auto;`);
    inlineList.push(`z-index:${layer.zIndex};`);
    if (transformParts.length > 0) inlineList.push(`transform:${transformParts.join(" ")};`);
    if (layer.opacity !== 1) inlineList.push(`opacity:${layer.opacity};`);
    if (layer.shadowBlur > 0 || layer.shadowOx !== 0 || layer.shadowOy !== 0) {
      inlineList.push(`filter:drop-shadow(${layer.shadowOx}px ${layer.shadowOy}px ${layer.shadowBlur}px ${layer.shadowRgba});`);
    }
    if (layer.extraStyle) inlineList.push(layer.extraStyle);

    cssLines.push(`/* 对应内联 style 属性: */`);
    cssLines.push(`style="${inlineList.join(' ')}"\n`);
  });

  return cssLines.join("\n");
}

function generateExportHTML() {
  let html = `<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="UTF-8">\n<style>\n`;
  html += `  * { box-sizing: border-box; margin: 0; padding: 0; }\n`;
  html += `  body {\n    width: ${PROJECT_DATA.width}px;\n    height: ${PROJECT_DATA.height}px;\n    overflow: hidden;\n    background-color: ${PROJECT_DATA.bgColor};\n`;
  html += `    font-family: "PingFang SC", "Hiragino Sans GB", "Source Han Serif CN", "Noto Serif CJK SC", "SimSun", serif;\n`;
  html += `    -webkit-font-smoothing: antialiased;\n  }\n`;
  html += `  .canvas {\n    position: relative;\n    width: ${PROJECT_DATA.width}px;\n    height: ${PROJECT_DATA.height}px;\n    overflow: hidden;\n  }\n`;

  if (PROJECT_DATA.styleText) {
    const customRules = PROJECT_DATA.styleText
      .replace(/body\s*\{[^}]*?\}/gs, "")
      .replace(/\.canvas\s*\{[^}]*?\}/gs, "")
      .replace(/\*\s*\{[^}]*?\}/gs, "")
      .trim();
    if (customRules) {
      html += `  /* 附加主题与图元样式 */\n  ${customRules}\n`;
    }
  }
  html += `</style>\n</head>\n<body>\n<div class="canvas">\n`;

  layers.forEach((layer, idx) => {
    let styleAttr = [];
    styleAttr.push(`position:absolute;`);
    styleAttr.push(`left:${Math.round(layer.left)}px;`);
    styleAttr.push(`top:${Math.round(layer.top)}px;`);
    if (layer.width) styleAttr.push(`width:${Math.round(layer.width)}px;`);
    if (layer.height) styleAttr.push(`height:${Math.round(layer.height)}px;`);
    else styleAttr.push(`height:auto;`);
    styleAttr.push(`z-index:${layer.zIndex};`);

    let transforms = [];
    if (layer.rotate !== 0) transforms.push(`rotate(${layer.rotate}deg)`);
    if (layer.scale !== 1) transforms.push(`scale(${layer.scale})`);
    if (transforms.length > 0) styleAttr.push(`transform:${transforms.join(" ")};`);
    if (layer.opacity !== 1) styleAttr.push(`opacity:${layer.opacity};`);

    if (layer.shadowBlur > 0 || layer.shadowOx !== 0 || layer.shadowOy !== 0) {
      styleAttr.push(`filter:drop-shadow(${layer.shadowOx}px ${layer.shadowOy}px ${layer.shadowBlur}px ${layer.shadowRgba});`);
    }
    if (layer.extraStyle) styleAttr.push(layer.extraStyle);

    let classAttr = layer.classes && layer.classes.length > 0 ? ` class="${layer.classes.join(" ")}"` : "";

    html += `  <!-- ${idx + 1}. ${layer.name} (z: ${layer.zIndex}) -->\n`;
    if (layer.tag === "img") {
      html += `  <img src="${layer.src}"${classAttr} style="${styleAttr.join(' ')}" />\n\n`;
    } else {
      const temp = document.createElement("div");
      temp.innerHTML = layer.outerHtml.trim();
      const child = temp.firstElementChild;
      if (child) {
        child.setAttribute("style", styleAttr.join(" "));
        html += `  ${child.outerHTML}\n\n`;
      }
    }
  });

  html += `</div>\n</body>\n</html>\n`;
  return html;
}

// 统一跨浏览器剪贴板写入与降级
function copyToClipboard(text, successMsg = "✅ 已成功复制到剪贴板！") {
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(() => {
      showToast(successMsg);
    }).catch(() => {
      fallbackCopy(text, successMsg);
    });
  } else {
    fallbackCopy(text, successMsg);
  }
}

function fallbackCopy(text, successMsg) {
  try {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.top = "-9999px";
    textArea.style.left = "-9999px";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    const successful = document.execCommand("copy");
    document.body.removeChild(textArea);
    if (successful) {
      showToast(successMsg);
      return;
    }
  } catch (err) {}
  showToast("📋 请在弹出面板中直接按 Ctrl+C 复制代码");
}

// 核心【一键复制合适的位置】
const btnCopyMain = document.getElementById("btn-copy-main");
btnCopyMain.addEventListener("click", () => {
  const cssCode = generateExportCSS();
  copyToClipboard(cssCode, "✅ 已成功复制最新零件定位！可直接贴入工程或发给 AI 热修复。");
  openExportModal("css");
});

// 弹窗逻辑
let currentModalTab = "css";
function openExportModal(tab = "css") {
  currentModalTab = tab;
  updateModalContent();
  document.getElementById("export-modal").classList.add("active");
}

function updateModalContent() {
  const textarea = document.getElementById("export-code-area");
  document.querySelectorAll(".modal-tab").forEach(t => {
    t.classList.toggle("active", t.dataset.tab === currentModalTab);
  });

  if (currentModalTab === "css") {
    textarea.value = generateExportCSS();
  } else if (currentModalTab === "html") {
    textarea.value = generateExportHTML();
  } else if (currentModalTab === "json") {
    textarea.value = JSON.stringify(layers, null, 2);
  }
}

document.querySelectorAll(".modal-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    currentModalTab = tab.dataset.tab;
    updateModalContent();
  });
});

document.getElementById("btn-close-modal").addEventListener("click", () => {
  document.getElementById("export-modal").classList.remove("active");
});

document.getElementById("btn-copy-modal-code").addEventListener("click", () => {
  const code = document.getElementById("export-code-area").value;
  copyToClipboard(code, "✅ 对应格式代码已复制到剪贴板！");
});

document.getElementById("btn-download-html").addEventListener("click", () => {
  const blob = new Blob([generateExportHTML()], { type: "text/html;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "tuned_cover.html";
  a.click();
  showToast("💾 HTML 文件已触发下载！");
});

// 纯前端 Canvas 物理全像素无损导出 PNG
async function exportFullCanvasImage(cropSquare = false) {
  showToast("⏳ 正在合成高清图片并导出...");
  
  const canvasW = PROJECT_DATA.width || 2115;
  const canvasH = PROJECT_DATA.height || 900;
  
  const targetW = cropSquare ? Math.min(canvasW, canvasH) : canvasW;
  const targetH = cropSquare ? Math.min(canvasW, canvasH) : canvasH;
  
  const canvas = document.createElement("canvas");
  canvas.width = targetW;
  canvas.height = targetH;
  const ctx = canvas.getContext("2d");
  
  // 填充背景色
  ctx.fillStyle = PROJECT_DATA.bgColor || "#faefd3";
  ctx.fillRect(0, 0, targetW, targetH);
  
  if (cropSquare) {
    const offsetX = (canvasW - targetW) / 2;
    const offsetY = (canvasH - targetH) / 2;
    ctx.translate(-offsetX, -offsetY);
  }

  // 1. 等待画布内所有图片完成解码与就绪
  const imageElements = Array.from(viewport.querySelectorAll("img"));
  await Promise.all(imageElements.map(img => {
    if (img.decode) return img.decode().catch(() => {});
    if (img.complete) return Promise.resolve();
    return new Promise(resolve => {
      img.onload = img.onerror = resolve;
    });
  }));

  // 2. 按 z-index 拓扑深度升序绘制
  const sortedLayers = layers
    .map((layer, idx) => ({ layer, idx }))
    .filter(({ layer }) => !layer.hidden && layer.visible !== false)
    .sort((a, b) => a.layer.zIndex - b.layer.zIndex);
    
  for (const { layer, idx } of sortedLayers) {
    const domElem = document.getElementById(`canvas-layer-${idx}`) 
      || document.querySelector(`[data-layer-id="${layer.id}"]`) 
      || document.getElementById(layer.id);
    if (!domElem) continue;

    let drawW = layer.width;
    let drawH = layer.height;

    let imgElem = null;
    if (layer.tag === "img" || domElem.tagName === "IMG") {
      imgElem = domElem.tagName === "IMG" ? domElem : domElem.querySelector("img");
    }

    if (imgElem) {
      const natW = imgElem.naturalWidth || 0;
      const natH = imgElem.naturalHeight || 0;
      if (!drawW && !drawH) {
        drawW = domElem.offsetWidth || natW || 100;
        drawH = domElem.offsetHeight || natH || 100;
      } else if (drawW && !drawH) {
        drawH = (natW > 0 && natH > 0) ? Math.round(drawW * natH / natW) : (domElem.offsetHeight || drawW);
      } else if (!drawW && drawH) {
        drawW = (natW > 0 && natH > 0) ? Math.round(drawH * natW / natH) : (domElem.offsetWidth || drawH);
      }
    } else {
      drawW = drawW || domElem.offsetWidth || 100;
      drawH = drawH || domElem.offsetHeight || 40;
    }

    drawW = Math.max(1, drawW || 1);
    drawH = Math.max(1, drawH || 1);

    ctx.save();

    // 旋转缩放中心：图元几何中心
    const cx = layer.left + drawW / 2;
    const cy = layer.top + drawH / 2;
    ctx.translate(cx, cy);
    if (layer.rotate) {
      ctx.rotate((layer.rotate * Math.PI) / 180);
    }
    if (layer.scale && layer.scale !== 1) {
      ctx.scale(layer.scale, layer.scale);
    }
    ctx.translate(-cx, -cy);

    if (layer.opacity !== undefined && layer.opacity !== null) {
      ctx.globalAlpha = layer.opacity;
    }

    if (layer.shadowBlur > 0 || layer.shadowOx !== 0 || layer.shadowOy !== 0) {
      ctx.shadowOffsetX = layer.shadowOx;
      ctx.shadowOffsetY = layer.shadowOy;
      ctx.shadowBlur = layer.shadowBlur;
      ctx.shadowColor = layer.shadowRgba || "rgba(0, 0, 0, 0.25)";
    }

    if (imgElem) {
      try {
        ctx.drawImage(imgElem, layer.left, layer.top, drawW, drawH);
      } catch (err) {
        console.warn("ctx.drawImage failed for layer", layer.name, err);
      }
    } else {
      let foreignRendered = false;
      try {
        const clone = domElem.cloneNode(true);
        clone.style.position = "static";
        clone.style.left = "0";
        clone.style.top = "0";
        clone.style.transform = "none";
        clone.style.margin = "0";
        
        const customStyles = PROJECT_DATA.styleText || "";
        const svgString = `<svg xmlns="http://www.w3.org/2000/svg" width="${drawW}" height="${drawH}">
          <style>${customStyles}</style>
          <foreignObject width="100%" height="100%">
            <div xmlns="http://www.w3.org/1999/xhtml">
              ${clone.outerHTML}
            </div>
          </foreignObject>
        </svg>`;
        
        const svgImg = new Image();
        svgImg.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svgString);
        await svgImg.decode();
        ctx.drawImage(svgImg, layer.left, layer.top, drawW, drawH);
        foreignRendered = true;
      } catch (e) {
        console.warn("ForeignObject rendering failed, falling back to manual text drawing:", e);
      }

      if (!foreignRendered) {
        const enElem = domElem.querySelector(".subtitle-en");
        const zhElem = domElem.querySelector(".subtitle-zh");
        if (enElem && zhElem) {
          const enStyle = window.getComputedStyle(enElem);
          ctx.textBaseline = "top";
          ctx.font = `${enStyle.fontWeight || '800'} ${enStyle.fontSize || '24px'} ${enStyle.fontFamily || 'sans-serif'}`;
          ctx.fillStyle = enStyle.color || "#1a1815";
          ctx.shadowColor = "rgba(255, 255, 255, 0.9)";
          ctx.shadowOffsetX = 0;
          ctx.shadowOffsetY = 1;
          ctx.shadowBlur = 2;
          if (ctx.letterSpacing && enStyle.letterSpacing && enStyle.letterSpacing !== "normal") {
            ctx.letterSpacing = enStyle.letterSpacing;
          }
          ctx.fillText(enElem.innerText.trim(), layer.left, layer.top);

          const zhStyle = window.getComputedStyle(zhElem);
          ctx.font = `${zhStyle.fontWeight || '700'} ${zhStyle.fontSize || '26px'} ${zhStyle.fontFamily || 'sans-serif'}`;
          ctx.fillStyle = zhStyle.color || "#382e26";
          if (ctx.letterSpacing && zhStyle.letterSpacing && zhStyle.letterSpacing !== "normal") {
            ctx.letterSpacing = zhStyle.letterSpacing;
          }
          const enHeight = enElem.offsetHeight || 30;
          const gap = parseFloat(window.getComputedStyle(domElem).gap) || 6;
          ctx.fillText(zhElem.innerText.trim(), layer.left, layer.top + enHeight + gap);
        } else if (domElem.innerText && domElem.innerText.trim()) {
          ctx.textBaseline = "top";
          ctx.font = "700 24px 'PingFang SC', 'Source Han Sans CN', 'Microsoft YaHei', sans-serif";
          ctx.fillStyle = "#1a1815";
          ctx.fillText(domElem.innerText.trim(), layer.left, layer.top);
        }
      }
    }

    ctx.restore();
  }

  canvas.toBlob((blob) => {
    if (!blob) {
      showToast("❌ 导出失败，请重试");
      return;
    }
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = cropSquare ? "tuned_cover_1x1_crop.png" : `tuned_cover_${canvasW}x${canvasH}.png`;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(a.href);
    }, 5000);
    showToast(cropSquare ? "✅ 微信 1:1 方形图已下载！" : `✅ ${canvasW}×${canvasH} 高清封面已下载！`);
  }, "image/png");
}

document.getElementById("btn-export-full-png").addEventListener("click", () => {
  exportFullCanvasImage(false);
});

document.getElementById("btn-export-crop-png").addEventListener("click", () => {
  exportFullCanvasImage(true);
});

// Toast 提示
let toastTimeout;
function showToast(msg) {
  const toast = document.getElementById("toast-notify");
  document.getElementById("toast-text").innerText = msg;
  toast.classList.add("show");
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => {
    toast.classList.remove("show");
  }, 2800);
}

// 启动初始化
renderCanvasElements();
renderLayersList();
setTimeout(() => {
  fitToScreen();
  // 默认选中第一个非背景图层（通常是文字条或主体人物）
  const defaultSelectIdx = layers.findIndex(l => !l.isBackground && l.name.includes("text")) !== -1
    ? layers.findIndex(l => !l.isBackground && l.name.includes("text"))
    : 1;
  if (layers.length > defaultSelectIdx) selectLayer(defaultSelectIdx);
}, 100);

// 窗口尺寸自适应
window.addEventListener("resize", () => {
  updateSelectionBox();
});
</script>
</body>
</html>
"""


def generate_workbench(input_html, output_html=None):
    if not os.path.exists(input_html):
        print(f"Error: Input HTML file '{input_html}' does not exist.")
        sys.exit(1)

    if not output_html:
        dirname = os.path.dirname(input_html)
        basename = os.path.basename(input_html)
        name, _ = os.path.splitext(basename)
        # 若是 <slug>_wechat_2115x900.html，提取前缀作为 workbench 命名
        slug = re.sub(r'_(wechat_\d+x\d+|landscape_\d+x\d+|xhs_\d+x\d+)$', '', name)
        output_html = os.path.join(dirname, f"{slug}_workbench.html")

    print(f"[*] Parsing assembly HTML: {input_html}")
    project_data = parse_assembly_html(input_html)
    print(f"    - Canvas dimensions: {project_data['width']}x{project_data['height']}")
    print(f"    - Extracted layers: {len(project_data['layers'])}")

    data_json = json.dumps(project_data, ensure_ascii=False, indent=2)

    # 替换占位符
    final_html = WORKBENCH_TEMPLATE.replace("__PROJECT_DATA_PLACEHOLDER__", data_json)

    os.makedirs(os.path.dirname(os.path.abspath(output_html)), exist_ok=True)
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(final_html)

    print(f"[+] Successfully generated interactive workbench:")
    print(f"    -> {os.path.abspath(output_html)}")
    return output_html


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成拼贴封面交互式调优工作台 (Collage Cover Workbench)")
    parser.add_argument("input", help="输入的拼贴装配 HTML 文件路径")
    parser.add_argument("-o", "--output", help="输出的 workbench HTML 文件路径（可选）")

    args = parser.parse_args()
    generate_workbench(args.input, args.output)
