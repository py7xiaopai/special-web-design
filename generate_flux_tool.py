#!/usr/bin/env python3
"""
FLUX.1-schnell 生图工具
用法: /home/jckchen/ComfyUI/venv/bin/python generate_flux_tool.py --prompt "描述" [--output path.png] [--width 512] [--height 512] [--steps 1]
产出: 图片文件路径（stdout 输出）
依赖: ComfyUI venv (diffusers + torch), FLUX.1-schnell 模型在 /home/jckchen/FLUX.1-schnell/
注意: 8GB 显存需 sequential_cpu_offload，Z-Image 与 FLUX 不能同时运行
"""
import argparse
import os
import sys
import time


def main():
    parser = argparse.ArgumentParser(description="FLUX.1-schnell 生图")
    parser.add_argument("--prompt", required=True, help="生图提示词")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--width", type=int, default=512, help="宽度 (default: 512)")
    parser.add_argument("--height", type=int, default=512, help="高度 (default: 512)")
    parser.add_argument("--steps", type=int, default=1, help="推理步数 (default: 1, schnell 推荐 1-4)")
    parser.add_argument("--seed", type=int, help="随机种子")
    parser.add_argument("--out-dir", default="/home/jckchen/西游记/illustrations",
                        help="默认输出目录")
    args = parser.parse_args()

    seed = args.seed if args.seed is not None else int(time.time() * 1000) % 2147483647

    import torch
    from diffusers import FluxPipeline

    model_path = "/home/jckchen/FLUX.1-schnell"

    if not os.path.exists(model_path):
        print(f"ERROR: 模型路径不存在: {model_path}", file=sys.stderr)
        sys.exit(1)

    print(f"加载 FLUX 模型: {model_path}", file=sys.stderr)
    pipe = FluxPipeline.from_pretrained(
        model_path,
        torch_dtype=torch.bfloat16,
        local_files_only=True,
    )

    # sequential offload: 所有参数在 CPU，用时才移到 GPU，最低显存
    print("启用 sequential CPU offload 模式", file=sys.stderr)
    pipe.enable_sequential_cpu_offload()

    print(f"开始生成 (seed={seed}, steps={args.steps}, size={args.width}x{args.height})", file=sys.stderr)
    print(f"提示词: {args.prompt[:100]}...", file=sys.stderr)

    with torch.inference_mode():
        image = pipe(
            prompt=args.prompt,
            guidance_scale=0.0,
            num_inference_steps=args.steps,
            width=args.width,
            height=args.height,
            generator=torch.Generator("cuda").manual_seed(seed),
        ).images[0]

    # 确定输出路径
    if args.output:
        dst = args.output
    else:
        safe_name = "".join(c for c in args.prompt[:30] if c.isalnum() or c in "._- ").strip().replace(" ", "_")
        if not safe_name:
            safe_name = f"flux_{int(time.time())}"
        dst = os.path.join(args.out_dir, f"{safe_name}.png")

    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    image.save(dst)
    print(dst)


if __name__ == "__main__":
    main()
