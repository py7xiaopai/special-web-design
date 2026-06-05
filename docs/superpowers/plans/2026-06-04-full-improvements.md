# 西游记取经图 · 全面改进 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `index.html` 单页应用从"MVP 能跑"提升到"数据驱动、a11y、错误处理、可维护"水平，并清理仓库结构。

**Architecture:** 保持"单文件 HTML + 静态 JSON + 静态图片"零构建栈；JSON 显式持有图片文件名与坐标；HTML 消费 JSON；不引入框架。

**Tech Stack:** 原生 HTML/CSS/SVG/ESM-vanilla JS。Python 仅用于数据/图片生成脚本（不在此计划中重构）。

**Not in scope:** 重写 `extract_tribulations.py` / `generate_*.py`；重做地图背景图；更换字体。

---

## Task 1: 更新 CLAUDE.md 的 "Current State"

**Files:**
- Modify: `/home/jckchen/西游记/CLAUDE.md` (line 7)

**Why:** 当前 `CLAUDE.md` 仍写"no application code has been written yet"，与实际完全不符；后续 AI/工程师读到会得到错误预期。

- [ ] **Step 1: 重写 Current State 段（line 7）**

替换为：
```markdown
## Current State

应用已基本完成 MVP 并通过浏览器截图验证。结构如下：

- `index.html` — 单文件前端，SVG 地图 + 横向滚动 + 详情面板
- `tribulations.json` — 81 条数据（提取自 `西游记.txt` line 6543 起的列表）
- `illustrations/` — 78 张妖怪插画（ComfyUI/Flux 本地生成）
- `extract_tribulations.py` — 数据提取脚本
- `generate_illustrations_flux.py` — 主流的 Flux 图片生成脚本（取代 `generate_illustrations.py`）
- `generate_map_bg.py` — 地图背景生成脚本
- 多个 `.png` 截图与 `page-snapshot.md` — 开发/调试产出

没有框架、没有构建步骤、没有 `.codegraph/` 索引。要跑应用：浏览器打开 `index.html` 即可（需本地 HTTP server，因为 `fetch('tribulations.json')` 在 `file://` 协议下被 CORS 拦截）。
```

- [ ] **Step 2: 同步更新第 9-11 行的 "Source files" 列表**

把原来的两行（只有 .txt 和 .md）替换为：
```markdown
入口与构件：
- `index.html` — 前端入口（打开它即可）
- `tribulations.json` — 81 难结构化数据（节点坐标、妖怪、地点、章节、危险等级、事件）
- `illustrations/*.png` — 妖怪插画，文件名由 `tribulations.json` 的 `illustrationFile` 字段引用
- `extract_tribulations.py` — 从 `西游记.txt` 抽取 81 难 → `tribulations.json`
- `generate_illustrations_flux.py` — 调用本地 ComfyUI/Flux 批量生成插画
- `generate_map_bg.py` — 程序化生成古风地图背景（SVG）

源材料：
- `西游记.txt` — 小说全文（6,622 行，UTF-8 with CRLF）
- `西游记网页设计要求.md` — 用户的 7 条设计要求（权威规范）
```

- [ ] **Step 3: 删掉 "Recommended Tech Stack" 一节中已过时的"目前还没有 index.html"暗示**

第 107-115 行写的"lightweight, single-static-page appropriate for ~81 SVG nodes"和"no build step"已经和实际一致，但第 110 行的 "Framework: Plain HTML/CSS/JS with ESM modules" 还应改一下：因为目前 index.html 仍是单文件 + inline `<script>`，没用 ESM。

改为：
```markdown
- **Framework**: 纯 HTML/CSS/JS（无框架、无构建步骤）。index.html 是单文件应用。
```

- [ ] **Step 4: 在 "Open Questions" 上方插入新的 "Known Limitations" 一节**

把对话中识别的问题固化到文档里：
```markdown
## Known Limitations（已知限制）

