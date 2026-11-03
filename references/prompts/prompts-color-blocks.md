# 物理剪纸色块提示词模版

本模版用于生成具有手工裁切微颤、物理纸张厚度与纤维毛边的实体几何色块资产（替代纯代码生成的 `div` 拱门与圆盘）。

## 陶土红手工剪纸拱门

```text
Handmade scissor-cut terracotta red (#E24A32) thick cardstock arch shape, isolated on pure solid white background (#FFFFFF). Microscopic scissor cutting stutter, organic paper edge roughness, visible cardstock edge thickness with subtle specular highlight, authentic tactile heavy paper texture, matte unlit flat finish, crisp polygon silhouette, zero gradient shading, clean cutout element for physical collage art.
```

## 板岩青手工剪裁圆盘

```text
Hand-cut slate teal (#2D485E) heavy paper disc cutout, isolated on a pure flat solid white background (#FFFFFF). Hand-trimmed circular silhouette with subtle human micro-tremor and fibrous burr along the contour, visible paper sheet edge thickness, rich cellulose texture, flat screen-printed color fill, no soft gradient, razor-sharp edge contrast for physical collage asset.
```

## 几何衬底与多边形底托

```text
Scissor-cut geometric paper strip pedestal, deep navy blue (#233748) textured heavy cardstock, isolated on pure white background (#FFFFFF). Crisp hand-cut bevels, subtle paper fiber fraying at the cut edge, flat unshaded surface, tactile craft paper thickness, minimalist constructivist collage backing block.
```

## 关键参数与设计考量

- **物理裁切顿挫**：声明 `microscopic scissor cutting stutter` 与 `fibrous burr along the contour`，粉碎矢量贝塞尔曲线的机械平滑感。
- **纸张实体厚度**：声明 `visible cardstock edge thickness`，使纸片在下游光影计算中展现真实的物理边缘凸起。
- **白底隔离标准**：严格锁定 `isolated on pure solid white background (#FFFFFF)`，便于 `cutout_asset.py` 执行零损耗透明通道提取。
