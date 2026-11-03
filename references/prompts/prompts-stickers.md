# 复古剪纸实体素材提示词模版

本模版用于将用户提供的真人剧照、实拍照片或概念主体，转置为带有历史质感的 1950-1970 年代复古生活杂志剪纸素材（纯白背景单体孤立，严禁贴纸白边）。

## 真实纸张与物理剪裁原则

发给生图模型的提示词中，**必须前置声明真实印刷与物理剪裁的视觉语言规范**，让扩散模型直接生成具备实体拼贴质感的位图：

1. **复古生活杂志扫描**：声明源自 1950-1970 年代真实出版物印刷质感（1950s-1970s vintage lifestyle magazine scan），带有历史印刷品的轻微褪色与油墨沉淀；
2. **铜版照相凹版与半色调网点**：注入铜版照相凹版（Photogravure）与木刻丝网网点（Halftone dot pattern）肌理，呈现真实的网点颗粒感，杜绝数码矢量的塑料平滑感；
3. **剪刀物理顿挫**：要求逼真的剪刀物理裁剪边缘（Authentic scissor cut-out contour），呈现手工剪裁特有的微小顿挫与纸张纤维切口，边缘自然干脆；
4. **单体纯白孤立**：输出主体必须在纯白平坦背景上孤立呈现（Isolated on pure solid white background），便于后续精准无损抠图；
5. **严禁贴纸白边与外发光**：彻底禁用模切白边、贴纸边缘与人工光晕（No white outline, no die-cut border, no outer glow, no sticker effect），主体边缘必须紧贴真实轮廓。

## 提示词配方

```text
A vintage cut-out figure from a 1950s-1970s lifestyle magazine scan, photogravure and halftone dot pattern texture, authentic hand-cut scissor contour with subtle edge fiber imperfections, isolated on a seamless pure solid white background. High contrast retro print aesthetic, raw paper cut-out feel, no white borders, no die-cut outlines, no artificial outer glow, no stickers.
```

## 关键机制与合规考量

- **粉碎数码平庸与复古质感**：现代二次元矢量或平涂贴纸具有强烈的 AI 数码味，而 1950-1970 年代的凹版网点与胶印颗粒赋予拼贴作品真实的物理重量感与艺术典藏价值。
- **纯净无字红线**：提示词中严禁出现任何添加短句或英文说明的诉求，锁定纯粹的人物或物体主体。
- **真实边缘紧贴穿插**：剥离人工白边后，主体轮廓可以与背景星空、地质字条或超现实道具产生无缝物理咬合与空间穿插，实现纯正的 Joe Webb / Toon Joosen 拼贴语言。
