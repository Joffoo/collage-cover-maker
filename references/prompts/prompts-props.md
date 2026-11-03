# 超现实隐喻异质道具提示词模版

本模版用于生成 Toon Joosen 美学风格中与人物发生物理级交互的巨型荒诞日常物件。

> [!IMPORTANT]
> **去锚定与多样性保护铁律**：严禁提供任何固定的死道具清单（如火柴、打字机、放大镜），防止模型产生样例锚定（Mode Collapse）导致日后产出的封面千篇一律。所有道具必须遵循以下三步衍生机制由文稿动态推导。

---

## 道具隐喻衍生生成机制（Derivation Mechanism）

在制作封面道具前，模型与作者必须依次执行三步推导：

1. **提取核心矛盾或动作隐喻**：
   - 深入阅读文章，提炼出文章最核心的一个动词或矛盾（例如：争辩、解构、修剪、衡量、拼接、过滤、窥探、校准、破土）；
2. **映射微观现实实体**：
   - 将上述动词映射为一个现实中客观存在的微小物品或 1950 年代复古工业/生活物件（例如测量仪表、办公工具、厨房器皿、工器具、实验标本、机械发条、针织用具等任意未被限制的微观实体）；
3. **极端尺度倒置**：
   - 将该微观实体在画面中放大 10 到 50 倍，使其成为人物踩踏攀登的地基、斜倚休憩的椅背、对抗博弈的巨峰或遮阳遮雨的伞盖。

---

## 通用动态开放提示词配方

在调用生图模型时，使用下述带有开放占位符的配方，将推导出的专属微观实体代入 `[Gigantic surreal object derived from the article's core metaphor]`：

```text
Vintage 1950s lifestyle magazine scan cut-out illustration of a [Gigantic surreal object derived from the article's core metaphor], isolated on a pure flat solid white background (#FFFFFF). Minimalist Toon Joosen cut paper style, photogravure and halftone dot pattern texture, solid opaque flat color planes with subtle ink sedimentation, authentic scissor-cut contour with micro-roughness along edges, completely flat diffuse studio lighting, zero soft gradients, zero airbrush shading, no white borders, no die-cut outlines, no artificial outer glow, raw paper collage asset.
```

## 提示词代入与生成范例（仅供演示推导逻辑，非预设道具库）

- 若文章核心隐喻为“**修剪冗余**”：
  推导实体为园艺小剪刀或理线夹，代入为 `[an oversized vintage metal garden pruner with peeling green paint]`；
- 若文章核心隐喻为“**精确校准**”：
  推导实体为工业游标卡尺或老式千分尺，代入为 `[a colossal 1950s mechanical vernier caliper with engraved measurement notches]`；
- 若文章核心隐喻为“**思想记录**”：
  推导实体为折角木工铅笔或老式活字印模，代入为 `[a giant yellow carpenter pencil with sharp graphite tip and pressed wood grain]`。

## 关键参数与设计考量

- **长宽比忠实度**：细长道具（如标尺、探针、铅笔）必须保持真实物理比例（如 1:4 或 1:6），严禁在装配时被拉伸或压扁变形。
- **平版与铜版网点质感**：要求 `photogravure and halftone dot pattern texture` 与 `solid opaque flat color planes`，贴合 1950 年代真实出版物的凹版与丝网印刷质感。
- **纯白隔离底**：统一使用 `#FFFFFF` 纯平无影底色，确保下游 `cutout_asset.py` 能够紧贴真实轮廓无白边剔除。
