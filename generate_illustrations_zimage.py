"""
Z-Image Turbo 全量妖怪插画生成
- 遍历 tribulations.json
- 对每个需要插画的妖怪，按 DEMON_VISUALS 的 zh 提示词生成
- 无提示词的妖怪用通用 fallback 提示词
- 输出到 illustrations/<filename>.png
- 已存在的文件会被覆盖（Flux 版已备份到 illustrations_flux_backup/）
- 支持断点续跑：每个成功生成的文件会写入 .zimage_done 标记
- 单条失败不中断整批
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

SERVER = "127.0.0.1:8188"
ROOT = "/home/jckchen/西游记"
ILLUS_DIR = f"{ROOT}/illustrations"
DONE_MARKER = ".zimage_done"  # 写入到 ILLUS_DIR/<name>.png.done 标记已生成

# 提取 DEMON_VISUALS 字典
_src = open(f"{ROOT}/generate_illustrations_flux.py", encoding="utf-8").read()
_src = _src.split("if __name__")[0] + "\nDEMON_VISUALS = DEMON_VISUALS"
_globals = {}
exec(_src, _globals)
DEMON_VISUALS = _globals["DEMON_VISUALS"]

# 通用 fallback 提示词（无 DEMON_VISUALS 条目时使用）
FALLBACK_ZH = (
    "西游记中的中国妖怪，{name}。古风插画，中国传统工笔重彩风格，"
    "唐代壁画质感，绢本设色，水墨淡彩，细腻线条，留白典雅，"
    "邪恶神秘的妖怪形象，电影感，史诗级，高质量"
)
FALLBACK_EN_STYLE = (
    "ancient Chinese demon character, classical Chinese gongbi painting style, "
    "Tang dynasty mural aesthetic, silk and color, ink wash, "
    "delicate lines, elegant white space, mysterious evil aura, masterpiece, best quality"
)


def build_workflow(prompt: str, seed: int, w=1024, h=1024):
    return {
        "28": {"inputs": {"unet_name": "z_image_turbo-Q4_K_S.gguf"}, "class_type": "UnetLoaderGGUF"},
        "30": {"inputs": {"clip_name": "Qwen_3_4b-IQ4_XS.gguf", "type": "lumina2"}, "class_type": "CLIPLoaderGGUF"},
        "29": {"inputs": {"vae_name": "ae.safetensors"}, "class_type": "VAELoader"},
        "27": {"inputs": {"text": prompt, "clip": ["30", 0]}, "class_type": "CLIPTextEncode"},
        "33": {"inputs": {"conditioning": ["27", 0]}, "class_type": "ConditioningZeroOut"},
        "13": {"inputs": {"width": w, "height": h, "batch_size": 1}, "class_type": "EmptySD3LatentImage"},
        "11": {"inputs": {"model": ["28", 0], "shift": 3}, "class_type": "ModelSamplingAuraFlow"},
        "3": {
            "inputs": {
                "model": ["11", 0],
                "positive": ["27", 0],
                "negative": ["33", 0],
                "latent_image": ["13", 0],
                "seed": seed,
                "steps": 8,
                "cfg": 1,
                "sampler_name": "res_multistep",
                "scheduler": "simple",
                "denoise": 1,
            },
            "class_type": "KSampler",
        },
        "8": {"inputs": {"samples": ["3", 0], "vae": ["29", 0]}, "class_type": "VAEDecode"},
        "9": {"inputs": {"images": ["8", 0], "filename_prefix": "zimage"}, "class_type": "SaveImage"},
    }


def queue_prompt(workflow, client_id="zimage_batch"):
    body = json.dumps({"prompt": workflow, "client_id": client_id}).encode()
    req = urllib.request.Request(f"http://{SERVER}/prompt", data=body,
                                  headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def get_history(pid):
    return json.loads(urllib.request.urlopen(f"http://{SERVER}/history/{pid}", timeout=10).read())


def wait_for_done(pid, timeout=180):
    """轮询 /history/<pid>，完成或出错都返回"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            hist = get_history(pid)
            entry = hist.get(pid, {})
            status = entry.get("status", {})
            if status.get("completed", False):
                return hist, None
            if status.get("status_str") == "error":
                return hist, status
        except urllib.error.HTTPError:
            pass
        time.sleep(1.5)
    return None, "timeout"


