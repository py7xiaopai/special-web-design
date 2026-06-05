#!/usr/bin/env python3
"""
Z-Image Turbo 生图工具
用法: python3 generate_image_zimage.py --prompt "描述" [--output path.png] [--width 1024] [--height 1024] [--seed 42]
产出: 图片文件路径（stdout 输出）
依赖: ComfyUI 运行在 127.0.0.1:8188，GGUF 模型已加载
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request

SERVER = "127.0.0.1:8188"
# 默认输出目录（与项目 illustrations 目录一致）
DEFAULT_OUT = "/home/jckchen/西游记/illustrations"
COMFY_OUT = "/home/jckchen/ComfyUI/output"


def build_workflow(prompt: str, seed: int, w=1024, h=1024):
    """构建 Z-Image Turbo ComfyUI workflow"""
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
        "9": {"inputs": {"images": ["8", 0], "filename_prefix": "zimage_tool"}, "class_type": "SaveImage"},
    }


def queue_prompt(workflow, client_id="zimage_tool"):
    """提交 workflow 到 ComfyUI"""
    body = json.dumps({"prompt": workflow, "client_id": client_id}).encode()
    req = urllib.request.Request(
        f"http://{SERVER}/prompt",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def get_history(pid):
    """获取历史记录"""
    return json.loads(urllib.request.urlopen(f"http://{SERVER}/history/{pid}", timeout=10).read())


def wait_for_done(pid, timeout=300):
    """轮询直到生成完成"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            hist = get_history(pid)
            entry = hist.get(pid, {})
            status = entry.get("status", {})
            if status.get("completed", False):
                return hist, None
            if status.get("status_str") == "error":
                return hist, f"ComfyUI error: {status}"
        except urllib.error.HTTPError:
            pass
        time.sleep(2)
    return None, f"timeout after {timeout}s"


def find_output_image(hist, pid):
    """从 history 中找生成的图片文件名"""
    entry = hist.get(pid, {})
    outputs = entry.get("outputs", {})
    for node_id, node_output in outputs.items():
        images = node_output.get("images", [])
        if images:
            return images[0]  # {"filename": "...", "subfolder": "...", "type": "output"}
    return None


def main():
    parser = argparse.ArgumentParser(description="Z-Image Turbo 生图")
    parser.add_argument("--prompt", required=True, help="生图提示词")
    parser.add_argument("--output", help="输出文件路径（默认: <out_dir>/<basename>.png）")
    parser.add_argument("--width", type=int, default=1024, help="宽度 (default: 1024)")
    parser.add_argument("--height", type=int, default=1024, help="高度 (default: 1024)")
    parser.add_argument("--seed", type=int, help="随机种子 (default: 随机)")
    parser.add_argument("--out-dir", default=DEFAULT_OUT, help=f"默认输出目录 (default: {DEFAULT_OUT})")
    args = parser.parse_args()

    seed = args.seed if args.seed is not None else int(time.time() * 1000) % 2147483647

    # 1. 提交任务
    workflow = build_workflow(args.prompt, seed, args.width, args.height)
    try:
        result = queue_prompt(workflow)
    except Exception as e:
        print(f"ERROR: 无法连接 ComfyUI ({SERVER}): {e}", file=sys.stderr)
        sys.exit(1)

    pid = result.get("prompt_id")
    if not pid:
        print("ERROR: 未获取到 prompt_id", file=sys.stderr)
        sys.exit(1)

    print(f"任务已提交 (pid={pid}, seed={seed})", file=sys.stderr)

    # 2. 等待完成
    hist, err = wait_for_done(pid)
    if err:
        print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)

    # 3. 找到输出图片
    img_info = find_output_image(hist, pid)
    if not img_info:
        print("ERROR: 未找到输出图片", file=sys.stderr)
        sys.exit(1)

    # 4. 复制到目标位置
    src = os.path.join(COMFY_OUT, img_info["filename"])
    if not os.path.exists(src):
        # 可能在 subfolder 里
        sub = img_info.get("subfolder", "")
        if sub:
            src = os.path.join(COMFY_OUT, sub, img_info["filename"])

    if not os.path.exists(src):
        print(f"ERROR: 源文件不存在: {src}", file=sys.stderr)
        sys.exit(1)

    # 确定输出路径
    if args.output:
        dst = args.output
    else:
        # 用 prompt 前 30 个非 ASCII 字符作为文件名
        safe_name = "".join(c for c in args.prompt[:30] if c.isalnum() or c in "._- ").strip().replace(" ", "_")
        if not safe_name:
            safe_name = f"zimage_{pid[:8]}"
        dst = os.path.join(args.out_dir, f"{safe_name}.png")

    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    import shutil
    shutil.copy2(src, dst)
    print(dst)


if __name__ == "__main__":
    main()
