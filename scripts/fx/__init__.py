"""计算视觉与几何拓扑解构特效工具库 (Collage Cover Maker FX Toolkit)

提供 4 款面向 Selman Hoşgör 与前卫波普拼贴的纯算法解构算子：
1. voronoi_fracture: 加权质心 Voronoi 晶体热应力碎裂
2. moire_topology: 莫尔拓扑干涉光栅
3. shredder_slice: 物理重磅卡纸撕裂切片
4. kawamura_shred: 河村康辅碎纸机垂直条纹重组（Kosuke Kawamura Vertical Shredder Strips）

所有算子绝对保护 Alpha 透明通道（RGBA 贴纸输入输出，或纯透明底矢量 SVG）。
"""
from .voronoi_fracture import voronoi_fracture
from .moire_topology import moire_topology
from .shredder_slice import shredder_slice
from .kawamura import kawamura_shred

__all__ = [
    "voronoi_fracture",
    "moire_topology",
    "shredder_slice",
    "kawamura_shred",
]
