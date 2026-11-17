---
name: collage-cover-maker
description: 拼贴封面（Selman Hoşgör 风格）：由文章加用户素材出发，经效果图、元件图、分流处理（真实素材抠图、AIGC 元件 SVG 化），在 HTML 里装配并交给用户拖拽微调，产出公众号 2.35:1/1:1、16:9、小红书 3:4。用户要"拼贴封面""剪纸拼贴""波普拼贴""Selman Hoşgör 风格"，或要复修已有拼贴封面时使用。
---

# 拼贴封面

**材料分流**是这条流水线的脊柱：每个元件只有两种出身，处理方式因此固定。摄影质感的元件（人像、实物）恒为 real，gen 只负责平涂图形。

| 出身 | 例子 | 来源 | 处理 | 产物 |
| --- | --- | --- | --- | --- |
| **real** | 主体人像、实物道具 | 用户素材；没有就由 Agent 取 CC0/公有领域图 | 从原片抠图（保住相机像素） | RGBA PNG |
| **gen** | 丙烯厚涂、马克笔涂鸦、扁平道具 | 生图 | 矢量化 | SVG |

风格、画幅、安全区见 [`references/style.md`](references/style.md)；提示词见 [`references/prompts.md`](references/prompts.md)。

## 工作区

所有产物放 `00-Inbox/<slug>_assets/`（下称项目目录），在其中运行脚本：

```text
mockup.png   效果图          parts/        元件（_index.png 是认领图）
sheet.png    元件图          layers.json   装配的唯一真相源
cover.html   由 layers.json 生成，编辑器与出图共用
cover_*.png  成品封面
```

脚本在 `.agents/skills/collage-cover-maker/scripts/`，`make_part.py check` 报告缺哪些依赖（`rembg`、`vtracer`、`playwright`、`scipy`、`shapely`、`skimage`），缺什么装什么。

## 步骤

### 1. 素材分流与方案

读文章，提炼核心动词与矛盾，按 `style.md` 的「道具推导」得到隐喻道具与 4~8 字主标题。

**取材**：主体与摄影质感道具，用户没给素材的由 Agent 去公版库取。
- **人像选角（Editorial Casting）**：**不要按文章字面去搜历史名人**（读者不认识反而突兀），而是按**戏剧神态、手势与高反差影棚光影**选角（如 `George Hurrell portrait`、`MGM 1930s studio portrait`、`dramatic studio portrait`）。用 `--sheet raw/_candidates.png` 生成候选缩略拼图与反差评分（`ct`），亲眼挑出最具张力与吸引力的一张：

```bash
python <scripts>/fetch_public.py search commons "George Hurrell portrait" --sheet raw/_candidates.png
python <scripts>/fetch_public.py search openverse "<现代道具英文关键词>" --sheet raw/_prop_candidates.png
python <scripts>/fetch_public.py get <url> raw/subject.jpg --title <标题> --license <许可> --page <来源页>
```

只有许可为 CC0 或公有领域的才下载；`get` 会计算清晰度与反差并写入 `raw/sources.json`。检索无果时向用户要素材，或按第 2 步的「影棚白底实物道具」兜底生成。

完成标准是方案卡里每个元件都有出身，且每个 real 元件都有原片（用户给的，或已登记 `sources.json` 的）。向用户展示方案卡与取到的候选原图并**等确认**：

- 主标题与副标题
- 道具推导（动词 → 实物）
- 元件清单：每项标 real（附原片与出处）/ gen
- slug

### 2. 道具与元件获取（两条标准路径）

根据道具属性与生成需求，严格划分为两条工业化路径：

- **路径 A · AI 生图流（双垫图标准工作流 · 超现实特异化道具）**：
  仅当需要现实中不存在的超现实波普道具时触发，执行双垫图标准工作流：
  1. **垫人像出整图**：将真实选角原片（`raw/subject.jpg`）作为参考图垫给生图模型，输入 `prompts.md` 的创意效果图提示词，生成具备全局俯仰透视与空间动势的艺术草图 `mockup.png`；
  2. **垫整图出白底零件**：将 `mockup.png` 垫图输入生图工具，提示词明确声明『**排除人物，仅提取周围平涂道具与涂鸦**』，生成纯白底平铺母版 `sheet.png`。
