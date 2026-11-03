# 全图概念造魂与平铺解构提示词规范（Selman Hoşgör 现代混合拼贴体系）

本规范彻底淘汰老旧的“1930s 泛黄做旧报纸”、“半色调印刷网点”与“K-Means 暴力纯色聚类压平”，将生图模型源头 100% 锁定为 **Selman Hoşgör 现代混合媒介编辑拼贴（Contemporary Pop-Editorial Mixed-Media Collage）** 风格。

核心人物采用**“大画幅光学全景深 + Platon 雕塑窄过渡硬光 + Kicker 细轮廓光”**，确保既保留真实摄影的眼神光、发丝与骨骼立体感（非动漫平涂大色块），又在明暗交界处产生陡峭梯度，能够无损、极速转化为轻量高精的纯矢量 SVG 贴纸，彻底抹除 AI 指纹。

---

## 核心美学定义

- **艺术范式**：Selman Hoşgör 当代混合媒介画报编辑拼贴（Contemporary Pop-Editorial Mixed-Media）。
- **人物主体**：写实摄影肖像模切贴纸（8×10 大画幅解像力、Platon 雕塑硬光、窄阴影过渡带、眼神反光、Kicker 轮廓光），带 18px 冲压模切纯白边（Die-cut Sticker）。
- **即兴干预**：电光钴蓝（#0052FF）、荧光柠檬黄（#FFE600）与鲜品红（#FF2A85）的粗粝丙烯厚涂笔刷（Acrylic Smears / Impasto Strokes）。
- **手绘涂鸦**：黑色手绘马克笔涂鸦（思维螺旋线圈、漫画闪电、惊叹火花、手绘星号草图）。
- **排印文字**：Dymo 实体打标机黑胶带标签条（极粗纯白无衬线块面字，-2.5° 动态微倾角）+ 鲜红胶带副标。
- **底纸环境**：现代画廊展陈暖白卡纸（#F6F4EE），开阔、通透、呼吸充分。

---

## 步骤 1 全图概念造魂提示词模板

```markdown
A contemporary mixed-media editorial collage in the signature modern style of Selman Hoşgör:
- Style & Aesthetic: High-end contemporary editorial collage, dynamic pop-art mixed media. Zero vintage halftone dots, zero 1950s yellowed newspaper textures, crisp modern art gallery aesthetic.
- Central Character (Acutance & Lighting): A high-contrast editorial photographic portrait cutout of [主体描述，如：a thoughtful young Japanese woman with dark straight bangs and an intense contemplating gaze]. Shot on 8x10 large format with f/11 deep focus acutance, sculptural Platon-style directional lighting with narrow shadow falloff zones, razor-thin kicker rim light outlining the silhouette against backdrop, authentic skin micro-details, vivid pupil catchlights (NOT flat cartoon color blocks, NOT anime cel-shading), styled as a physical die-cut paper sticker with an 18px clean white border and subtle tactile drop shadow.
- Spontaneous Painterly Strokes: Bold, energetic sweeps of thick electric cobalt blue (#0052FF) and acid neon yellow (#FFE600) acrylic gouache overlapping dynamically behind and around the head, featuring visible impasto paint bristle textures.
- Whimsical Marker Doodles: Hand-drawn black ink marker doodles floating playfully around the temples (comic lightning sparks, thinking spiral swirls, abstract exclamation scribbles), expressing intense internal dialogue.
- Typography Component: Bold typography integrated as a physical peel-off label tape strip reading "[文章核心标题]", stark white heavy sans-serif block lettering stamped on an electric red or black cardstock strip, placed dynamically at a subtle -2.5 degree tilt across the lower chest.
- Surreal Prop: An oversized surreal [微观道具，如：giant brass quiz buzzer / colossal yellow carpenter pencil], 30x scale discrepancy, crisp graphic edges, overlapping dynamically as a physical cutout asset.
- Canvas & Palette: Clean contemporary off-white art cardstock ground (#F6F4EE). High-saturation pop contrast: cobalt blue, acid lemon yellow, vivid lacquer red, deep charcoal black, and crisp optic white.
- Composition: Tangible layered physical paper collage, crisp clean edges, spontaneous creative energy, uncluttered modern negative space. --ar 1:1
```

---

## 步骤 2 垫图解构平铺散件提示词模板

```markdown
Based on the reference image:
Deconstruct this contemporary Selman Hoşgör style collage into an exploded flat knolling layout / spritesheet of isolated tangible papercut and sticker elements, neatly arranged on a seamless pure solid white background:
1. The character portrait cutout, styled distinctly as a physical die-cut photo sticker with a clean white border around the entire silhouette, preserving authentic camera photographic realism, sculptural lighting contrast, facial tones, and hair details (DO NOT flatten into cartoon polygons or muddy gradients);
2. Isolated dynamic acrylic paint smears and gouache brush strokes (cobalt blue, neon yellow, and vermilion pink);
3. Whimsical hand-drawn black marker doodle stickers (comic lightning bolts, thought loops, playful star scribbles);
4. The physical label-maker tape sticker strip with bold cutout title typography;
5. The oversized surreal prop cutout with clean scissor edges.
Isolate each element with ample clear white margins between them, crisp sharp contours, ready for automated segmentation. Seamless solid pure white background, zero overlap between items.
```
