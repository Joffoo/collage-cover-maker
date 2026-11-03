# 现代展陈卡纸与零 AI 指纹底纸规范

本模版彻底废弃调用生图模型生成 1930s 泛黄做旧牛皮纸的做法（该做法是导致背景被检测出 AI 指纹的根源）。

全面转向 **Selman Hoşgör 当代展陈暖白卡纸（Gallery Ivory Cardstock）**，通过浏览器原生 CSS/SVG 滤镜或经过版权核验的真实物理原纸超高清扫描件实现，确保**背景层 100% 零 AI 指纹**。

---

## 方案 A：纯 CSS / SVG 现代展陈暖白卡纸（推荐首选，0% AI 指纹）

无需任何外部图片资源请求，由浏览器渲染引擎直接光栅化生成，彻底杜绝任何潜空间伪影：

```css
body {
    margin: 0;
    padding: 0;
    background-color: #F7F5F0; /* 现代画廊高阶展陈暖白卡纸 */
    /* 采用原生 SVG 细微湍流生成纯物理漫反射触感，不依赖外部位图文件 */
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3CfeColorMatrix type='matrix' values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.035 0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E");
}
```

---

## 方案 B：公有领域（CC0 / Public Domain）真实纸张高清扫描

若项目必须采用外部大图承托，必须且只能选用经过版权验证的真实物理纸张扫描原片（真实光学光电信号，AI 指纹为 0%）：

- **Rawpixel Public Domain Collection**：大英图书馆 / 纽约公共图书馆（NYPL）数字化归档的 **Blank Fine Art Paper / Cotton Watercolor Paper**（CC0 协议，600 DPI，无任何生成伪影）；
- **Wikimedia Commons**：`Category:Blank paper textures` 原生胶片扫描件；
- **Unsplash**：摄影师在真实影棚漫反射布光下拍摄的空白美术卡纸。