- **路径 B · 零生图流（纯公版实拍与算法合成 · 零生图消耗）**：
  当道具在现实中存在实体且公版库能找到**现代高辨识度干净实拍**时触发：
  - **公版实体道具**：优先用 `fetch_public.py search openverse "<英文关键词>"`（已默认锁定 `category=photograph`，可命中 Rawpixel/StockSnap/Flickr 现代 CC0 实拍）或 `commons "<英文关键词> -18th -19th -engraving -drawing -patent"` 检索现代实拍摄影（**严禁用 CMA/AIC 的冷门古董异形件充当现代道具**，且必须满足 `style.md` 的「1 秒辨识度」与「镂空避撞」门禁）；
  - **影棚白底生图兜底（real-fallback，仅最后手段）**：若 Openverse/Commons 确实搜不到干净现代实拍，优先向用户要图；确需兜底生图时按 `prompts.md`「影棚白底实物道具」生成 `raw/prop.png`，走 `make_part.py real` 后再叠加 `fx halftone` 抹除 AI 平滑指纹；
  - **算法无模型合成**：运行 `python <scripts>/make_part.py synth parts --seed <随机整数>`，现场合成高精细干刷丙烯与马克笔涂鸦，零配额消耗，彻底杜绝 AI 指纹。

完成标准是得到纯白底零件图 `sheet.png`（路径 A）或公版原片/算法合成文件（路径 B）。

### 3. 切件与矢量化

运行 `python <scripts>/make_part.py split sheet.png parts` 切出独立散件并由 `_index.png` 认领。后续通过 `make_part.py gen` 强制矢量化为纯净 SVG。严禁在技能库囤积静态死图，严禁手写简笔画充数。

### 4. 分流处理

**real**：对原片抠图并烘模切白边。默认使用已就绪的 `birefnet-general-lite`（人像与物件通吃）；也可指定 `--model birefnet-portrait`（模型文件放 `~/.u2net/`，缺失时 rembg 会联网下载）。

```bash
python <scripts>/make_part.py real raw/subject.jpg parts/subject.png
```

**gen**：对元件 PNG 矢量化。丙烯、涂鸦等平涂元件加 `--border 0`，需要模切白边的扁平道具保留默认。

```bash
python <scripts>/make_part.py gen parts/p03.png parts/prop.svg
```

**fx**（前卫视觉解构算子）：当需要打破传统贴纸的单一呆板感，进行**主体解构**、**视窗穿透**与**质感对撞**时，使用纯科学计算栈实现的 4 款前卫算子（恒保透明通道，输出可直接装配进 `layers.json`）：

1. **晶体热应力碎裂**（Voronoi Fracture）：根据图像反差与 Canny 边缘构建自适应密度场，经加权 Lloyd 松弛产生非均匀晶胞，沿主梯度方向施加微小刚体位移与旋转，烘焙微小硬阴影与晶体白边。用于认知破裂、机械义体、人格重构。
   ```bash
   python <scripts>/make_part.py fx voronoi parts/subject.png parts/subject_fracture.png --cells 80 --jitter 6 --gap 2
   ```
2. **莫尔拓扑干涉光栅**（Moiré Topology）：将主体明暗映射为第二层微变形线阵的相位偏移 $\phi(x,y) = \alpha \cdot I(x,y)$，Marching Squares 提取等值线，输出纯透明底高精矢量 SVG。用于欧普艺术、数字孪生、全息波纹浮现。
   ```bash
   python <scripts>/make_part.py fx moire parts/subject.png parts/subject_moire.svg --freq 18 --alpha 4.0
   ```
3. **物理重磅卡纸撕裂切片**（Shredder Slice）：结合分形撕裂噪声与高频纸浆纤维毛刺（Torn Paper Fuzz），交替横向位移与微倾角，烘焙纸芯白毛边与下压投影。支持单张错位贴纸直出，或通过 `--explode` 导出多图层切片序列。用于戏剧错位、时代断裂、多重状态。
   ```bash
   python <scripts>/make_part.py fx slice parts/subject.png parts/subject_slice.png --strips 6 --shift 18 [--explode parts/strips/]
   ```
4. **河村康辅碎纸机垂直条纹重组**（Kosuke Kawamura Vertical Shredder）：模拟日本拼贴巨擘河村康辅的碎纸机重组技法，高密度垂直切片结合多频谐波波浪、拉链式相邻跳跃（Zipper Stagger）与刀口微浮雕硬投影，产生兼具手作实体拼贴与数字故障张力的前卫质感。
   ```bash
   python <scripts>/make_part.py fx kawamura parts/subject.png parts/subject_kawamura.png --strips 70 --amplitude 50 --stagger 16
   ```
