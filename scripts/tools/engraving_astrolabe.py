import math
import os
import sys
import argparse

def polar_to_cartesian(cx, cy, r, angle_deg):
    rad = math.radians(angle_deg)
    return cx + r * math.cos(rad), cy + r * math.sin(rad)

def generate_astrolabe_svg(
    output_path="_inbox/engraving_astrolabe.svg",
    size=1000,
    ink_color="#1A1715",
    gold_color="#B88E3E",
    blue_line="#1D3557",
    paper_tone="#FAF5EB",
    transparent=True
):
    """
    古典蚀刻星盘与铜版图腾 SVG 生成器（Celestial Astrolabe & Copperplate Engraving Totem Generator）：
    1. 同心精密刻度环（360度方位微刻度）；
    2. 十二星座黄道带扇区与古典罗马数字；
    3. 铜版版画交叉排线微刻度（Copperplate Hatched Scales）；
    4. 星位指针叶片（Astrolabe Rete Star Pointers：北极星、天狼星、织女星等）；
    5. 开普勒椭圆黄道倾角线与分至天球十字轴；
    6. 太阳放射光芒射线与四方方位印章。
    """
    scale = size / 1000.0
    cx = size / 2.0
    cy = size / 2.0

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">']
    svg.append('<defs>')
    svg.append(f'''
        <style>
            .ink {{ stroke: {ink_color}; fill: none; stroke-linecap: round; stroke-linejoin: round; }}
            .gold {{ stroke: {gold_color}; fill: none; }}
            .blue-line {{ stroke: {blue_line}; fill: none; stroke-opacity: 0.75; }}
            .text-ink {{ font-family: "Times New Roman", "Baskerville", "Songti SC", serif; fill: {ink_color}; text-anchor: middle; dominant-baseline: central; }}
            .text-gold {{ font-family: "Times New Roman", serif; fill: {gold_color}; font-weight: bold; text-anchor: middle; dominant-baseline: central; }}
        </style>
    ''')
    svg.append('</defs>')

    if not transparent:
        svg.append(f'<rect width="{size}" height="{size}" fill="{paper_tone}" />')

    # 1. 经典同心刻度环
    base_radii = [488, 484, 460, 456, 420, 416, 370, 366, 310, 260, 210, 175]
    for r_base in base_radii:
        r = r_base * scale
        stroke_w = 2.0 * scale if r_base in [488, 456, 416, 366] else 0.8 * scale
        color_cls = "gold" if r_base in [456, 366, 260] else "ink"
        svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" class="{color_cls}" stroke-width="{stroke_w:.2f}" />')

    # 2. 360 度圆周微刻度与方位度数（r=460 到 r=484）
    for deg in range(360):
        if deg % 10 == 0:
            r_in = 460 * scale
            r_out = 484 * scale
            x1, y1 = polar_to_cartesian(cx, cy, r_in, deg)
            x2, y2 = polar_to_cartesian(cx, cy, r_out, deg)
            svg.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="ink" stroke-width="{1.6 * scale:.2f}" />')
            if deg % 30 == 0:
                tx, ty = polar_to_cartesian(cx, cy, 497 * scale, deg)
                svg.append(f'<text x="{tx:.1f}" y="{ty:.1f}" class="text-ink" font-size="{10 * scale:.1f}">{deg}°</text>')
        elif deg % 5 == 0:
            r_in = 466 * scale
            r_out = 484 * scale
            x1, y1 = polar_to_cartesian(cx, cy, r_in, deg)
            x2, y2 = polar_to_cartesian(cx, cy, r_out, deg)
            svg.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="ink" stroke-width="{1.0 * scale:.2f}" />')
        else:
            r_in = 472 * scale
            r_out = 484 * scale
            x1, y1 = polar_to_cartesian(cx, cy, r_in, deg)
            x2, y2 = polar_to_cartesian(cx, cy, r_out, deg)
            svg.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="ink" stroke-width="{0.6 * scale:.2f}" stroke-opacity="0.8" />')

    # 3. 十二星座黄道带（r=420 到 r=456）
    zodiac_signs = [
        ("♈", "ARIES", "I"), ("♉", "TAURUS", "II"), ("♊", "GEMINI", "III"),
        ("♋", "CANCER", "IV"), ("♌", "LEO", "V"), ("♍", "VIRGO", "VI"),
        ("♎", "LIBRA", "VII"), ("♏", "SCORPIO", "VIII"), ("♐", "SAGITTARIUS", "IX"),
        ("♑", "CAPRICORN", "X"), ("♒", "AQUARIUS", "XI"), ("♓", "PISCES", "XII")
    ]
    for i, (glyph, name, roman) in enumerate(zodiac_signs):
        angle = i * 30
        x1, y1 = polar_to_cartesian(cx, cy, 420 * scale, angle)
        x2, y2 = polar_to_cartesian(cx, cy, 456 * scale, angle)
        svg.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="gold" stroke-width="{1.8 * scale:.2f}" />')

        mid_angle = angle + 15
        gx, gy = polar_to_cartesian(cx, cy, 444 * scale, mid_angle)
        svg.append(f'<text x="{gx:.1f}" y="{gy:.1f}" class="text-gold" font-size="{16 * scale:.1f}">{glyph}</text>')
        rx, ry = polar_to_cartesian(cx, cy, 428 * scale, mid_angle)
        svg.append(f'<text x="{rx:.1f}" y="{ry:.1f}" class="text-ink" font-size="{9 * scale:.1f}" font-style="italic">{roman}</text>')

    # 4. 铜版交叉倾斜排线刻度（r=370 到 r=416）
    for deg in range(0, 360, 2):
        r_start = 370 * scale
        r_end = 416 * scale
        x1, y1 = polar_to_cartesian(cx, cy, r_start, deg)
        x2, y2 = polar_to_cartesian(cx, cy, r_end, deg + 4)
        svg.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="ink" stroke-width="{0.5 * scale:.2f}" stroke-opacity="0.4" />')

    # 5. 星盘星位指针（Astrolabe Rete Star Pointers）
    star_pointers = [
        (25, "POLARIS", 355), (65, "ALDEBARAN", 345), (110, "SIRIUS", 360),
        (155, "REGULUS", 340), (200, "SPICA", 350), (245, "ARCTURUS", 360),
        (290, "VEGA", 355), (335, "ALTAIR", 345)
    ]
    for deg, star_name, r_tip_base in star_pointers:
        r_tip = r_tip_base * scale
        r_base = 310 * scale
        r_ctrl = 335 * scale
        x_base1, y_base1 = polar_to_cartesian(cx, cy, r_base, deg - 6)
        x_base2, y_base2 = polar_to_cartesian(cx, cy, r_base, deg + 6)
        x_tip, y_tip = polar_to_cartesian(cx, cy, r_tip, deg)
        x_c1, y_c1 = polar_to_cartesian(cx, cy, r_ctrl, deg - 2)
        x_c2, y_c2 = polar_to_cartesian(cx, cy, r_ctrl, deg + 2)

        path_d = f"M {x_base1:.1f} {y_base1:.1f} Q {x_c1:.1f} {y_c1:.1f} {x_tip:.1f} {y_tip:.1f} Q {x_c2:.1f} {y_c2:.1f} {x_base2:.1f} {y_base2:.1f} Z"
        svg.append(f'<path d="{path_d}" fill="{paper_tone}" stroke="{ink_color}" stroke-width="{1.2 * scale:.2f}" />')
        svg.append(f'<circle cx="{x_tip:.1f}" cy="{y_tip:.1f}" r="{3 * scale:.1f}" fill="{gold_color}" stroke="{ink_color}" stroke-width="{1 * scale:.2f}" />')
        lx, ly = polar_to_cartesian(cx, cy, (r_tip_base - 18) * scale, deg)
        svg.append(f'<text x="{lx:.1f}" y="{ly:.1f}" class="text-ink" font-size="{8 * scale:.1f}" font-weight="bold">{star_name}</text>')

    # 6. 开普勒椭圆黄道倾角线
    rx1, ry1 = 360 * scale, 240 * scale
    rx2, ry2 = 320 * scale, 180 * scale
    rx3, ry3 = 280 * scale, 140 * scale
    svg.append(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx1:.1f}" ry="{ry1:.1f}" transform="rotate(-23.5 {cx:.1f} {cy:.1f})" class="blue-line" stroke-width="{1.8 * scale:.2f}" stroke-dasharray="8,4" />')
    svg.append(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx2:.1f}" ry="{ry2:.1f}" transform="rotate(35 {cx:.1f} {cy:.1f})" class="gold" stroke-width="{1.2 * scale:.2f}" stroke-opacity="0.8" />')
    svg.append(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx3:.1f}" ry="{ry3:.1f}" transform="rotate(-55 {cx:.1f} {cy:.1f})" class="ink" stroke-width="{0.8 * scale:.2f}" stroke-dasharray="3,3" />')

    # 7. 分至十字轴
    r_axis = 488 * scale
    svg.append(f'<line x1="{cx - r_axis:.1f}" y1="{cy:.1f}" x2="{cx + r_axis:.1f}" y2="{cy:.1f}" class="ink" stroke-width="{1.2 * scale:.2f}" stroke-dasharray="12,4,2,4" />')
    svg.append(f'<line x1="{cx:.1f}" y1="{cy - r_axis:.1f}" x2="{cx:.1f}" y2="{cy + r_axis:.1f}" class="ink" stroke-width="{1.2 * scale:.2f}" stroke-dasharray="12,4,2,4" />')

    # 8. 太阳放射光芒射线（r=175 到 r=280）
    for deg in range(0, 360, 5):
        r_out_base = 280 if deg % 20 == 0 else (250 if deg % 10 == 0 else 220)
        r_in = 175 * scale
        r_out = r_out_base * scale
        x1, y1 = polar_to_cartesian(cx, cy, r_in, deg)
        x2, y2 = polar_to_cartesian(cx, cy, r_out, deg)
        sw = (1.4 if deg % 20 == 0 else 0.7) * scale
        svg.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="gold" stroke-width="{sw:.2f}" stroke-opacity="0.75" />')

    # 9. 东西南北方位标
    for deg, label in [(0, "OR"), (90, "ME"), (180, "OC"), (270, "SEP")]:
        x, y = polar_to_cartesian(cx, cy, 475 * scale, deg)
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{8 * scale:.1f}" fill="{paper_tone}" stroke="{gold_color}" stroke-width="{1.5 * scale:.2f}" />')
        svg.append(f'<text x="{x:.1f}" y="{y:.1f}" class="text-gold" font-size="{8 * scale:.1f}">{label}</text>')

    svg.append('</svg>\n')
    svg_content = "\n".join(svg)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Celestial Astrolabe SVG Generated: {output_path} (Size={size}x{size})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Celestial Astrolabe & Copperplate Engraving Totem SVG Generator")
    parser.add_argument("--output", "-o", default="_inbox/engraving_astrolabe.svg", help="Output SVG path (default: _inbox/engraving_astrolabe.svg)")
    parser.add_argument("--size", "-s", type=int, default=1000, help="Canvas size width and height (default: 1000)")
    parser.add_argument("--ink-color", default="#1A1715", help="Ink line color (default: #1A1715)")
    parser.add_argument("--gold-color", default="#B88E3E", help="Gold line color (default: #B88E3E)")
    parser.add_argument("--blue-line", default="#1D3557", help="Keplerian orbit ellipse line color (default: #1D3557)")
    parser.add_argument("--paper-tone", default="#FAF5EB", help="Paper tone color (default: #FAF5EB)")
    parser.add_argument("--no-transparent", dest="transparent", action="store_false", help="Render solid paper background instead of transparent")
    parser.set_defaults(transparent=True)

    args = parser.parse_args()
    generate_astrolabe_svg(
        output_path=args.output,
        size=args.size,
        ink_color=args.ink_color,
        gold_color=args.gold_color,
        blue_line=args.blue_line,
        paper_tone=args.paper_tone,
        transparent=args.transparent
    )