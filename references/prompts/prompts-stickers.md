# 现代写实摄影模切贴纸提示词规范

本模版用于在全图概念或垫图解构中，将人物或核心生物主体生成为具备**真实摄影微观质感、清爽模切白边与物理投影**的现代贴纸图元（纯白无缝背景独立孤立）。

> [!IMPORTANT]
> **绝对禁止纯色压平与网点劣化**：严禁将人物使用 K-Means 聚类为纯色矢量色块，严禁打上 1950 年代老报纸半色调网点（Halftone Dots）。必须保持真实高反差摄影质感（Authentic Photographic Texture），包含细腻发丝、眼神光与自然肤质。

---

## 提示词配方

```text
A modern high-contrast photographic cut-out portrait sticker of [主体描述，如：a contemplative young woman with sharp dark bangs and expressive eyes], authentic camera photograph texture, natural studio lighting, crisp skin micro-details, sharp individual hair strands, styled distinctly as a tangible die-cut paper sticker with a continuous 4px solid pure white die-cut border around the entire silhouette and a soft subtle contact drop shadow, isolated on a seamless pure solid white background (#FFFFFF). Contemporary editorial pop art aesthetic, raw photography paper sticker feel, zero halftone dots, zero vintage grain, zero solid vector flattening, no stickers overlapping.
```

## 关键参数与设计考量

- **写实微观摄影质感**：锁定 `authentic camera photograph texture` 与 `natural studio lighting`，避免 AI 假画质或扁平化；
- **4px 模切白边（Die-cut Border）**：声明 `continuous 4px solid pure white die-cut border around the entire silhouette`，让扩散模型直接生成实体贴纸冲压轮廓；
- **实图垫图零 AI 指纹替代路线**：当用户提供真人剧照或实拍素材时，跳过扩散模型，直接运行 Python 脚本基于真实 CMOS 像素与形态学膨胀生成纯物理模切贴纸（AI 指纹为 0.00%）。
