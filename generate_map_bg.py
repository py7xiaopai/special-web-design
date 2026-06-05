"""
生成取经路线图背景
用 Flux Schnell 生成一张古风丝绸之路/取经路线地图
"""
import torch
from diffusers import FluxPipeline
import os

MODEL_PATH = "/home/jckchen/FLUX.1-schnell"
OUTPUT = "map-bg.png"

def main():
    print("正在加载 Flux Schnell...")
    pipe = FluxPipeline.from_pretrained(
        MODEL_PATH,
        torch_dtype=torch.bfloat16,
        local_files_only=True,
    )
    print("启用 sequential CPU offload...")
    pipe.enable_sequential_cpu_offload(gpu_id=0)

    # 古风取经地图提示词 - 中英文结合
    prompt_map = (
        # T5 长文本（中文描述）
        "一幅中国古代手绘风格的丝绸之路取经路线图。"
        "画面从右侧的长安城出发，蜿蜒向西经过沙漠、高山、河流，"
        "最终到达左侧的天竺灵山。"
        "沿途标有关键地点：长安、五行山、高老庄、流沙河、火焰山、"
        "通天河、西梁女国、狮驼岭、天竺。"
        "中国传统山水画风格，水墨淡彩，绢本质感，唐代壁画风格。"
        "地图上有虚线标注取经路线。"
        "古朴典雅，留白恰当。"
    )

    prompt_clip = (
        # CLIP 短文本（英文）
        "ancient Chinese silk road pilgrimage map, "
        "Tang dynasty landscape painting style, "
        "ink wash painting, parchment texture, "
        "route from Chang'an to India, "
        "traditional Chinese cartography, "
        "mountains deserts rivers, elegant minimalist"
    )

    print("正在生成背景地图 (1216x512)...")
    generator = torch.Generator(device="cpu").manual_seed(42)

    image = pipe(
        prompt=prompt_map,
        prompt_2=prompt_clip,
        width=1216,
        height=512,
        num_inference_steps=4,
        guidance_scale=0.0,
        generator=generator,
        max_sequence_length=256,
    ).images[0]

    image.save(OUTPUT)
    print(f"✓ 背景图已保存: {OUTPUT} ({os.path.getsize(OUTPUT)//1024}KB)")

    # 也生成一个竖版（移动端）
    print("正在生成竖版背景 (512x1216)...")
    image_v = pipe(
        prompt=prompt_map.replace("右侧", "上方").replace("左侧", "下方").replace("向西", "向南"),
        prompt_2=prompt_clip,
        width=512,
        height=1216,
        num_inference_steps=4,
        guidance_scale=0.0,
        generator=torch.Generator(device="cpu").manual_seed(43),
        max_sequence_length=256,
    ).images[0]

    image_v.save("map-bg-vertical.png")
    print(f"✓ 竖版背景已保存: map-bg-vertical.png ({os.path.getsize('map-bg-vertical.png')//1024}KB)")


if __name__ == "__main__":
    main()