数据/视图当前的小问题（计划在 2026-06-04 改进中处理）：
- `tribulations.json` 的 `coordinates` 字段当前未被 `index.html` 使用（HTML 改用 `Math.sin/cos` 重算），需要让其一者胜出
- "无图" 判定靠字符串里含 `'(非妖怪)'` `'(人)'` `'(天庭)'` 等子串，脆弱；应改为显式 `hasIllustration: false`
- 插画文件名靠 `name.replace(/[/、]/g, '-')` 临时生成，未处理全角符号、英文括号等；应改为 JSON 显式持有 `illustrationFile`
- 节点高亮基于"已滚动比例 × 81"近似，未点过的也算"已过"；应改为基于"已点开过的节点"
- 山/云背景用 `Math.random()`，每次刷新长得不一样，截图难回归
- fetch `tribulations.json` 失败时静默白屏，无错误提示
```
```

- [ ] **Step 5: 验证文件可读、Markdown 标题层级正确**

`Read` 一下文件确认无破损。

---

## Task 2: 重构 `tribulations.json` schema —— 显式 `hasIllustration` 和 `illustrationFile`

**Files:**
- Modify: `/home/jckchen/西游记/tribulations.json` (全部 81 条)

**Why:** 消除字符串猜测；让数据自描述；与文件目录解耦。

- [ ] **Step 1: 写一个 Python 一次性迁移脚本 `migrate_json.py`（先放项目根，不入版本）**

内容（实际执行时直接跑）：
```python
import json, os, re
from pathlib import Path

ROOT = Path('/home/jckchen/西游记')
JSON_PATH = ROOT / 'tribulations.json'
ILLUS_DIR = ROOT / 'illustrations'

# 1) 收集 illustrations/ 里的所有文件名（去后缀）
existing_files = {f.stem: f.name for f in ILLUS_DIR.glob('*.png')}

# 2) 标准化"是否需要插画"判定：基于语义标签
SKIP_TOKENS = ['(非妖怪)', '（非妖怪）', '(人)', '（人）',
               '(天庭)', '（天庭）', '无', '待考证']

def needs_illustration(name: str) -> bool:
    if name in ('无', '待考证'):
        return False
    return not any(tok in name for tok in ['(非妖怪)', '（非妖怪）',
                                          '(人)', '（人）',
                                          '(天庭)', '（天庭）'])

# 3) 候选文件名：先试原名，再试"去括号别名"
def strip_paren(name: str) -> str:
    """去掉 '(xxx)' '（xxx）' 及其内容，但保留中点分隔"""
    return re.sub(r'[（(][^）)]*[）)]', '', name).strip()

def find_illustration(name: str):
    if not needs_illustration(name):
        return None
    # 优先级：原名 → 去括号名
    if name in existing_files:
        return existing_files[name]
    bare = strip_paren(name)
    if bare and bare in existing_files:
        return existing_files[bare]
    # 文件目录里有但 JSON 没引用的(孤儿)：保留为映射的"备选"
    return None  # 当前数据盘点显示 84/84 都能找到

# 4) 加新字段、保留所有旧字段
with open(JSON_PATH, encoding='utf-8') as f:
    data = json.load(f)

for t in data:
    t['hasIllustration'] = False
    t['illustrationFile'] = None
    t['demonNames'] = []  # 平坦化妖怪名列表（保留旧 demons 数组作展示）
    for d in t['demons']:
        d['hasIllustration'] = needs_illustration(d['name'])
        d['illustrationFile'] = find_illustration(d['name'])
        t['hasIllustration'] = t['hasIllustration'] or d['hasIllustration']
        t['demonNames'].append(d['name'])

# 5) 写回（ensure_ascii=False，indent=2 与原文件风格一致）
with open(JSON_PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write('\n')

# 6) 统计
total_demons = sum(len(t['demons']) for t in data)
with_img = sum(1 for t in data for d in t['demons'] if d['hasIllustration'])
print(f'OK · 81 条已迁移 · {with_img}/{total_demons} 个妖怪有插画')
```

- [ ] **Step 2: 跑脚本并验证输出**

```bash
cd /home/jckchen/西游记 && python3 migrate_json.py
```

预期输出：
```
OK · 81 条已迁移 · 84/93 个妖怪有插画
```

（93 - 84 = 9 个无插画，包括 "无"/"待考证"/含"(非妖怪)" 等。）

