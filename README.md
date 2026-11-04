# Collage Cover Maker · 拼贴封面引擎

> **Modern Pop Mixed-Media Collage Cover Engine in the Style of Selman Hoşgör**  
> 现代波普剪纸拼贴封面引擎：解耦 AIGC 假面，双轨材料分流，多端画幅一键装配

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![RemBG BiRefNet](https://img.shields.io/badge/segmentation-BiRefNet-brightgreen.svg)](https://github.com/danielgatis/rembg)
[![Playwright Rendering](https://img.shields.io/badge/render-Playwright%20Chromium-orange.svg)](https://playwright.dev/)

[ 🇨🇳 简体中文 ](#-简体中文) &nbsp; | &nbsp; [ 🇬🇧 English ](#-english)

---

# 🇨🇳 简体中文

## 1. 核心定位与美学哲学

在自媒体推文、深度长文与社媒运营中，传统的一体化端到端 AI 生图（如 Midjourney、DALL-E 3、FLUX）存在两个无法克服的结构性痛点：
1. **AI 塑料指纹**（Diffusion 假面）：过度平滑的漫反射皮肤、油腻反光的高光、结构混乱的几何结构与一眼即识的“AI 生成感”，极易拉低文稿的专业度与严肃可信度；
2. **像素强耦合无法微调**：文字、人物、道具、背景死死烘焙在同一张位图中。一旦需要微调标题字距、移动人物避开社媒头像遮挡，或将横版封面适配为小红书竖版，只能全图推倒重绘，且无法保证角色一致性。

**Collage Cover Maker** 确立了面向真实出版物标准的工业化解决方案：以土耳其当代插画大师 **Selman Hoşgör** 的混合媒介拼贴艺术为审美底座，采用**物理剪纸与现代波普拼贴**（Pop Paper-Cut Collage）的形式，将封面彻底解构为独立分层的实体零件。

```
                    ┌──────────────────────────────────────────────┐
                    │              文章核心议题与矛盾               │
                    └──────────────────────┬───────────────────────┘
                                           │ 动词映射与选角推导
                    ┌──────────────────────┴───────────────────────┐
                    │                   双轨材料分流                │
                    ├──────────────────────────────┬───────────────┤
                    ▼                              ▼               ▼
          【 real 摄影质感轨 】           【 gen 扁平矢量轨 】   【 tape 打标胶带 】
          • 真实历史/影棚人像主体          • 参数化干刷丙烯飞白     • 主标题（黑底白字）
          • 博物馆 CC0 隐喻实物道具       • 手绘马克笔涂鸦         • 副标题（红/蓝底）
          • BiRefNet 神经网络抠图         • 矢量切件转 SVG        • Dymo 物理立体质感
          • 14px 纯白模切边烘焙           • 路径复杂度 ≥ 25
                    │                              │               │
                    └──────────────────────┬───────┴───────────────┘
                                           │ 装配于 layers.json
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │        cover.html 本地交互工作台 (零 CORS)     │
                    │   自由拖拽 / 旋转 / 缩放 / 跨画幅自适应微调    │
                    └──────────────────────┬───────────────────────┘
                                           │
                    ┌──────────────────────┴───────────────────────┐
                    ▼                                              ▼
          【 自动化工程验收 】                           【 多端高清交付 】
          • 主体微反差 σ ≥ 38                           • 微信公号 2115×900
          • SVG 路径节点 ≥ 25                           • 转发卡片 900×900
          • 四画幅安全区合规性检测                       • 宽屏横版 1920×1080
                                                        • 小红书 3:4 1440×1920
```

### 1.1 双轨材料分流（Material Bifurcation）
每个视觉元件有且仅有两种出身，处理管道严格分立，绝不混淆：
- **real 轨**（摄影质感真实元件）：主体人像与核心实物道具。来源必须是真实相机拍摄的原片或各大博物馆（CMA、AIC、Commons）开放的 CC0 公版素材；通过神经网络抠图算法完整保住相机的真实光学噪点与质感细节，严禁使用 AI 模拟真实人像。
- **gen 轨**（平涂图形与矢量元件）：高饱和干刷丙烯厚涂（Cobalt Blue `#0052FF`、Acid Yellow `#FFE600`、Hot Pink `#FF2A85`）、黑色手绘马克笔涂鸦（脑波螺旋、闪电、星芒）与扁平插画道具。由算法参数化生成或生图后经 `vtracer` 矢量化为高精 SVG 色块，抹除一切生成式位图瑕疵。

### 1.2 零件级彻底解耦（Complete Decoupling）
- **文字与画面解耦**：画面彻底净化，生图提示词中严禁任何文本生成。所有文字退回为 Dymo 物理打标胶带（Tape Strip），在 CSS/Canvas 渲染层独立排版，文字角度、字号、边距随心所欲。
- **跨画幅独立排布**：每个元件在不同比例（微信 2.35:1、微信 1:1、宽屏 16:9、小红书 3:4）下记录独立的坐标与变换，彻底告别单图生硬拉伸或粗暴居中裁切。

---

## 2. 架构设计与文件规范

本工具链坚持“**单一真相源**”与“**离线即开即用**”的工程原则。

### 2.1 目录组织结构
项目运行于临时工作区（如 `_inbox/<slug>_assets/`）：

```text
_inbox/<slug>_assets/
├── raw/                      # 原始素材归档
│   ├── _candidates.png       # 候选人像与道具的选角拼图（带反差评分）
│   ├── subject.jpg           # 选定的真实主体原片
│   ├── prop.jpg              # 选定的真实道具原片
│   └── sources.json          # 公版出处、许可协议与客观画质指标（反差/锐度）
├── parts/                    # 切割与分流就绪的独立元件
│   ├── _index.png            # 元件总览认领图
│   ├── subject.png           # real 轨：带透明通道与 14px 模切白边的 PNG
│   ├── smear_blue.svg        # gen 轨：参数化干刷丙烯飞白
│   ├── smear_yellow.svg      # gen 轨：高饱和厚涂笔触
│   ├── doodle_bolt.svg       # gen 轨：手绘马克笔闪电涂鸦
│   └── prop.svg              # gen 轨：矢量化道具
├── mockup.png                # AI 构思阶段的全局概念效果图（仅作构图参考）
├── sheet.png                 # AIGC 阶段生成的独立元件平铺图（备用）
├── layers.json               # 核心：整个拼贴封面的唯一真相源（JSON 描述）
├── cover.html                # 编译生成的独立单页编辑器（内嵌 Base64 资产，零 CORS）
├── cover_2115x900.png        # 微信公众号头条封面（2.35:1）
├── cover_900x900.png         # 微信会话转发卡片图（1:1）
├── cover_1920x1080.png       # 宽屏高清横版封面（16:9）
├── cover_1440x1920.png       # 小红书贴文竖版封面（3:4）
└── review.png                # 验收并排全家福评审板（效果图 + 4 尺寸成品）
```

### 2.2 核心真相源：`layers.json`
封面所有的排版逻辑、图层深度穿插、各端适配坐标均固化在 `layers.json` 中：
```json
{
  "slug": "demo",
  "paper": "#F7F5F0",
  "layers": [
    {
      "id": "smear-blue",
      "kind": "image",
      "src": "parts/smear_blue.svg",
      "origin": "gen",
      "role": "decor",
      "z": 15,
      "frames": {
        "wechat": { "x": 900, "y": 420, "w": 900, "rot": -12 },
        "wide":   { "x": 960, "y": 500, "w": 900, "rot": -12 },
        "xhs":    { "x": 720, "y": 900, "w": 850, "rot": -10 }
      }
    },
    {
      "id": "subject",
      "kind": "image",
      "src": "parts/subject.png",
      "origin": "real",
      "role": "subject",
      "z": 22,
      "frames": {
        "wechat": { "x": 1057, "y": 430, "w": 560, "rot": 0 }
      }
    },
    {
      "id": "title",
      "kind": "tape",
      "text": "认知断层与思维陷阱",
      "bg": "#111111",
      "fg": "#FFFFFF",
      "role": "title",
      "z": 32,
      "frames": {
        "wechat": { "x": 1057, "y": 720, "w": 84, "rot": -2.5 }
      }
    }
  ]
}
```

---

## 3. 环境要求与依赖安装

### 3.1 运行环境
- **操作系统**：Windows 10/11、macOS、Linux
- **Python 版本**：Python 3.10+
- **基础依赖组件**：
  - `rembg[cpu]`：基于 BiRefNet 高分辨率二分图像分割神经网络的抠图引擎，默认模型 `birefnet-general-lite.onnx`（自动缓存至用户主目录 `~/.u2net/`）。
  - `opencv-python` / `numpy`：负责连通域分析、自适应膨胀轮廓生成、14px 纯白模切边（Die-cut）烘焙与画质指标计算。
  - `vtracer`：Rust 驱动的高性能栅格转矢量库，输出分层堆叠（stacked）彩色平滑 SVG。
  - `playwright`：Headless Chromium 渲染内核，驱动 CSS 噪点纸纹与亚像素文本排版的高精度离线出图。

### 3.2 一键安装命令

#### 标准安装：
```bash
# 1. 安装核心 Python 依赖包
pip install rembg[cpu] opencv-python numpy vtracer playwright requests

# 2. 初始化 Playwright 无头 Chromium 浏览器内核
playwright install chromium
```

#### 中国大陆镜像源加速安装：
```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple rembg[cpu] opencv-python numpy vtracer playwright requests
playwright install chromium
```

> [!TIP]
> **网络与离线提示**：
> - 首次运行 `python scripts/make_part.py real ...` 时，`rembg` 会自动拉取约 120MB 的 `birefnet-general-lite.onnx` 模型权重到 `~/.u2net/`。若遇到下载阻断，可提前配置代理终端，或手动将该权重文件放入该目录。
> - 公版博物馆素材检索脚本 `fetch_public.py` 内部原生集成了本地代理端口嗅探逻辑（自动探测 `127.0.0.1:12000`、`7890`、`10809`），开箱即连。

---

## 4. 工作流与核心命令速查（CLI Cheat Sheet）

```bash
# ==============================================================================
# 0. 环境就绪度自检
# ==============================================================================
python scripts/make_part.py check

# ==============================================================================
# 1. 公版摄影选角与道具免密检索（CMA / AIC / Wikimedia Commons）
# ==============================================================================
# 检索并输出带反差评分的候选人像拼图（支持 George Hurrell、MGM 1930s 影棚硬光风格）
python scripts/fetch_public.py search commons "George Hurrell portrait" --sheet raw/_candidates.png

# 在克利夫兰艺术博物馆检索摄影类公版道具
python scripts/fetch_public.py search cma "microscope" --type Photograph --limit 6

# 下载选定的 CC0 素材并自动登记客观反差/清晰度到 raw/sources.json
python scripts/fetch_public.py get "<IMAGE_URL>" raw/subject.jpg \
  --title "Portrait of Man" \
  --license "CC0" \
  --page "<SOURCE_PAGE_URL>"

# ==============================================================================
# 2. 元件加工与双轨分流处理
# ==============================================================================
# 【real 轨】：主体原片神经网络精准抠图 + 自动边缘修剪 + 14px 纯白模切白边烘焙
python scripts/make_part.py real raw/subject.jpg parts/subject.png --border 14

# 【real 轨（指定肖像精细模型）】：
python scripts/make_part.py real raw/subject.jpg parts/subject.png --model birefnet-portrait --border 14

# 【gen 轨（算法合成）】：极速生成 6 组高精细干刷丙烯飞白与马克笔涂鸦（零静态图库依赖）
python scripts/make_part.py synth parts --seed 42

# 【gen 轨（元件图切件）】：从纯白底 sprite sheet 自动切割独立道具并生成 _index.png 认领图
python scripts/make_part.py split sheet.png parts/

# 【gen 轨（矢量化）】：将切出的道具元件转化为高精色块 SVG，并注入剪裁蒙版
python scripts/make_part.py gen parts/p03.png parts/prop.svg --border 14

# ==============================================================================
# 3. 装配、编辑与多端出图
# ==============================================================================
# 将 layers.json 与所有素材打包编译为离线独立网页 cover.html
python scripts/cover.py build

# 启动本地实时交互式排版编辑器（带热回写接口）
python scripts/cover.py edit --port 8765

# 自动化工程质检、渲染四种规格成品封面（并生成并排评审板 review.png）
python scripts/cover.py render --mockup mockup.png --review
```

---

## 5. 可视化工作台与交互操作指南

通过 `cover.html` 提供的轻量级免配工作台，用户与设计者可实现**所见即所得**的毫米级排版微调。

### 5.1 零 CORS 离线架构
运行 `python scripts/cover.py build` 后，系统会将所有引用的 PNG/SVG 资产以 Base64 编码方式直接内嵌进 HTML 源码中。因此：
- 用户**无需启动任何本地 Web 服务器**；
- 直接在操作系统文件管理器中**双击** `cover.html` 即可在 Chrome/Edge 中完整运行；
- 内置离线 HTML5 Canvas 高保真渲染管线，支持带物理噪点和阴影的高清渲染。

### 5.2 交互式编辑器快捷键系统

| 交互操作 | 快捷键 / 鼠标行为 | 说明 |
| :--- | :--- | :--- |
| **选择图层** | 单击画面元件 或 在右侧列表点击 | 选中的图层显示蓝色虚线框，右侧同步显示参数 |
| **移动位置** | 鼠标直接拖拽 或 **方向键** (`↑` `↓` `←` `→`) | 方向键微调 1px；按住 `Shift` 步进 10px |
| **角度旋转** | `[`（逆时针） / `]`（顺时针） | 默认以 0.5° 步进微调；按住 `Shift` 步进 5° |
| **尺寸缩放** | `-`（缩小） / `=` 或 `+`（放大） | 精细缩放（步长 2%）；按住 `Shift` 加速缩放（步长 10%） |
| **层级穿插** | `PageUp`（上移一层） / `PageDown`（下移一层） | 调整 z-index，实现丙烯在身后、道具斜插身前的三维穿插感 |
| **文字直改** | 选中胶带图层后在右侧 `文字` 输入框编辑 | 实时刷新字距排版与黑红胶带底纹 |
| **画幅切换** | 顶部 `wechat` / `wide` / `xhs` 按钮切换 | 每个画幅独立记录元件位置、尺寸与旋转度 |
| **安全区开/关** | 点击 `安全区` 按钮 | 切换显示微信 1:1 裁剪绿框与小红书边缘避让红区 |
| **即时保存** | **Ctrl + S** / **Cmd + S** | 立即渲染导出当前画幅全尺寸高清 PNG，并自动静默更新 `layers.json` |
| **批量导出** | 点击右侧 `导出全部 4 张 PNG` | 一键并发导出微信 2.35:1、微信 1:1、宽屏 16:9 与小红书 3:4 全量图片 |

---

## 6. 机器质检与验收标准（QA）

运行 `python scripts/cover.py render` 时，自动化质检引擎将实施硬性工程审查。任何一项不符合标准，流水线将直接报错中断（`FAIL`）：

```
[PASS/FAIL Checklist]
├── 1. Schema 完整性
│   ├── 图层 id 唯一性检查（禁止同名图层）
│   ├── role=subject 必须恰好 1 个（严禁多主体冲突）
│   ├── role=title 必须恰好 1 个（主标题唯一）
│   ├── role=subtitle 至多 1 个
│   └── z 轴深度层级 ≥ 4 档（强制要求产生前后物理穿插深度）
├── 2. 材料合规与反差标准
│   ├── origin=gen 必须为 .svg，且路径控制命令 (MLCQZ) ≥ 25（彻底杜绝简笔画几何图形充数）
│   ├── origin=real 必须为带 Alpha 通道且有效透明的 PNG（严禁未抠图原片）
│   └── 主体人像灰度反差标准差必须满足：σ ≥ 38（强制剔除灰平、呆板的普通白底证件照，必须具备戏剧硬光）
├── 3. 画幅尺寸精确度
│   └── 导出像素尺寸必须严格等同于预设定义，画面均方差检测排除全白/全黑坏图
└── 4. 平台安全区合规性
    ├── 微信 (2115×900)：主副标题胶带整体及主体中心必须完全落在中央 900×900 正方保护区内
    └── 小红书 (1440×1920)：标题严禁压入顶部 80px、底部 140px 及右上角 180×180 互动避让区
```

---

## 7. 规格矩阵与输出定义

| 画幅代码 | 目标平台与应用场景 | 像素尺寸 | 比例 | 版式与安全区核心约束 |
| :--- | :--- | :--- | :--- | :--- |
| **wechat** | 微信公众号推送大图（信息流主推） | **2115 × 900** | 2.35:1 | 核心视觉、人物与标题胶带必须全部落在中央 `[607.5, 0, 900, 900]` 区域内。 |
| *(square)* | 微信单聊/朋友圈转发卡片、文章历史列表 | **900 × 900** | 1:1 | 由 `wechat` 画幅正中央自动裁切，要求缩略图模式下主标题依然清晰可读。 |
| **wide** | 官方网站文章封面、B站专栏、视频横版题图 | **1920 × 1080** | 16:9 | 标准高清晰度横向构图，强调负空间留白与波普穿插。 |
| **xhs** | 小红书首图、手机海报、竖屏资讯流 | **1440 × 1920** | 3:4 | 标题自动避开顶部 80px 状态栏、底部 140px 描述遮罩与右上角 180×180 按钮区。 |

---

# 🇬🇧 English

## 1. Core Philosophy & Aesthetics

In modern digital publishing, content curation, and social media branding, relying on end-to-end monolithic AI generation (e.g., Midjourney, DALL-E 3, FLUX) introduces two fatal structural bottlenecks:
1. **The AI Plastic Mask** (Diffusion Artifacts): Overly airbrushed skin, synthetic oily reflections, distorted geometry, and an unmistakable "AI aesthetic" that instantly degrades the credibility of serious editorial writing;
2. **Monolithic Pixel Entanglement**: Text, characters, props, and backgrounds are baked immutably into a single raster bitmap. Adjusting a headline, shifting an eye-line away from an avatar overlay, or adapting a landscape hero image into a vertical 3:4 card requires prompt rerolling, destroying character identity and layout balance.

**Collage Cover Maker** implements an industrial-grade solution inspired by Turkish mixed-media master **Selman Hoşgör**. By decoupling covers into **modern physical paper-cut pop collages**, every element is preserved as an isolated, repositionable layer.

```
                    ┌──────────────────────────────────────────────┐
                    │          Editorial Theme & Conflict          │
                    └──────────────────────┬───────────────────────┘
                                           │ Casting & Metaphor Mapping
                    ┌──────────────────────┴───────────────────────┐
                    │             Dual-Track Material Engine        │
                    ├──────────────────────────────┬───────────────┤
                    ▼                              ▼               ▼
           [ real Track: Photo ]          [ gen Track: Vector ]   [ Tape Strip Track ]
          • Studio/Historic Portraits     • Procedural Acrylic    • Main Title (Black/White)
          • Museum CC0 Metaphor Props     • Hand-drawn Doodles    • Subtitle (Red/Blue)
          • BiRefNet Neural Matting       • SVG Vectorization     • Physical Dymo Texture
          • 14px Baked Die-cut Ring       • Node Complexity ≥ 25
                    │                              │               │
                    └──────────────────────┬───────┴───────────────┘
                                           │ Assembled into layers.json
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │      cover.html Interactive Canvas (Zero-CORS)│
                    │ Drag & Drop / Rotate / Scale / Multi-Format   │
                    └──────────────────────┬───────────────────────┘
                                           │
                    ┌──────────────────────┴───────────────────────┐
                    ▼                                              ▼
           [ Automated QA Checks ]                        [ Production Exports ]
          • Subject Contrast σ ≥ 38                       • WeChat Hero: 2115×900
          • SVG Path Commands ≥ 25                        • WeChat Square: 900×900
          • Multi-Platform Safe Zones                     • Widescreen: 1920×1080
                                                          • Xiaohongshu 3:4: 1440×1920
```

### 1.1 Dual-Track Material Pipeline
Every component belongs strictly to one of two pipelines:
- **real Track** (Photographic Realism): Subject portraits and realistic metaphor props. Sourced exclusively from user-supplied camera photographs or verified CC0 / Public Domain collections (Cleveland Museum of Art, Art Institute of Chicago, Wikimedia Commons). Neural matting preserves real camera grain and optical micro-textures. AI hallucination of human faces is strictly avoided.
- **gen Track** (Flat Graphic Vectors): High-saturation acrylic paint sweeps (Cobalt Blue `#0052FF`, Acid Yellow `#FFE600`, Hot Pink `#FF2A85`), black marker doodles (cerebral spirals, thunderbolts, starbursts), and stylized flat props. Generated procedurally via mathematical algorithms or vectorized from flat sheets via `vtracer` into clean SVG paths, eliminating all generative bitmap artifacts.

### 1.2 True Component-Level Decoupling
- **Decoupled Typography**: Backgrounds and illustrations contain zero text. All headlines are rendered as Dymo-style label tape strips with independent CSS/Canvas geometry, allowing arbitrary rotation, letter-spacing, and wording changes without touching artwork.
- **Independent Multi-Format Framing**: Rather than naively scaling or cropping, each layer stores specific coordinates and transformations per aspect ratio (WeChat 2.35:1, WeChat 1:1, Widescreen 16:9, Xiaohongshu 3:4).

---

## 2. Architectural Design & Directory Specification

The toolchain adheres to the principles of a **Single Source of Truth** and **Zero-Dependency Portability**.

### 2.1 Workspace Layout
Generated assets reside within an isolated workspace directory (e.g., `_inbox/<slug>_assets/`):

```text
_inbox/<slug>_assets/
├── raw/                      # Archive of raw inputs & research
│   ├── _candidates.png       # Casting contact sheet (with contrast metric scores)
│   ├── subject.jpg           # Selected full-resolution photograph
│   ├── prop.jpg              # Selected museum CC0 metaphor prop
│   └── sources.json          # Public domain license attribution, URLs, & QA metrics
├── parts/                    # Isolated, ready-to-compose visual parts
│   ├── _index.png            # Visual overview catalog of parts
│   ├── subject.png           # real track: PNG with alpha channel & 14px die-cut border
│   ├── smear_blue.svg        # gen track: Procedural dry-brush acrylic smear
│   ├── smear_yellow.svg      # gen track: Saturated acrylic brush stroke
│   ├── doodle_bolt.svg       # gen track: Hand-drawn marker lightning bolt
│   └── prop.svg              # gen track: Vectorized metaphor prop
├── mockup.png                # Holistic conceptual mockup (composition reference only)
├── sheet.png                 # Sprite sheet of flat elements (optional)
├── layers.json               # The Single Source of Truth for cover composition
├── cover.html                # Compiled zero-CORS standalone visual editor
├── cover_2115x900.png        # WeChat article header banner (2.35:1)
├── cover_900x900.png         # WeChat message & chat card (1:1)
├── cover_1920x1080.png       # 16:9 Widescreen landscape master
├── cover_1440x1920.png       # Xiaohongshu / Rednote 3:4 portrait cover
└── review.png                # Combined evaluation sheet (mockup + 4 output renders)
```

### 2.2 The Single Truth: `layers.json`
Every coordinate, depth index, and responsive transformation is stored in `layers.json`:
```json
{
  "slug": "demo",
  "paper": "#F7F5F0",
  "layers": [
    {
      "id": "smear-blue",
      "kind": "image",
      "src": "parts/smear_blue.svg",
      "origin": "gen",
      "role": "decor",
      "z": 15,
      "frames": {
        "wechat": { "x": 900, "y": 420, "w": 900, "rot": -12 },
        "wide":   { "x": 960, "y": 500, "w": 900, "rot": -12 },
        "xhs":    { "x": 720, "y": 900, "w": 850, "rot": -10 }
      }
    },
    {
      "id": "subject",
      "kind": "image",
      "src": "parts/subject.png",
      "origin": "real",
      "role": "subject",
      "z": 22,
      "frames": {
        "wechat": { "x": 1057, "y": 430, "w": 560, "rot": 0 }
      }
    },
    {
      "id": "title",
      "kind": "tape",
      "text": "The Paradigm Shift",
      "bg": "#111111",
      "fg": "#FFFFFF",
      "role": "title",
      "z": 32,
      "frames": {
        "wechat": { "x": 1057, "y": 720, "w": 84, "rot": -2.5 }
      }
    }
  ]
}
```

---

## 3. Environment & Dependencies Installation

### 3.1 Runtime Requirements
- **Operating System**: Windows 10/11, macOS, Linux
- **Python**: Version 3.10 or higher
- **Core Packages**:
  - `rembg[cpu]`: Neural background removal powered by BiRefNet (`birefnet-general-lite.onnx`, cached in `~/.u2net/`).
  - `opencv-python` / `numpy`: Connected-component analysis, contour dilation, 14px die-cut white border baking, and contrast scoring.
  - `vtracer`: High-performance Rust-based raster-to-vector engine producing stacked color SVGs.
  - `playwright`: Headless Chromium engine for rendering CSS paper textures, subpixel font kerning, and automated exports.

### 3.2 Quick Installation

#### Standard Installation:
```bash
# 1. Install Python packages
pip install rembg[cpu] opencv-python numpy vtracer playwright requests

# 2. Install Playwright Chromium headless binary
playwright install chromium
```

#### Accelerated Installation (China Mirrors):
```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple rembg[cpu] opencv-python numpy vtracer playwright requests
playwright install chromium
```

> [!TIP]
> **Network & Offline Setup**:
> - When running `python scripts/make_part.py real ...` for the first time, `rembg` will download the `birefnet-general-lite.onnx` weights (~120MB) to `~/.u2net/`. Ensure internet access or place the pre-downloaded ONNX file into `~/.u2net/`.
> - The public domain museum search utility `fetch_public.py` automatically detects local proxy ports (`127.0.0.1:12000`, `7890`, `10809`) for stable asset fetching.

---

## 4. Workflow & CLI Cheat Sheet

```bash
# ==============================================================================
# 0. Environment Health Check
# ==============================================================================
python scripts/make_part.py check

# ==============================================================================
# 1. Public Domain Casting & Editorial Research (CMA / AIC / Commons)
# ==============================================================================
# Search Wikimedia Commons and build a contact sheet with contrast metrics
python scripts/fetch_public.py search commons "George Hurrell portrait" --sheet raw/_candidates.png

# Query Cleveland Museum of Art (CMA) for photograph props
python scripts/fetch_public.py search cma "microscope" --type Photograph --limit 6

# Download approved CC0 asset and log license & quality metrics into raw/sources.json
python scripts/fetch_public.py get "<IMAGE_URL>" raw/subject.jpg \
  --title "Portrait of Man" \
  --license "CC0" \
  --page "<SOURCE_PAGE_URL>"

# ==============================================================================
# 2. Material Processing & Dual-Track Separation
# ==============================================================================
# [real Track]: Neural matting + bounding trim + 14px white die-cut border baking
python scripts/make_part.py real raw/subject.jpg parts/subject.png --border 14

# [real Track (Portrait-Specific Model)]:
python scripts/make_part.py real raw/subject.jpg parts/subject.png --model birefnet-portrait --border 14

# [gen Track (Procedural Synth)]: Generate 6 dynamic acrylic smears & doodles (zero image hoarding)
python scripts/make_part.py synth parts --seed 42

# [gen Track (Sprite Sheet Splitting)]: Split flat props on pure white ground & build _index.png
python scripts/make_part.py split sheet.png parts/

# [gen Track (Vectorization)]: Convert isolated prop into stacked SVG with silhouette clipping
python scripts/make_part.py gen parts/p03.png parts/prop.svg --border 14

# ==============================================================================
# 3. Assembly, Interactive Editing & Production Rendering
# ==============================================================================
# Compile layers.json and assets into a standalone, zero-CORS cover.html
python scripts/cover.py build

# Start local interactive workbench with auto-save HTTP listener
python scripts/cover.py edit --port 8765

# Run automated QA validation and render all production PNGs + review.png
python scripts/cover.py render --mockup mockup.png --review
```

---

## 5. Visual Workbench & Interactive Controls

The compiled `cover.html` provides a lightweight, browser-based graphical editing environment for rapid fine-tuning.

### 5.1 Zero-CORS Local Architecture
When `python scripts/cover.py build` runs, all linked PNG and SVG assets are encoded into Base64 data URIs and embedded directly inside `cover.html`.
- **No Web Server Required**: Simply double-click `cover.html` to open it locally via `file:///` in Google Chrome or Microsoft Edge.
- **Built-in Canvas Exporter**: Generates full-resolution PNGs directly in-memory, faithfully replicating noise texture layers and drop shadows.

### 5.2 Keyboard & Mouse Shortcuts

| Action | Control / Keybinding | Description |
| :--- | :--- | :--- |
| **Select Layer** | Click element on canvas or list item | Selected item displays a blue dashed outline |
| **Translate / Move** | Drag with mouse or **Arrow Keys** | Arrow keys move by 1px; hold `Shift` to move by 10px |
| **Rotate** | `[` (Counter-clockwise) / `]` (Clockwise) | Rotates by 0.5°; hold `Shift` for 5° steps |
| **Scale / Resize** | `-` (Shrink) / `=` or `+` (Enlarge) | Adjusts size by 2%; hold `Shift` for 10% steps |
| **Z-Order Layering** | `PageUp` (Bring forward) / `PageDown` (Send back) | Rearranges depth index for 3D paper-cut overlapping |
| **Edit Typography** | Type in the `文字` field on the right sidebar | Updates tape text, letter-spacing, and background pads live |
| **Switch Formats** | Click `wechat`, `wide`, or `xhs` tab buttons | Custom coordinates and scale are tracked per format |
| **Safe Guides** | Click `安全区` button | Toggles WeChat 1:1 green boundary and Xiaohongshu red zones |
| **Instant Save** | **Ctrl + S** / **Cmd + S** | Renders current format PNG and quietly writes back to `layers.json` |
| **Export All** | Click `导出全部 4 张 PNG` | Batch exports all 4 format PNGs to disk |

---

## 6. Automated Quality Assurance (QA Criteria)

When running `python scripts/cover.py render`, the built-in QA engine executes rigid geometric, stylistic, and optical validations. Violations result in an immediate `FAIL`:

```
[QA Acceptance Criteria]
├── 1. Schema & Layer Integrity
│   ├── Unique layer IDs (duplicate IDs prohibited)
│   ├── Exactly 1 layer with role="subject"
│   ├── Exactly 1 layer with role="title"
│   ├── At most 1 layer with role="subtitle"
│   └── At least 4 distinct z-index levels (enforces physical spatial layering)
├── 2. Material & Optical Fidelity
│   ├── origin="gen" layers MUST be .svg with ≥ 25 path commands (bans simplistic geometric icons)
│   ├── origin="real" layers MUST be RGBA PNGs with valid non-opaque alphas
│   └── Subject portrait contrast MUST satisfy: σ ≥ 38 (eliminates flat, lifeless passport photos)
├── 3. Precision Render Checks
│   └── Exact pixel matching with target format presets; zero near-blank frames allowed
└── 4. Platform Safe Zone Compliance
    ├── WeChat (2115×900): Title/subtitle tape and subject center MUST be inside [607.5, 0, 900, 900]
    └── Xiaohongshu (1440×1920): Text prohibited from top 80px, bottom 140px, and top-right 180×180
```

---

## 7. Specifications & Output Definitions

| Format Code | Target Application | Dimensions | Aspect Ratio | Constraints & Platform Rules |
| :--- | :--- | :--- | :--- | :--- |
| **wechat** | WeChat Official Account Hero Banner | **2115 × 900** | 2.35:1 | Essential visual center and title tape must reside inside `[607.5, 0, 900, 900]`. |
| *(square)* | WeChat Chat Cards & Article List Thumbnails | **900 × 900** | 1:1 | Auto-extracted from the exact center of `wechat` format. Headline must remain legible. |
| **wide** | Website Articles, Bilibili Column, Video Covers | **1920 × 1080** | 16:9 | Clean widescreen balance with ample negative space. |
| **xhs** | Xiaohongshu / Rednote Feeds, Mobile Posters | **1440 × 1920** | 3:4 | Avoids top 80px status bar, bottom 140px caption zone, and top-right 180×180 action icon area. |

---

<p align="center">
  Crafted with care for high-signal digital publishing. Decoupled, reproducible, and publisher-grade.
</p>
