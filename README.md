# 西游取经图 · 九九八十一难

一个交互式单页 Web 应用，以《西游记》取经路线为轴，串联起九九八十一难，点击节点查看妖怪插画、危险等级与主要事件。背景是全幅古风取经地图，顶部进度条随横向滚动联动。

> 单文件前端（`index.html`），零构建步骤；插画本地用 Z-Image / Flux 生成。

## 在线演示

部署在 GitHub Pages：<https://py7xiaopai.github.io/special-web-design/>

## 特性

- **81 难串联**：从长安到天竺的完整路线，按章节串联
- **点击节点查看详情**：妖怪立绘、危险等级（1-5）、主要事件、所在章节
- **横向滚动驱动进度**：顶部进度条 + 路径动画 + 节点已访问高亮
- **古风插画**：所有妖怪立绘用本地 AI 模型（Z-Image Turbo / FLUX Schnell）生成，统一唐代壁画质感
- **纯中文 UI**

## 技术栈

- 单文件 HTML / 内联 CSS / vanilla JS（无构建、无依赖）
- SVG 路线 + 节点，路径动画用 `stroke-dasharray` / `stroke-dashoffset`
- 横向滚动：`wheel` 事件转横向 `scrollLeft`，进度由 `scroll` 位置驱动
- 数据来源：`西游记.txt` → Python 提取脚本 → `tribulations.json`（运行时 fetch）

## 本地运行

> 因为 `fetch('tribulations.json')` 在 `file://` 协议下被 CORS 拦截，必须用 HTTP server。

```bash
# 任选一种
python3 -m http.server 8000
# 或
npx serve .
# 或
php -S 127.0.0.1:8000
```

然后访问 <http://localhost:8000/>。

## 重新生成妖怪插画

插画分两个版本（独立目录）：

| 目录 | 模型 | 用途 |
|------|------|------|
| `illustrations/` | Z-Image Turbo（活动版本） | 网页默认读取 |
| `illustrations_flux_backup/` | FLUX.1-schnell（备份版本） | 旧版本存档 |

### Z-Image Turbo（推荐）

依赖本地 ComfyUI 服务（端口 8188）+ 已下载模型：

- `models/diffusion_models/z_image_turbo-Q4_K_S.gguf`
- `models/text_encoders/Qwen_3_4b-IQ4_XS.gguf`
- `models/vae/ae.safetensors`

启动 ComfyUI 后：

```bash
# 单张测试
python3 test_zimage.py

# 全量生成（自动跳过已完成的）
python3 generate_illustrations_zimage.py

# 强制重跑全部
python3 generate_illustrations_zimage.py --force
```

支持 `--only <name>` 单独生成某个妖怪，`--limit N` 限制数量。每个成功文件会写 `.zimage_done` 标记，断点续跑安全。

### FLUX Schnell（旧版）

```bash
python3 generate_illustrations_flux.py [<demon_name>]
```

## 项目结构

```
.
├── index.html                  # 唯一的前端入口
├── tribulations.json           # 81 难结构化数据（fetch 加载）
├── illustrations/              # 活动版妖怪插画（页面读取这里）
│   └── *.png
├── illustrations_flux_backup/  # FLUX 版备份（不参与页面）
├── generate_illustrations_zimage.py   # Z-Image 批量生图
├── generate_illustrations_flux.py     # FLUX 批量生图（旧）
├── test_zimage.py              # Z-Image 2 张测试
├── extract_tribulations.py     # 从 西游记.txt 抽 81 难
├── 西游记.txt                  # 原文（gitignore，但生成时需要）
├── 西游记网页设计要求.md       # 原始需求规范
└── CLAUDE.md                   # 给后续 AI/工程师的架构说明
```

## 数据来源

`西游记.txt` 中第 99 回（约 6543 行）有一段连写格式的"蒙差揭谛皈依旨谨记唐僧难数清"——80 难按"描述第N难"格式排成连续字符串。`extract_tribulations.py` 解析这段字符串得到 80 条；第 81 难（通天河遇鼋湿经书）由脚本手动追加。

## 部署到 GitHub Pages

1. Push 到 `main` 分支
2. 仓库 Settings → Pages → Source: `main` / `(root)`
3. 访问 `https://<user>.github.io/<repo>/`

无需任何构建步骤。

## 致谢

- 数据源：《西游记》原文
- 插画：本地 [ComfyUI](https://github.com/comfyanonymous/ComfyUI) + [Z-Image](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo) + [FLUX.1-schnell](https://huggingface.co/black-forest-labs/FLUX.1-schnell)
- 字体：Noto Serif SC / Source Han Serif SC / STSong / KaiTi

## 许可

源码部分以 MIT 协议开源；插画、《西游记》原文版权归原作者所有。