- [ ] **Step 3: 抽查三条数据**

```bash
python3 -c "
import json
data = json.load(open('/home/jckchen/西游记/tribulations.json', encoding='utf-8'))
for tid in [1, 27, 81]:
    t = data[tid-1]
    print(json.dumps(t, ensure_ascii=False, indent=2))
    print('---')
"
```

预期：第 1 难（"无"）`hasIllustration: false`；第 27 难（黄风怪）`illustrationFile: "黄风怪.png"`；第 81 难（白鼋）`hasIllustration: false`。

- [ ] **Step 4: 删掉迁移脚本 `migrate_json.py`**

一次性工具，迁移完成不留。

---

## Task 3: 清理 `illustrations/` 目录（删除孤儿 + 重复）

**Files:**
- Delete: `illustrations/` 中的孤儿文件
- Modify: （可能需要根据 Task 2 步骤 3 的反馈调整）

**Why:** Task 2 后，部分 `illustrationFile` 字段没有引用一些文件。这些"孤儿"图没人引，浪费存储；保留它们容易在以后误用。

- [ ] **Step 1: 找出孤儿文件**

```bash
python3 << 'PY'
import json
from pathlib import Path
ROOT = Path('/home/jckchen/西游记')
data = json.load(open(ROOT/'tribulations.json', encoding='utf-8'))
referenced = {d['illustrationFile'] for t in data for d in t['demons'] if d['illustrationFile']}
actual = {f.name for f in (ROOT/'illustrations').glob('*.png')}
orphans = sorted(actual - referenced)
print(f'引用的图: {len(referenced)} · 实际图: {len(actual)} · 孤儿: {len(orphans)}')
for o in orphans:
    print(f'  {o}')
PY
```

预期孤儿可能包括：`白骨精.png`、`黄袍怪.png`、`金角大王.png`、`银角大王.png`、`大鹏金翅雕.png`、`虎力-鹿力-羊力大仙.png` 等（如数据盘点所示）。

- [ ] **Step 2: 删掉孤儿（先 `ls` 确认）**

```bash
ls -la /home/jckchen/西游记/illustrations/白骨精.png /home/jckchen/西游记/illustrations/黄袍怪.png
# 看着对的才执行下一步
rm /home/jckchen/西游记/illustrations/白骨精.png
# ... 依次 rm 列出的孤儿
```

> 注意：执行前必须用 `ls` 看到的所有孤儿逐一 rm，不能批量（避免错删）。

- [ ] **Step 3: 删完后核对**

```bash
ls /home/jckchen/西游记/illustrations/ | wc -l
# 预期 ≈ 78 - 孤儿数
```

---

## Task 4: 重构 `index.html` —— 数据驱动 + 修复 5 个核心问题

**Files:**
- Modify: `/home/jckchen/西游记/index.html` (line 9-465)

**Why:** 5 个最影响质量的 bug 同时修：随机背景、坐标不用 JSON、图片名硬猜、无错误处理、节点高亮语义错。

- [ ] **Step 1: 在 `el()` 辅助函数后增加 PRNG（伪随机种子生成）**

`el()` 函数下（第 371 行后）增加：
```javascript
// Mulberry32 — 可重复 PRNG，给定 seed 永远返回同样序列
function mulberry32(a) {
  return function() {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = a; t = Math.imul(t ^ t >>> 15, t | 1);
    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
const rand = mulberry32(20260604);  // 固定种子：今日日期
```

- [ ] **Step 2: 替换 `buildMap()` 中的 `Math.random()` 为 `rand()`（line 266, 268）**

