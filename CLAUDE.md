# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A single-page Chinese-language web application visualizing 唐僧 (Tang Seng)'s pilgrimage as an interactive horizontally-scrollable map of the **九九八十一难** (81 tribulations). Clicking a node opens a side panel with demon illustrations, danger level, and key events. The progress bar at the top is driven by horizontal scroll position.

Deployed as a GitHub Pages site (no build step). Source text: `西游记.txt` (gitignored, only needed for re-extraction). Design spec: `西游记网页设计要求.md`.

## Running the App

The app is a single static file — no build step, no `node_modules`, no framework.

```bash
python3 -m http.server 8000
# → http://localhost:8000/
```

Opening via `file://` won't work — `fetch('tribulations.json')` is blocked under `file://` CORS. Always use a local HTTP server.

## Data Pipeline

```
西游记.txt                          (gitignored, source of truth)
  └─ extract_tribulations.py         # parses line 6543 for the 80-tribulation list
       └─ tribulations.json          # 81 entries (80 parsed + 1 manual: 通天河遇鼋湿经书)
            ├─ generate_illustrations_zimage.py  # Z-Image Turbo (active)
            │    └─ illustrations/<demon>.png   # page reads these at runtime
            └─ generate_illustrations_flux.py   # FLUX.1-schnell (legacy backup)
                 └─ illustrations_flux_backup/<demon>.png
```

### Illustration versions (双版本)

| 目录 | 模型 | 状态 |
|------|------|------|
| `illustrations/` | Z-Image Turbo (GGUF) | **活动版**，网页默认读取 |
| `illustrations_flux_backup/` | FLUX.1-schnell | 旧版备份，不被网页引用 |

切换活动版：把 `illustrations/` 改名 `illustrations_zimage/`、`illustrations_flux_backup/` 改名 `illustrations/`。两个目录的文件名规则一致。

### 1. Re-extract tribulations

```bash
python3 extract_tribulations.py
# Writes tribulations.json (81 entries)
```

Source: line 6543 (`蒙差揭谛皈依旨谨记唐僧难数清`). The 81st entry (通天河遇鼋湿经书) is added manually inside the script.

**Important**: `tribulations.json` must always have exactly 81 entries. The progress bar, node ring count, and panel all assume 81. Don't reorder entries—the order maps to the visual route from left (长安) to right (天竺). The `coordinates` field in JSON is **not** used by the renderer (which procedurally generates positions via sine/cosine in JS — see `index.html:308`).

### 2. Regenerate illustrations — Z-Image (active)

依赖：本地 ComfyUI 服务（端口 8188）+ 已下载的 GGUF 模型。模型路径：

- `models/diffusion_models/z_image_turbo-Q4_K_S.gguf`
- `models/text_encoders/Qwen_3_4b-IQ4_XS.gguf`
- `models/vae/ae.safetensors`

```bash
# 启动 ComfyUI
cd /home/jckchen/ComfyUI && ./venv/bin/python main.py --lowvram &

# 单张测试（白骨精 + 牛魔王）
python3 test_zimage.py

# 全量（自动跳过已完成的）
python3 generate_illustrations_zimage.py

# 强制重跑全部
python3 generate_illustrations_zimage.py --force

# 单独生成某个妖怪
python3 generate_illustrations_zimage.py --only <demon-name>

# 限制数量
python3 generate_illustrations_zimage.py --limit N
```

每个成功生成的文件旁会写 `.zimage_done` 标记，支持断点续跑。78 个需要插画的妖怪（81 难中共 79 个唯一妖怪名称，其中 1 个为 `白鼋(非妖怪)` 跳过）。`--lowvram` 是 8GB 显存 RTX 4060 上的安全配置。

**提示词来源**: `generate_illustrations_zimage.py` 通过 `exec()` 动态加载 `generate_illustrations_flux.py` 中的 `DEMON_VISUALS` 字典（取 `zh` 字段），没有提示词的妖怪用通用 fallback 提示词。`DEMON_VISUALS` 是 prompts 的唯一权威来源——新增妖怪时两套脚本都能用。

**自动重跑脚本**: `_zimage_loop.sh` 是一个死循环脚本，监测 ComfyUI 状态，崩了就重启，直到所有 78 张图生成完。适合无人值守大批量生成。

### 3. Regenerate illustrations — FLUX (legacy)

```bash
python3 generate_illustrations_flux.py        # 全部
python3 generate_illustrations_flux.py <name> # 单个
```

直接用 diffusers + FLUX.1-schnell，模型路径 `/home/jckchen/FLUX.1-schnell`。

### 4. Regenerate map background (legacy, currently unused)

`generate_map_bg.py` 用 FLUX 生成 `map-bg.png` 和 `map-bg-vertical.png`。当前 `index.html` 不用它们（SVG 自绘背景），脚本和 PNG 已被 `.gitignore`。

## App Architecture (`index.html`)

Single file, ~470 lines, three logical sections:

