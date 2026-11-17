# 提示词

占位符 `[...]` 由 Phase 1 的方案填入。画面里不放任何文字。

## 效果图（mockup）

有真实素材时，把它作为参考图一并传入，让生成结果与真实主体的光线、色调融合。

```text
A contemporary mixed-media editorial collage in the style of Selman Hoşgör, on a clean off-white art-cardstock ground (#F7F5F0).
Subject: [主体描述。真实素材：保持参考图中的人物/物件原样，不重绘五官]. Photographic realism, sculptural directional light, die-cut paper sticker with a thick clean white border.
Behind and around the subject: bold sweeps of thick acrylic paint in cobalt blue (#0052FF), acid yellow (#FFE600) and hot pink (#FF2A85) with visible bristle texture.
Hand-drawn black marker doodles near the temples: lightning bolt, thinking spiral, sparks, asterisks.
Prop: an oversized [隐喻道具], 30x scale, crisp graphic edges, overlapping the subject.
A blank black label-tape strip tilted -2.5° across the lower chest.
Layered physical paper collage, uncluttered negative space, no text, no letters, no logos.
```

## 元件图（sprite sheet）

把效果图作为参考图。主体与摄影质感道具是 real，元件图只拆平涂的 gen 元件；平涂是为了让后续矢量化几乎无损。

```text
Based on the reference image, deconstruct the collage into an exploded flat layout of isolated flat vector-style elements on a seamless pure white background (#FFFFFF), at least 80px of empty white between elements, nothing touching the image edge:
1. each acrylic paint smear as its own element, one per color;
2. each black marker doodle as its own element;
3. [仅当道具是扁平图形时] the oversized [隐喻道具].
Flat solid colors, limited palette, crisp edges, no gradients, no texture, no photographic detail. Keep every element's shape, color and proportion identical to the reference. No shadows on the white ground, no text.
```

## 影棚白底实物道具（real-fallback）

当公版库（`openverse` / `commons`）搜不到干净、高辨识度的现代实物原片时，用本提示词生成孤立的影棚摄影实物，随后走 `make_part.py real` 抠图并烘焙 14px 纯白模切边。严禁去博物馆库硬凑古董怪件。

```text
A single isolated studio product photograph on a seamless pure white background (#FFFFFF): [现代常见实物的精确描述，如 a vintage analog needle pressure gauge with brushed steel bezel and bright red needle]. Hard directional studio lighting, sculptural contrast, photorealistic, crisp edges, centered with generous white margin around it, no drop shadow on the white ground, no extra objects, no brand logo or watermark.
```