第 265-269 行（山）和第 273-279 行（云）改：
```javascript
// 装饰性山水轮廓
const mountains = el('g', {opacity:0.06,fill:'#3c2415'});
for (let i = 0; i < 20; i++) {
  const mx = 100 + i * 250 + rand() * 100;
  const mh = 60 + rand() * 140;
  mountains.appendChild(el('path', {d:`M${mx},${420+rand()*200} l30,-${mh} l30,${mh*0.4} l40,-${mh*0.8} l30,${mh*0.3} l30,-${mh*0.5} l20,${mh*0.3} l30,-${mh*0.6} l25,${mh*0.4}z`}));
}
svg.appendChild(mountains);

// 装饰云纹
const clouds = el('g', {opacity:0.05,fill:'#b8943c'});
for (let i = 0; i < 12; i++) {
  const cx = 150 + i * 400, cy = 100 + Math.sin(i*1.7)*150;
  clouds.appendChild(el('circle', {cx,cy,r:35}));
  clouds.appendChild(el('circle', {cx:cx+35,cy:cy-10,r:28}));
  clouds.appendChild(el('circle', {cx:cx-20,cy:cy-15,r:22}));
}
svg.appendChild(clouds);
```

注意：`Math.sin(i*1.7)*150` 这种是**确定性**计算，不用替换。

- [ ] **Step 3: 让 `nodePositions` 使用 JSON 的 `coordinates`（line 305-310）**

```javascript
// --- 计算节点坐标 ---
// 优先用 tribulations.json 的 coordinates；缺则回退到 sin/cos 推算
nodePositions = TRIB.map((t, i) => {
  const c = t.coordinates;
  if (c && typeof c.x === 'number' && typeof c.y === 'number') {
    // coordinates 是 0-100 的相对坐标，缩放到 SVG 视口
    const x = (c.x / 100) * (MAP_W - 400) + 200;
    const y = (c.y / 100) * (MAP_H - 200) + 100;
    return {x, y, id: t.id, name: t.name, danger: t.dangerLevel};
  }
  // 回退方案（仅当 JSON 没填时）
  const p = i / 80;
  const x = 200 + p * (MAP_W - 800);
  const y = 340 + Math.sin(p * Math.PI * 5) * 130 + Math.cos(p * Math.PI * 2.7) * 70 + Math.sin(p * Math.PI * 1.5) * 80;
  return {x, y, id: t.id, name: t.name, danger: t.dangerLevel};
});
```

- [ ] **Step 4: 修 `openPanel()` 使用新字段（line 437-449）**

替换：
```javascript
document.getElementById('p-demons').innerHTML = t.demons.map(d => {
  const imgHtml = d.illustrationFile ? `
    <img src="illustrations/${d.illustrationFile}" alt="${d.name}" loading="lazy"
         onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
    <div class="img-placeholder" style="display:none">🎨 插画生成中...</div>` : '';
  return `<div class="demon-block">
    <h4>${d.hasIllustration ? '👹' : '📜'} ${escapeHtml(d.name)}</h4>
    <div class="desc">${escapeHtml(d.description)}</div>
    ${imgHtml}
  </div>`;
}).join('');
```

并在文件顶部 helper 区（第 371 行后）加 `escapeHtml`：
```javascript
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[c]));
}
```

- [ ] **Step 5: 加 fetch 错误处理（line 248-253）**

```javascript
async function init() {
  const bar = document.getElementById('progress-fill');
  const num = document.getElementById('progress-num');
  try {
    const r = await fetch('tribulations.json');
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    TRIB = await r.json();
    if (!Array.isArray(TRIB) || TRIB.length === 0) throw new Error('数据为空');
    buildMap();
    bindScroll();
  } catch (err) {
    console.error('加载失败:', err);
    num.textContent = '❌ 加载失败';
    num.style.color = 'var(--cinnabar)';
    num.style.opacity = '1';
    bar.style.background = 'var(--cinnabar)';
    document.getElementById('hint').textContent =
      '请通过 HTTP server 访问（如 `python3 -m http.server`），file:// 协议无法 fetch 本地 JSON';
  }
}
```

- [ ] **Step 6: 改"已通过"高亮语义（line 402-405）**

当前：滚动过的比例 × 81 ≈ 已点过的节点数。这是错的（没点过也算"已过"）。