1. **CSS** (lines 7–~195): design tokens in `:root` (parchment/ink/gold/cinnabar palette, `--danger-1..5` for the 5-level scale), then layout. No framework, no preprocessor.
2. **HTML** (lines ~200–235): `#progress-wrap` (top bar) + `#map-viewport` (horizontal scroll container) + `#panel` (side detail panel) + `#overlay` (click-to-close).
3. **JS** (lines 237–465): vanilla, no ESM imports. Four functions drive the app:
   - `init()` — `fetch('tribulations.json')`, then `buildMap()` + `bindScroll()`. Falls back gracefully to an error message if the fetch fails (e.g., `file://` protocol).
   - `buildMap()` — draws decorative mountains/clouds, 8 landmark labels, then computes node positions with a sinusoidal path (line 308), generates the cubic-Bézier route string, and renders 81 clickable `<g class="click-node">` groups.
   - `bindScroll()` — wheel handler maps vertical wheel delta to horizontal `scrollLeft` (line 385), then on scroll updates `#progress-fill` width, route `stroke-dashoffset`, and `.passed` class on nodes.
   - `openPanel(idx)` — populates `#p-*` slots; if `demons[].name` matches `illustrations/<name>.png`, image is embedded with `onerror` placeholder (shows "插画生成中..." on 404).

### Coordinate system
`MAP_W = 5000`, `MAP_H = 950` (in `index.html:240`). The route is procedurally generated in JS via sine/cosine — the `coordinates` field in `tribulations.json` is **not** used by the renderer. If you want the route to honor the JSON coordinates, replace line 308's expression with `t.coordinates`.

### Danger level
Integer 1–5 → `DANGER_NAMES` (安全/小险/中等/凶险/九死一生) and `DANGER_CLRS` (green→cinnabar). Nodes with `dangerLevel >= 4` get a pulsing outer ring (line 342).

## Conventions

- **All UI in Simplified Chinese.** Don't localize to English; the spec is explicitly 中文.
- **All demon illustrations must be 古风 (classical Chinese) Tang-dynasty style** — prompts in both scripts enforce this with keywords like "唐代壁画", "工笔重彩", "绢本设色". When adding a new demon prompt, match that style vocabulary.
- **Filename contract**: `illustrations/<demon-name>.png` exactly as the demon's `name` in `tribulations.json`. The panel logic (line 438) replaces `/` and `、` with `-`; entries marked `(非妖怪)`, `(人)`, or `(天庭)` skip image lookup (line 439).
- **Don't break the 81 count.** The progress bar, node ring, and panel all assume exactly 81 entries. The 81st is always `通天河遇鼋湿经书` (manually appended in `extract_tribulations.py`).
- **All resources use relative paths** (`fetch('tribulations.json')`, `illustrations/<name>.png`) so the site works under any GitHub Pages URL path.

## Adding a Tribulation or Demon

1. Edit `tribulations.json`
2. If a new demon, add `zh` prompt to `DEMON_VISUALS` in `generate_illustrations_flux.py` (line 20+), then:
   ```bash
   python3 generate_illustrations_zimage.py --only <demon-name>
   ```
3. Refresh `index.html` — no rebuild step

## Deploying to GitHub Pages

1. Push to `main` branch (the repo root IS the site root)
2. Settings → Pages → Source: `Deploy from a branch` / `main` / `/ (root)`
3. Access at `https://<user>.github.io/<repo>/`

No build step. The `.gitignore` keeps dev artifacts (screenshots, `.playwright-mcp/`, `map-bg*.png`, regeneration markers) and the large source text out of the repo. `.nojekyll` ensures GitHub Pages serves directories/files starting with `_` properly. `404.html` is a custom 404 page with a 3-second auto-redirect to the homepage.

## Pushing Illustration Updates to GitHub

After regenerating Z-Image illustrations locally, use `_push_updated.py` to upload the new PNGs to GitHub via the Contents API:

```bash
export GH_TOKEN="github_pat_..."
python3 _push_updated.py
```

This script:
1. Scans `.zimage_done` markers to find newly generated PNGs
2. Fetches the current SHA tree from GitHub recursively (one API call)
3. Uses the Contents API to update each file with proper `sha` tracking
4. Retries on SHA mismatch (auto-retry up to 3 times)

If the repo is very large or there are many large PNGs, `_push_api.py` provides an alternative strategy that separates small files (Contents API, ≤500KB) from large PNGs (tarball via Release assets).

## Screenshot Testing

`_screenshot.py` uses Chrome DevTools Protocol to automate screenshots:
- Starts a headless Chrome instance on port 9222
- Scrolls the map to various positions and takes full-view screenshots
- Clicks on nodes and captures the side-panel view
- Saves to `screenshot-*.png` (gitignored)

## Utility Scripts Overview

| Script | Purpose |
|--------|---------|
| `test_zimage.py` | Test Z-Image pipeline: generates 2 demo images (白骨精 + 牛魔王) |
| `generate_illustrations_zimage.py` | Z-Image batch generation (active), ComfyUI HTTP API |
| `generate_illustrations_flux.py` | FLUX batch generation (legacy), diffusers pipeline + DEMON_VISUALS prompts |
| `generate_illustrations.py` | Original simple generation script (pre-FLUX/pre-ZImage era) |
| `extract_tribulations.py` | Parse 西游记.txt → tribulations.json |
| `generate_map_bg.py` | FLUX map background generation (legacy, unused) |
| `_zimage_loop.sh` | Auto-loop: run zimage → monitor ComfyUI → restart → repeat until all done |
| `_push_updated.py` | Push newly generated Z-Image PNGs to GitHub |
| `_push_api.py` | Alternative push strategy (small files via Contents API, large via Release) |
| `_screenshot.py` | Headless Chrome screenshot automation via CDP |

## Tools

- `codegraph_*` — this project is part of a large indexed workspace. For project-specific code questions, `Read` is usually enough.
- `rtk` is available globally as a token-saving proxy for `git`, `ls`, `grep`, etc. Use `rtk <cmd>` directly.
