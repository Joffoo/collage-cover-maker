# Joe Webb 深空圆窗与星系裂隙提示词模版

本模版用于生成具有物理纸张切口轮廓、显露哈勃真实星尘与星系深空的宇宙负空间裂隙（用于 Joe Webb 风格穿透）。

## 手工剪裁厚纸星空圆窗

```text
Hand-cut circular aperture on dark charcoal textured thick cardboard revealing an authentic Hubble deep space nebula inside, aesthetic inspired by Joe Webb. Scissor-cut circular opening with authentic micro-roughness along the inner cardboard rim, visible raw paper core bevel at the cut line, rich Hubble nebula dust clouds featuring glowing violet, magenta ionization ridges, deep indigo void and dense crystalline stellar clusters, isolated on pure solid white background (#FFFFFF) around the outer cardboard boundary, flat vintage paper-cut collage asset.
```

## 天体裂隙与破损纸张星河

```text
Torn paper tear slit across warm 1930s linen kraft cardstock revealing a glowing cosmic Milky Way and authentic Hubble stardust beneath, Joe Webb existential surrealism. Rough fibrous frayed paper tear edges with authentic cellulose fiber fuzz, deep indigo and cyan space dust shining from the rift, pristine #FFFFFF solid white background surrounding the paper specimen, tactile collage layer.
```

## 负空间服饰穿透提示词（配合 cutout_asset --hollow-apparel）

```text
A 1950s vintage monochrome photograph of an elegant lady wearing a pure white evening gown, standing in contemplative profile pose, isolated on pure solid white background, high contrast halftone dot texture, authentic 1950s lifestyle magazine scan, scissor-cut contour. (The white gown will be hollowed out into transparent negative space by cutout_asset.py to let background Hubble nebula shine through).
```

## 关键参数与设计考量

- **双层物理边缘**：外缘为纯白隔离底（便于抠图），内缘为带有白色纸芯斜角（`visible raw paper core bevel`）的手工裁切轮廓，呈现由实心纸面窥见宇宙深空的物理穿透感。
- **色彩饱和与对撞**：星云紫红、靛蓝与暖调米黄纸底形成强烈冷暖对撞，增强视觉冲击力。
- **本地程序化替代**：推荐优先使用 `generate_physical_papercuts.py` 中的 `generate_papercut_portal_galaxy` 本地生成，自动集成哈勃星云算法与纸张坡口光影。