修改为维护 `visitedSet`：
```javascript
const visitedIds = new Set();

function openPanel(idx) {
  // ... 原有代码
  visitedIds.add(t.id);
  updateProgress();
}

function updateProgress() {
  const route = document.getElementById('route-fg');
  const done = visitedIds.size;
  const pct = done / 81;
  document.getElementById('progress-fill').style.width = `${pct * 100}%`;
  document.getElementById('progress-num').textContent = `${done} / 81 难`;
  if (totalPathLen > 0) {
    route.style.strokeDashoffset = totalPathLen * (1 - pct);
  }
  document.querySelectorAll('.node-ring').forEach(c => {
    const id = parseInt(c.id.replace('node-',''));
    c.classList.toggle('passed', visitedIds.has(id));
  });
}
```

`bindScroll()` 中的 update 函数删掉，改为调用 `updateProgress()` 保持初始 0/81 状态（首次运行不显示"已通过"）。

- [ ] **Step 7: 给所有节点 `.click-node` 加键盘可达性 + aria**

`buildMap()` 第 338-340 行的 `g` 元素加 `tabindex="0"` 和 `role="button"`，事件加 keydown：

```javascript
g.setAttribute('tabindex', '0');
g.setAttribute('role', 'button');
g.setAttribute('aria-label', `第 ${t.id} 难 ${t.name}，危险等级 ${t.dangerLevel}`);
g.addEventListener('click', (e) => { e.stopPropagation(); openPanel(i); });
g.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault();
    openPanel(i);
  }
});
```

- [ ] **Step 8: 验证 `index.html` 没有语法错误**

启动一个本地 HTTP server 并 curl 一次（只验证文件能编译/解析，不验证视觉）：
```bash
cd /home/jckchen/西游记 && python3 -m http.server 8765 &
SERVER_PID=$!
sleep 1
curl -sI http://localhost:8765/index.html | head -1
curl -sI http://localhost:8765/tribulations.json | head -1
kill $SERVER_PID
```

预期：`HTTP/1.0 200 OK` 各一次。

> 此处不进行视觉回归（无 Playwright test 框架）。视觉验证由最终 Task 7 通过手动 + 截图完成。

---

## Task 5: 项目结构清理 —— `.gitignore` + 归档开发产物

**Files:**
- Create: `/home/jckchen/西游记/.gitignore`
- Move: 多个 `.png` 截图 + `map-bg*.png` + `page-snapshot.md` + `.playwright-mcp/`

**Why:** 仓库根目录被开发产物污染；让 git 干净。

- [ ] **Step 1: 写 `.gitignore`**

```gitignore
# 开发产物（截图/快照/临时）
screenshot-*.png
final-*.png
comfyui-open.png
demo-with-panel.png
horizontal-scroll.png
new-frontend.png
page-snapshot.md
.playwright-mcp/

# 程序生成但当前不用的背景
map-bg.png
map-bg-vertical.png

# Python 一次性脚本
migrate_json.py

# Python
__pycache__/
*.pyc

# 常见
.DS_Store
Thumbs.db
```

- [ ] **Step 2: 把 `map-bg.png` / `map-bg-vertical.png` 移到 `assets/`（而不是忽略）**

因为之前步骤 1 把它们忽略了，**改主意**：先看一下 HTML 是否真没用它们。

```bash
grep -n 'map-bg' /home/jckchen/西游记/index.html
```

预期：无匹配（HTML 已用 SVG 自绘背景）。所以保留 `.gitignore` 忽略即可，不需要移到 `assets/`。

- [ ] **Step 3: 验证 `.gitignore` 覆盖正确**

```bash
# 这些文件应被忽略（运行 git check-ignore；如未 init git 仓库则跳过）
cd /home/jckchen/西游记
# 如果没 git，跳过；否则：
git check-ignore screenshot-initial.png map-bg.png .playwright-mcp/ 2>/dev/null && echo "OK"
```

注：本项目不是 git 仓库（环境 `Is a git repository: false`），故 `git check-ignore` 会失败，属预期。`.gitignore` 仍创建好，等用户未来 `git init`。

- [ ] **Step 4: 在 `CLAUDE.md` 末尾追加一句"开发产物与正式文件的位置说明"**