5. **印刷半调网点**（Halftone Print Dots）：将人物或物件贴纸的内部像素转换为 28° 旋转彩色印刷网点（Ben-Day Dots），用于抹除 AIGC 生成图的平滑像素指纹并强化波普画报印刷质感；保留 `14px` 纯白模切外缘与透明通道。加 `--invert` 可仅将主体内部反相为胶片负片（用于正/负双生对照封面）。
   ```bash
   python <scripts>/make_part.py fx halftone parts/subject_clean.png parts/subject.png --cell 6.5 --angle 28 [--invert]
   ```

完成标准是每个 real 元件是带透明通道的 PNG，每个 gen 元件是 SVG，fx 处理后的产物严格维持透明通道或纯净矢量，并且逐个打开看过边缘干净、无背景残留。抠不净就换模型或回到原片裁切后重抠；SVG 色块糟糕就换元件图重出该元件。

### 5. 装配与调整

按 `references/layers.example.json` 写 `layers.json`：每个元件一层，`origin` 与 `role` 必填，`z` 取 `style.md` 的参考值，各画幅的 `frames` 缺省时由编辑器兜底居中。放置位置参照 `mockup.png`。

直接双击打开 `cover.html`（或运行 `python <scripts>/cover.py edit`）即可进入交互式编辑器：拖动、方向键微调、`[ ]` 旋转、`- =` 缩放、PgUp/PgDn 调层级，切换画幅，安全区参考线可开关。点击「保存当前 PNG (Ctrl+S)」或「导出全部 4 张 PNG」可在浏览器内直接导出全尺寸高清 PNG。

### 6. 验收与多模态自检

```bash
python <scripts>/cover.py render
```

通过的标准包含**机器验收**与**Agent 多模态视觉核验**两道门禁：

1. **机器验收**（脚本自动判定）：schema（subject/title 各唯一、z 至少 4 档）、出身与格式对应（gen 为复杂路径 SVG，real 为带 alpha 的 PNG 且主体反差 $\sigma \ge 38$）、三画幅尺寸精确、标题满足安全区。若 `FAIL` 按报错改 `layers.json` 或元件后重跑。
2. **Agent 视觉自检（Visual QA · 交付红线）**：机器通过后，**必须立即调用 `read_file` 工具读取 `review.png`（四画幅总评审长板）进入多模态上下文，由 Agent 亲自肉眼审视画面**，严禁未经视觉自检直接交付。核验五项硬指标：
   - **画面无破损与解析异常**：画面中绝无 16×16 的破损图片占位图标（Broken image icon）、无缺失图层、SVG 路径无语法报错或属性冲突；
   - **道具纯净与透底**：实物道具内部不得残留原图自带的无关异物（如放大镜内意外带入的邮票/手指/水印，剪刀指环内部未抠净的底色，镂空部位必须透明透底）；
   - **构图与留白平衡**：小红书 3:4 竖图必须饱满撑起上下空间（主体位于黄金分割，标题与色块合理压实下半部，严禁人物缩成中间一小条而上下大片逼仄留白）；
   - **五官关键视线保全**：主副标题胶带与斜插道具绝不遮挡主体的五官、眼神与关键表情；
   - **文字纯净可读**：画面中仅出现 Dymo 打标胶带的主副标题文字，无任何多余符号或模型水印；在 1:1 缩略图模式下文字与主体仍完整可读。

**完成标准**：机器验收通过且 Agent 亲自目视确认上述五项全绿。若自检发现任何瑕疵，回到第 4 或 5 步修复元件/微调 `layers.json`，重新 `cover.py render` 并重新读取核验，闭环通过后方可交付。

## 交付

列出 `cover_2115x900.png`、`cover_900x900.png`、`cover_1920x1080.png`、`cover_1440x1920.png` 与 `cover.html`（`python <scripts>/cover.py edit` 随时回到编辑器），并附 `raw/sources.json` 里的公版素材出处。各尺寸默认用途：

- `cover_1920x1080.png`（16:9）：Obsidian 笔记题图、Hexo 博客文章封面
- `cover_2115x900.png`（2.35:1）：仅用于微信公众号头条封面/正文首图
- `cover_900x900.png`（1:1）：公众号次条/正方形卡片封面
- `cover_1440x1920.png`（3:4）：小红书图文封面

## 复修

用户事后要改，都只动 `layers.json`（位置、文字、颜色、层级），再 `cover.py render`。要换元件才回到步骤 3 或 4，整体换概念才回到步骤 2。
