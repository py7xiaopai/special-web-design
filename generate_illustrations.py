"""
ComfyUI + Flux Schnell 妖怪插画批量生图脚本

用法：
  python3 generate_illustrations.py             # 生成所有妖怪插图
  python3 generate_illustrations.py --demo       # 只生成前3个妖怪测试
  python3 generate_illustrations.py --name "牛魔王"  # 只生成指定妖怪
"""
import json
import uuid
import time
import urllib.request
import urllib.parse
import sys
import os
import argparse

COMFYUI_URL = "http://localhost:8188"
OUTPUT_DIR = "illustrations"
TRIBULATIONS_FILE = "tribulations.json"

# 图片生成参数
IMAGE_WIDTH = 768
IMAGE_HEIGHT = 768
STEPS = 6  # Flux Schnell 推荐4-8步
GUIDANCE = 0.0  # Schnell 是 guidance-distilled，不需要 CFG


def queue_prompt(prompt_workflow, client_id):
    """提交工作流到 ComfyUI"""
    data = json.dumps({
        "client_id": client_id,
        "prompt": prompt_workflow
    }).encode('utf-8')

    req = urllib.request.Request(f"{COMFYUI_URL}/prompt", data=data)
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get_history(prompt_id):
    """获取执行结果"""
    with urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}") as resp:
        return json.loads(resp.read())


def get_image_url(filename, subfolder, folder_type):
    """构建图片获取URL"""
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    return f"{COMFYUI_URL}/view?{url_values}"


def download_image(url, output_path):
    """下载生成的图片"""
    try:
        with urllib.request.urlopen(url) as resp:
            with open(output_path, 'wb') as f:
                f.write(resp.read())
        return True
    except Exception as e:
        print(f"  下载失败: {e}")
        return False


def build_flux_workflow(prompt_t5xxl, prompt_clip_l, seed, width=768, height=768):
    """
    构建 Flux Schnell 工作流

    节点连接:
    1. UnetLoaderGGUF → MODEL
    2. DualCLIPLoaderGGUF → CLIP
    3. ModelSamplingFlux(MODEL) → MODEL(shifted)
    4. CLIPTextEncodeFlux(CLIP, prompts, guidance) → CONDITIONING
    5. VAELoader → VAE
    6. EmptyFlux2LatentImage(width,height) → LATENT
    7. RandomNoise(seed) → NOISE
    8. BasicScheduler(MODEL) → SIGMAS
    9. KSamplerSelect → SAMPLER
    10. BasicGuider(MODEL, CONDITIONING) → GUIDER
    11. SamplerCustomAdvanced(NOISE, GUIDER, SAMPLER, SIGMAS, LATENT) → LATENT
    12. VAEDecode(LATENT, VAE) → IMAGE
    13. SaveImage → 保存
    """
    workflow = {
        "1": {"inputs": {"unet_name": "flux1-schnell-Q4_0.gguf"}, "class_type": "UnetLoaderGGUF"},
        "2": {"inputs": {"clip_name1": "clip_l.safetensors", "clip_name2": "t5-v1_1-xxl-encoder-Q4_K_S.gguf", "type": "flux"}, "class_type": "DualCLIPLoaderGGUF"},
        "3": {"inputs": {"model": ["1", 0], "max_shift": 1.15, "base_shift": 0.5, "width": width, "height": height}, "class_type": "ModelSamplingFlux"},
        "4": {"inputs": {"clip": ["2", 0], "clip_l": prompt_clip_l, "t5xxl": prompt_t5xxl, "guidance": GUIDANCE}, "class_type": "CLIPTextEncodeFlux"},
        "5": {"inputs": {"vae_name": "ae.safetensors"}, "class_type": "VAELoader"},
        "6": {"inputs": {"width": width, "height": height, "batch_size": 1}, "class_type": "EmptyFlux2LatentImage"},
        "7": {"inputs": {"noise_seed": seed}, "class_type": "RandomNoise"},
        "8": {"inputs": {"model": ["3", 0], "scheduler": "simple", "steps": STEPS, "denoise": 1.0}, "class_type": "BasicScheduler"},
        "9": {"inputs": {"sampler_name": "euler"}, "class_type": "KSamplerSelect"},
        "10": {"inputs": {"model": ["3", 0], "conditioning": ["4", 0]}, "class_type": "BasicGuider"},
        "11": {"inputs": {"noise": ["7", 0], "guider": ["10", 0], "sampler": ["9", 0], "sigmas": ["8", 0], "latent_image": ["6", 0]}, "class_type": "SamplerCustomAdvanced"},
        "12": {"inputs": {"samples": ["11", 0], "vae": ["5", 0]}, "class_type": "VAEDecode"},
        "13": {"inputs": {"images": ["12", 0], "filename_prefix": "yaoguai"}, "class_type": "SaveImage"},
    }
    return workflow