```markdown
## 仓库结构与忽略

- `screenshot-*.png` / `comfyui-*.png` / `horizontal-*.png` / `new-*.png` / `final-*.png` / `demo-*.png` — 浏览器/Playwright 截图，仅作开发参考
- `page-snapshot.md` — Playwright a11y tree 快照，开发期排查用
- `.playwright-mcp/` — Playwright MCP 工具的临时缓存
- `map-bg*.png` — 早期探索的程序生成背景（当前 HTML 用 SVG 自绘背景，已弃用）
- `generate_illustrations.py`（非 `_flux`） — 早期生图脚本，被 `_flux` 版取代
- 上述文件已被 `.gitignore` 忽略
```

---

## Task 6: 加 4 个新功能（回到当前难 / 章节跳 / 危险筛选 / 图全屏）

**Files:**
- Modify: `/home/jckchen/西游记/index.html` (CSS + HTML + JS)

**Why:** 用户体验补完，路线变得真正可探索。

- [ ] **Step 1: CSS —— 加全屏图查看层、筛选条、章节跳按钮的样式**

在 `@media` 之前加（约 line 193）：
```css
/* ===== 全屏图查看 ===== */
#lightbox {
  position: fixed; inset: 0; background: rgba(0,0,0,0.85);
  z-index: 2000; display: none; align-items: center; justify-content: center;
  cursor: zoom-out;
}
#lightbox.on { display: flex; }
#lightbox img { max-width: 90vw; max-height: 90vh; box-shadow: 0 8px 40px rgba(0,0,0,0.5); }
#lightbox .caption { position: absolute; bottom: 24px; left: 0; right: 0; text-align: center; color: #fff; font-size: 16px; opacity: 0.85; }

/* ===== 顶部工具栏 ===== */
#toolbar {
  position: fixed; top: 18px; left: 20px; z-index: 1001;
  display: flex; gap: 8px; align-items: center;
  background: rgba(247,240,219,0.85); backdrop-filter: blur(4px);
  padding: 6px 10px; border-radius: 6px; border: 1px solid var(--border);
  font-size: 13px;
}
#toolbar select, #toolbar button {
  font: inherit; color: var(--ink); background: var(--paper);
  border: 1px solid var(--border); border-radius: 4px; padding: 4px 8px;
  cursor: pointer;
}
#toolbar button:hover { background: var(--gold); color: #fff; }
#toolbar label { display: flex; align-items: center; gap: 4px; cursor: pointer; }
#toolbar input[type=checkbox] { cursor: pointer; }
```

- [ ] **Step 2: HTML —— 在 progress 元素下加 toolbar 和 lightbox**

紧跟 `<div id="progress-num">`（line 203）后：
```html
<!-- 工具栏 -->
<div id="toolbar">
  <select id="jump-chapter"><option value="">按章节跳…</option></select>
  <button id="reset-view" title="滚回当前已访问的最远节点">↺ 回到当前</button>
  <span style="opacity:0.5">|</span>
  <label title="隐藏 1-2 级（安全/小险）节点"><input type="checkbox" id="filt-low"> 隐藏低危</label>
  <label title="只看 4-5 级（凶险/九死一生）"><input type="checkbox" id="filt-high"> 只看高危</label>
</div>

<!-- 全屏图查看 -->
<div id="lightbox" onclick="closeLightbox()">
  <img id="lightbox-img" alt="">
  <div class="caption" id="lightbox-cap"></div>
</div>
```

- [ ] **Step 3: JS —— 章节下拉填充 + 跳转**

在 `init()` 末尾追加 `populateChapters()` 调用，并在文件新增函数：
```javascript
function populateChapters() {
  const sel = document.getElementById('jump-chapter');
  const chapters = [...new Set(TRIB.map(t => t.chapterRef))].sort((a,b) => {
    // '第12回' < '第100回'，简单按数字排
    const na = parseInt(a.match(/\d+/)?.[0] || '0');
    const nb = parseInt(b.match(/\d+/)?.[0] || '0');
    return na - nb;
  });
  for (const ch of chapters) {
    const opt = document.createElement('option');
    opt.value = ch; opt.textContent = ch;
    sel.appendChild(opt);
  }
  sel.addEventListener('change', () => {
    const ch = sel.value;
    if (!ch) return;
    const idx = TRIB.findIndex(t => t.chapterRef === ch);
    if (idx >= 0) openPanel(idx);
    sel.value = '';
  });
}
```

