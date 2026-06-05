"""
Z-Image Turbo 测试 — 生成 2 张图
通过 ComfyUI HTTP API 调用本地 Z-Image Turbo (GGUF) + Qwen3 4B 文本编码器
"""
import json
import urllib.request
import urllib.parse
import time
import os
import sys

SERVER = "127.0.0.1:8188"
PROMPT_ZH = "白骨精"  # 演示用

# 复用 generate_illustrations_flux.py 的提示词
import importlib.util
spec = importlib.util.spec_from_file_location("gif", "/home/jckchen/西游记/generate_illustrations_flux.py")
gif = importlib.util.module_from_spec(spec)
# 不执行 main 段，只取 DEMON_VISUALS 字典
gif_source = open("/home/jckchen/西游记/generate_illustrations_flux.py").read()
# 截取到 if __name__ 之前
gif_source = gif_source.split('if __name__')[0]
gif_source += "\nDEMON_VISUALS = DEMON_VISUALS"
exec(gif_source, gif.__dict__)

def build_workflow(prompt, seed, w=1024, h=1024):
    """从 Z-Image Turbo blueprint 改写，使用 GGUF 加载器"""
    return {
        # UNET
        "28": {"inputs": {"unet_name": "z_image_turbo-Q4_K_S.gguf"}, "class_type": "UnetLoaderGGUF"},
        # CLIP (Qwen3 4B)
        "30": {"inputs": {"clip_name": "Qwen_3_4b-IQ4_XS.gguf", "type": "lumina2"}, "class_type": "CLIPLoaderGGUF"},
        # VAE
        "29": {"inputs": {"vae_name": "ae.safetensors"}, "class_type": "VAELoader"},
        # 正向提示词
        "27": {"inputs": {"text": prompt, "clip": ["30", 0]}, "class_type": "CLIPTextEncode"},
        # 空负向
        "33": {"inputs": {"conditioning": ["27", 0]}, "class_type": "ConditioningZeroOut"},
        # 1024x1024 latent
        "13": {"inputs": {"width": w, "height": h, "batch_size": 1}, "class_type": "EmptySD3LatentImage"},
        # AuraFlow shift=3
        "11": {"inputs": {"model": ["28", 0], "shift": 3}, "class_type": "ModelSamplingAuraFlow"},
        # KSampler: seed, control_after_generate, 8 steps, 1 cfg, res_multistep, simple, 1 denoise
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
        # VAE Decode
        "8": {"inputs": {"samples": ["3", 0], "vae": ["29", 0]}, "class_type": "VAEDecode"},
        # 保存到 ComfyUI output/ 目录
        "9": {"inputs": {"images": ["8", 0], "filename_prefix": "zimage_test"}, "class_type": "SaveImage"},
    }


def queue_prompt(workflow, client_id="zimage_test"):
    body = json.dumps({"prompt": workflow, "client_id": client_id}).encode()
    req = urllib.request.Request(f"http://{SERVER}/prompt", data=body,
                                  headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def get_history(prompt_id):
    url = f"http://{SERVER}/history/{prompt_id}"
    return json.loads(urllib.request.urlopen(url, timeout=10).read())


def get_image(filename, subfolder, folder_type):
    qs = urllib.parse.urlencode({"filename": filename, "subfolder": subfolder, "type": folder_type})
    return f"http://{SERVER}/view?{qs}"


def wait_for_done(prompt_id, timeout=300):
    """轮询 /history/<pid>，状态非 running 即视为完成"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            hist = get_history(prompt_id)
            entry = hist.get(prompt_id, {})
            status = entry.get("status", {})
            if status.get("completed", False) or status.get("status_str") == "success":
                return hist
            if status.get("status_str") == "error":
                print(f"❌ 执行出错: {json.dumps(status, ensure_ascii=False)[:500]}")
                return hist
        except urllib.error.HTTPError:
            pass  # 还没写到 history
        time.sleep(2)
    raise TimeoutError(f"prompt {prompt_id} {timeout}s 内未完成")


def main():
    # 测试 2 张：白骨精 + 牛魔王
    # 提示词 key 复用 flux 脚本里的命名：白骨精 → "白骨夫人(白骨精)"
    test_demons = [
        ("白骨夫人(白骨精)", "白骨精.png"),
        ("牛魔王", "牛魔王.png"),
    ]
    results = []

    for i, (name, save_as) in enumerate(test_demons):
        visual = gif.DEMON_VISUALS.get(name)
        if not visual:
            print(f"⚠ 没找到 {name} 的提示词，跳过")
            continue

        # 拼一段强化古风的提示词
        prompt = (
            f"{visual['zh']} "
            "古风插画，中国传统工笔重彩风格，唐代壁画质感，"
            "绢本设色，水墨淡彩，细腻线条，留白典雅，"
            "movie still, masterpiece, best quality"
        )
        seed = 20260605 + i
        print(f"\n=== 生成 {i+1}/{len(test_demons)}: {name} → {save_as} (seed={seed}) ===")
        print(f"提示词: {prompt[:80]}...")

        workflow = build_workflow(prompt, seed)
        client_id = f"zimage_{int(time.time())}_{i}"
        qres = queue_prompt(workflow, client_id)
        pid = qres.get("prompt_id")
        if not pid:
            print(f"❌ 提交失败: {qres}")
            continue
        print(f"提交成功 prompt_id={pid}, 等待执行...")

        history = wait_for_done(pid, timeout=300)
        outputs = history.get(pid, {}).get("outputs", {})

        # 找 SaveImage 节点输出
        for nid, out in outputs.items():
            if "images" in out:
                for img in out["images"]:
                    # 从 ComfyUI 拉下来
                    src = f"http://{SERVER}/view?filename={urllib.parse.quote(img['filename'])}&subfolder={img.get('subfolder', '')}&type=output"
                    data = urllib.request.urlopen(src, timeout=30).read()
                    # 保存到项目 illustrations/ 目录
                    dst = f"/home/jckchen/西游记/illustrations/{save_as}"
                    with open(dst, "wb") as f:
                        f.write(data)
                    print(f"✓ 已保存: {dst} ({len(data)//1024} KB)")
                    results.append({"name": name, "filename": save_as, "size": len(data)})

    print(f"\n=== 完成 {len(results)}/{len(test_demons)} ===")
    for r in results:
        print(f"  {r['name']:15s} → {r['filename']:25s} ({r['size']//1024} KB)")


if __name__ == "__main__":
    main()
