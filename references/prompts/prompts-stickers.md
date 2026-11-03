# 现代写实摄影纯矢量模切贴纸提示词规范

本模版用于在全图概念造魂或散件提取中，生成具备**大画幅肖像摄影质感、极高微反差、利落模切白边，且转 SVG 时绝对清晰无泥斑**的贴纸图元。

> [!IMPORTANT]
> **拒绝两极化极端**：
> 1. 严禁倒退为卡通、动漫赛璐珞平涂（Cel-shading）或极简波普大纯色块（丢失真实摄影神韵）；
> 2. 严禁使用柔和漫射光、大光圈虚化或平缓过渡（会导致转 SVG 时产生波纹状等高线泥斑）。
> **核心破局点**：通过 **8×10 大画幅摄影光学全景深 + Platon 雕塑感窄过渡硬光 + Kicker 细反差轮廓光**，从物理光影源头收窄明暗交界带，使后端矢量化算法能够沿着长轮廓线顺畅切割，既保留 100% 真实摄影的神态、眼神光与立体感，又转化为 100% 纯矢量代码，彻底消灭 AI 指纹。

---

## 提示词标准配方

```text
A striking contemporary editorial photographic portrait of [主体描述，如：a thoughtful young Japanese woman with dark straight bangs and an intense, intensely focused contemplating gaze]:

- Optical Rig & Focus: Shot on 8x10 large format camera with ultra-sharp high-resolving lens, deep focus throughout at f/11 aperture, zero lens blur, zero depth-of-field bokeh, tack-sharp edge acutance across the entire silhouette.
- Sculptural Lighting Architecture: High-contrast editorial directional lighting in the signature style of Platon and Richard Avedon. Gridded hard key light with very narrow shadow falloff zones (crisp sculptural definition without muddy midtone gradations), paired with a razor-thin intense kicker rim light precisely outlining the hair, ears, and shoulders against the backdrop.
- Photographic Fidelity & Tactile Micro-Details: Authentic camera photographic texture, crisp skin micro-details, vibrant specular catchlights inside the pupils, natural dark straight bangs, distinct sharp hair strand masses (NOT flat cartoon color blocks, NOT anime cel-shading, NOT vector posterization).
- Acutance & Edge Definition: Extreme edge contrast between subject and background, zero motion blur, completely clear boundary separation ready for high-fidelity vector contour extraction.
- Wardrobe: Dark modern tailored jacket / blazer.
- Background & Placement: Isolated against a pure solid seamless white background (#FFFFFF).
- Aspect ratio: 1:1 square.

Negative Prompt:
flat vector art, cel-shaded, cartoon, anime, 1950s halftone dots, airbrush gradients, soft diffused light, muddy midtones, blurry bokeh, shallow depth of field, haze, motion blur, smudged contours, color block posterization, clip art, low micro-contrast, feathered borders.
```

---

## 纯矢量化与模切白边装配参数（Post-Processing）

1. **多阶聚类平坦化**：
   ```bash
   python .agents/skills/collage-cover-maker/scripts/cutout_asset.py "<source>.jpg" "sprites/<subject>_cutout.png" --vectorize --k-clusters 24 --export-svg "sprites/<subject>_vector.svg"
   ```
2. **冲压模切纯白边合成**：
   在 SVG 外层路径上施加 16~20px 纯白描边（`stroke="#FFFFFF" stroke-width="18" stroke-linejoin="round"`），内置柔和微距投影滤镜；
3. **零指纹断言**：
   转化后的素材 100% 为 XML 纯矢量几何代码，无任何扩散模型位图像素点阵，**AI 生成概率判定为 0.00%**。