- [ ] **Step 4: JS —— "回到当前"按钮**

新增：
```javascript
function scrollToCurrent() {
  if (visitedIds.size === 0) {
    // 没访问过，滚回起点
    document.getElementById('map-viewport').scrollTo({left: 0, behavior: 'smooth'});
    return;
  }
  const maxVisited = Math.max(...visitedIds);
  const idx = TRIB.findIndex(t => t.id === maxVisited);
  if (idx < 0) return;
  const pt = nodePositions[idx];
  const vp = document.getElementById('map-viewport');
  vp.scrollTo({left: Math.max(0, pt.x - vp.clientWidth / 2), behavior: 'smooth'});
}

document.getElementById('reset-view').addEventListener('click', scrollToCurrent);
```

并在 `init()` 末尾追加 `document.getElementById('reset-view').addEventListener(...)` —— 已写在上面那一步。

- [ ] **Step 5: JS —— 危险等级筛选**

新增：
```javascript
function applyFilters() {
  const hideLow = document.getElementById('filt-low').checked;
  const highOnly = document.getElementById('filt-high').checked;
  document.querySelectorAll('.click-node').forEach((g, i) => {
    const t = TRIB[i];
    let show = true;
    if (hideLow && t.dangerLevel <= 2) show = false;
    if (highOnly && t.dangerLevel < 4) show = false;
    g.style.opacity = show ? '1' : '0.15';
    g.style.pointerEvents = show ? 'auto' : 'none';
  });
}
document.getElementById('filt-low').addEventListener('change', applyFilters);
document.getElementById('filt-high').addEventListener('change', applyFilters);
```

- [ ] **Step 6: JS —— 全屏图查看**

把 `openPanel()` 里的图片 HTML 改为可点击（line 441 区域）：
```javascript
const imgHtml = d.illustrationFile ? `
  <img src="illustrations/${d.illustrationFile}" alt="${escapeHtml(d.name)}" loading="lazy"
       style="cursor:zoom-in"
       onclick="event.stopPropagation();openLightbox('illustrations/${d.illustrationFile}','${escapeHtml(d.name)} · ${escapeHtml(t.name)}')"
       onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
  <div class="img-placeholder" style="display:none">🎨 插画生成中...</div>` : '';
```

新增：
```javascript
function openLightbox(src, cap) {
  document.getElementById('lightbox-img').src = src;
  document.getElementById('lightbox-cap').textContent = cap;
  document.getElementById('lightbox').classList.add('on');
}
function closeLightbox() {
  document.getElementById('lightbox').classList.remove('on');
}
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') { closePanel(); closeLightbox(); }
});
// 已有 Escape 监听（line 461），需要合并
```

> 重复的 keydown 监听要合并。把 line 461 的 `document.addEventListener('keydown', e => { if (e.key==='Escape') closePanel(); });` 整行替换为上面那个合并版（同时关面板和 lightbox）。

- [ ] **Step 7: 验证文件能加载（HTTP 200）**

```bash
cd /home/jckchen/西游记 && python3 -m http.server 8765 &
SERVER_PID=$!
sleep 1
curl -sI http://localhost:8765/index.html | head -1
curl -sI http://localhost:8765/tribulations.json | head -1
kill $SERVER_PID
```

预期：两条 `HTTP/1.0 200 OK`。

---

## Task 7: 最终端到端验证

**Files:**
- 不修改，只验证

**Why:** 改完不能"我以为对了"。

- [ ] **Step 1: 启动 server、curl 三个关键路径**

```bash
cd /home/jckchen/西游记 && python3 -m http.server 8765 > /tmp/http.log 2>&1 &
echo $! > /tmp/http.pid
sleep 1
for path in / /index.html /tribulations.json /illustrations/黄风怪.png; do
  code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8765${path})
  echo "$code  http://localhost:8765${path}"
done
kill $(cat /tmp/http.pid) 2>/dev/null
```

预期：四行都是 `200`。

- [ ] **Step 2: 抽查 tribulations.json 的新字段**

