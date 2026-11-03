# 复古底纸生成提示词模版

本模版用于生成 1930 年代真实复古米黄亚麻牛皮纸基底（替代 CSS 纯色代码背景），承载所有拼贴纸片层的物理受光面。

## 提示词配方

```text
Flat top-down photograph of authentic 1930s vintage linen kraft paper, warm creamy beige and aged butcher paper tone (#F5EFEB), raw tactile cotton and linen paper fibers, microscopic organic cellulose pulp grain, subtle natural horizontal folding creases, faint tea water oxidation rings, delicate aged vignette along edges, completely flat surface, zero tilt, diffuse museum lighting, ultra-high resolution texture background, clean vintage material canvas, no text, no illustrations, pure blank textured craft paper.
```

## 关键参数与设计考量

- **亚麻与牛皮纸纤维触感**：强调 `raw tactile cotton and linen paper fibers` 与 `microscopic organic cellulose pulp grain`，在超清渲染中呈现真实的植物纤维交织网络。
- **岁月痕迹控制**：限定为微弱的自然折痕（`subtle natural horizontal folding creases`）与边缘氧化泛黄（`delicate aged vignette`），避免过度脏污抢走上层主体视线。
- **漫反射无影受光**：采用博物馆级柔和漫反射光照（`diffuse museum lighting`），确保整张纸基明度均匀平坦，便于作为底层承重托板。
- **本地程序化替代**：推荐优先使用 `generate_physical_papercuts.py` 中的 `generate_vintage_paper_canvas` 本地生成，无需消耗模型额度即可获得 100% 物理真实底纸。