def collect_demons(force=False):
    """返回 [(filename, prompt)] 列表。force=True 时忽略 .done 标记重新生成"""
    with open(f"{ROOT}/tribulations.json", encoding="utf-8") as f:
        data = json.load(f)

    out = []
    seen = set()
    for t in data:
        for d in t["demons"]:
            name = d["name"]
            no_img = (name in ("无", "待考证")
                      or "(非妖怪)" in name or "（非妖怪）" in name
                      or "(人)" in name or "（人）" in name
                      or "(天庭)" in name or "（天庭）" in name)
            if no_img:
                continue
            fn = name.replace("/", "-").replace("、", "-")
            if fn in seen:
                continue
            seen.add(fn)
            out.append((fn, name))

    if not force:
        out = [(fn, name) for fn, name in out
               if not os.path.exists(f"{ILLUS_DIR}/{fn}.{DONE_MARKER}")]
    return out


def get_prompt(name):
    """返回 (zh_prompt, seed) 元组"""
    visual = DEMON_VISUALS.get(name)
    if visual and visual.get("zh"):
        zh = visual["zh"]
    else:
        zh = FALLBACK_ZH.format(name=name)
    # 强化古风风格
    prompt = (
        f"{zh} "
        "古风插画，中国传统工笔重彩风格，唐代壁画质感，"
        "绢本设色，水墨淡彩，细腻线条，留白典雅，"
        "movie still, masterpiece, best quality"
    )
    # 稳定 seed：基于名称 hash
    seed = abs(hash(name)) % (2**31)
    return prompt, seed


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="忽略 .done 标记，全部重新生成")
    ap.add_argument("--only", help="只生成指定名字（不含扩展名）")
    ap.add_argument("--limit", type=int, default=0, help="最多生成多少张（0=全部）")
    args = ap.parse_args()

    queue = collect_demons(force=args.force)
    if args.only:
        queue = [(fn, name) for fn, name in queue if fn == args.only]
    if args.limit:
        queue = queue[:args.limit]

    print(f"=== 待生成: {len(queue)} 张 ===")
    if queue:
        print(f"前 5 个: {[n for _,n in queue[:5]]}")
    print()

    success = 0
    fail = 0
    start_all = time.time()
    for i, (fn, name) in enumerate(queue, 1):
        prompt, seed = get_prompt(name)
        print(f"[{i:>3}/{len(queue)}] {name:25s} → {fn}.png  seed={seed}", flush=True)

        t0 = time.time()
        try:
            # 限流：避免连续请求压垮 ComfyUI
            time.sleep(0.5)
            client_id = f"zimg_{int(time.time())}_{i}"
            qres = queue_prompt(build_workflow(prompt, seed), client_id)
            pid = qres.get("prompt_id")
            if not pid:
                print(f"  ❌ 提交失败: {qres}")
                fail += 1
                continue

            hist, err = wait_for_done(pid, timeout=180)
            if err == "timeout":
                print(f"  ⏱ 超时（180s）")
                fail += 1
                continue
            if err is not None:
                print(f"  ❌ 错误: {json.dumps(err, ensure_ascii=False)[:200]}")
                fail += 1
                # 等待 ComfyUI 恢复
                time.sleep(5)
                continue

            # 找 SaveImage 输出
            outputs = (hist.get(pid) or {}).get("outputs", {})
            saved = False
            for nid, out in outputs.items():
                for img in out.get("images", []):
                    src = (f"http://{SERVER}/view?filename={urllib.parse.quote(img['filename'])}"
                           f"&subfolder={img.get('subfolder','')}&type=output")
                    data = urllib.request.urlopen(src, timeout=30).read()
                    dst = f"{ILLUS_DIR}/{fn}.png"
                    with open(dst, "wb") as f:
                        f.write(data)
                    # 写 done 标记
                    open(f"{ILLUS_DIR}/{fn}.{DONE_MARKER}", "w").close()
                    dt = time.time() - t0
                    print(f"  ✓ {len(data)//1024} KB · {dt:.1f}s")
                    saved = True
                    break
                if saved:
                    break
            if saved:
                success += 1
            else:
                print(f"  ❌ 输出无图像")
                fail += 1
        except Exception as e:
            print(f"  ❌ 异常: {e}")
            fail += 1
            # 异常时等待更久
            time.sleep(10)

    dt_all = time.time() - start_all
    print(f"\n=== 完成: 成功 {success} / 失败 {fail} · 用时 {dt_all:.1f}s · 平均 {dt_all/max(success,1):.1f}s/张 ===")


if __name__ == "__main__":
    main()