```bash
python3 -c "
import json
data = json.load(open('/home/jckchen/西游记/tribulations.json', encoding='utf-8'))
assert all('hasIllustration' in t for t in data), '缺 hasIllustration'
assert all('demonNames' in t for t in data), '缺 demonNames'
assert all('illustrationFile' in d for t in data for d in t['demons']), '缺 illustrationFile'
print(f'OK · 81 条全部有 hasIllustration/demonNames/illustrationFile')
# 验证至少一个 known case
t1 = data[0]
assert t1['hasIllustration'] == False
assert all(d['hasIllustration'] == False for d in t1['demons']), '第1难应无插画'
print(f'第 1 难：hasIllustration = {t1[\"hasIllustration\"]} · 预期 False  ✓')
"
```

- [ ] **Step 3: 检查 illustrations/ 无孤儿**

```bash
python3 -c "
import json
from pathlib import Path
ROOT = Path('/home/jckchen/西游记')
data = json.load(open(ROOT/'tribulations.json', encoding='utf-8'))
referenced = {d['illustrationFile'] for t in data for d in t['demons'] if d['illustrationFile']}
actual = {f.name for f in (ROOT/'illustrations').glob('*.png')}
orphans = sorted(actual - referenced)
print(f'引用 {len(referenced)} · 实际 {len(actual)} · 孤儿 {len(orphans)}')
for o in orphans: print(f'  孤儿: {o}')
assert not orphans, '还有孤儿！'
print('OK')
"
```

- [ ] **Step 4: 用 Playwright MCP（如果可用）打开页面，截一张图肉眼验证**

如 `.playwright-mcp/` 工具可达：
- 访问 `http://localhost:8765/`
- 截屏
- 检查：
  - 进度条显示 `0 / 81 难`
  - 工具栏出现在左上
  - 点击任意节点 → 详情面板从左侧滑入
  - 节点高亮（"已访问"）== 0
- 截屏归档

如不可用，跳过此步，在最终回复里告诉用户"已 HTTP 200 验证，未做视觉回归，请用户自行打开浏览器看一眼"。

- [ ] **Step 5: 在最终回复中报告改动汇总**

向用户报告：
- 修改了哪些文件
- 删除了哪些图
- 哪些功能新增
- 还需要用户做的：浏览器打开 `index.html` 验证视觉（不能 `file://` 打开，要起一个 server）

---

## Self-Review

**1. Spec coverage:**
- ✅ Task 1: CLAUDE.md 更新（覆盖类别 1, 8）
- ✅ Task 2: tribulations.json schema 改造（覆盖类别 3 核心 + 部分 4）
- ✅ Task 3: 清理 illustrations/（覆盖类别 4）
- ✅ Task 4: index.html 五项核心修复（覆盖类别 2 + 5 的 #1-#5）
- ✅ Task 5: 仓库结构（覆盖类别 6）
- ✅ Task 6: 新功能（覆盖类别 7 全部 6 项中的 4 项：回到当前/章节跳/危险筛选/全屏图；未做"hover 小预览"和"前后节点高亮"——理由：UI 已够密集，YAGNI）
- ✅ Task 7: 验证

**2. Placeholder scan:** 无"TBD"；每步都有可执行内容。

**3. Type consistency:** `visitedIds` 在 Task 4 step 6 引入；`updateProgress()` 在同一步定义并被 Task 6 step 6 引用——一致。`escapeHtml()` 在 Task 4 step 4 引入并被 Task 6 step 6 复用——一致。`illustrationFile` 字段在 Task 2 JSON 中引入并被 Task 4 step 4 消费——一致。

**4. Out-of-scope 明确:** "生成脚本" 类的 Python 文件不在此计划；字体/背景图重做不在此计划；`hover 小预览` 和 `前后节点高亮` 不在此计划（YAGNI）。

---

## Execution Handoff

计划写完了。8 个类别中实际做了 7 个，hover 小预览和前后节点高亮被有意省略（UI 已够密集）。

执行方式有两种：
1. **Subagent-Driven** — 每个 Task 派一个新子 agent，我做 review
2. **Inline Execution** — 在当前会话里直接做，做完一组报一次

你想要哪种？或者直接说"全部开始"我就用 Inline 走起。