def build_demon_prompt(demon_name, description):
    """根据妖怪名称和描述构建古风中文提示词"""
    prompts = {
        # 简化的提示词 - 让Flux理解中文
        "default": f"中国古代神话妖怪：{demon_name}。{description}。中国古典工笔画风格，细腻线条，传统水墨渲染，唐代风格，白底，高清，细节丰富。"
    }

    base = prompts.get(demon_name, prompts["default"])

    # t5xxl: 更长更详细的描述
    prompt_t5xxl = f"一幅精美的中国古风妖怪插画。妖怪名为{demon_name}。{description}。画面采用中国传统工笔重彩画风格，模仿唐代敦煌壁画和吴道子画风，线条流畅有力，色彩古朴典雅。背景素雅，突出妖怪形象。画面构图饱满，细节精细。中国古典神话艺术。"

    # clip_l: 简短描述用于CLIP-L
    prompt_clip_l = f"{demon_name}，中国古代神话中的妖怪，{description[:100]}"

    return prompt_t5xxl, prompt_clip_l


def process_demon(demon_name, description, illust_dir, client_id, retry=3):
    """为单个妖怪生成插画"""
    # 安全文件名
    safe_name = demon_name.replace("/", "-").replace("、", "-")
    output_path = os.path.join(illust_dir, f"{safe_name}.png")

    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        print(f"  ✓ {demon_name} 已有插图，跳过")
        return True

    prompt_t5xxl, prompt_clip_l = build_demon_prompt(demon_name, description)
    seed = hash(demon_name) % (2**63)  # 确定性种子

    for attempt in range(retry):
        try:
            workflow = build_flux_workflow(prompt_t5xxl, prompt_clip_l, seed)

            # 提交任务
            result = queue_prompt(workflow, client_id)
            prompt_id = result.get('prompt_id')
            if not prompt_id:
                print(f"  ✗ {demon_name}: 提交失败")
                return False

            # 等待完成 (轮询)
            max_wait = 120  # 最大等待秒数
            for _ in range(max_wait * 2):  # 每0.5秒检查
                time.sleep(0.5)
                history = get_history(prompt_id)
                if prompt_id in history:
                    break
            else:
                print(f"  ✗ {demon_name}: 超时")
                continue

            # 获取图片
            outputs = history[prompt_id].get('outputs', {})
            for node_id, node_output in outputs.items():
                if 'images' in node_output:
                    for img in node_output['images']:
                        url = get_image_url(img['filename'], img.get('subfolder', ''), img.get('type', 'output'))
                        if download_image(url, output_path):
                            file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
                            print(f"  ✓ {demon_name} ({file_size//1024}KB)")
                            return True

            print(f"  ✗ {demon_name}: 尝试{attempt+1}失败")
        except Exception as e:
            print(f"  ✗ {demon_name}: 尝试{attempt+1}异常: {e}")
            time.sleep(2)

    print(f"  ✗ {demon_name}: 已达最大重试次数")
    return False


def get_unique_demons(tribulations):
    """提取不重复的妖怪列表"""
    seen = set()
    demons = []
    for t in tribulations:
        for d in t['demons']:
            if d['name'] not in seen:
                seen.add(d['name'])
                demons.append(d)
    return demons


def main():
    parser = argparse.ArgumentParser(description='Flux 妖怪插画批量生成')
    parser.add_argument('--demo', action='store_true', help='只生成前3个妖怪测试')
    parser.add_argument('--name', type=str, help='只生成指定名称的妖怪')
    parser.add_argument('--width', type=int, default=IMAGE_WIDTH, help='图片宽度')
    parser.add_argument('--height', type=int, default=IMAGE_HEIGHT, help='图片高度')
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(TRIBULATIONS_FILE, 'r', encoding='utf-8') as f:
        tribulations = json.load(f)

    demons = get_unique_demons(tribulations)

    if args.demo:
        demons = demons[:3]
        print(f"🧪 测试模式：只生成前 {len(demons)} 个妖怪")
    elif args.name:
        demons = [d for d in demons if args.name in d['name']]
        if not demons:
            print(f"未找到妖怪: {args.name}")
            sys.exit(1)

    client_id = str(uuid.uuid4())

    print(f"🎨 开始生成 {len(demons)} 个妖怪插画...")
    print(f"   模型: Flux Schnell (GGUF Q4_0)")
    print(f"   尺寸: {args.width}x{args.height}")
    print(f"   步数: {STEPS}")
    print(f"   GPU: RTX 4060 (8GB)")
    print()

    success = 0
    for i, demon in enumerate(demons):
        print(f"[{i+1}/{len(demons)}] {demon['name']}")
        if process_demon(demon['name'], demon['description'], OUTPUT_DIR, client_id):
            success += 1

    print(f"\n完成: {success}/{len(demons)} 成功")
    print(f"插图目录: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
