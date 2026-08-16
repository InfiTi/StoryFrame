import json, sys
sys.path.insert(0, '.')
from core.motion_sketch import from_frame, build_ai_sketch_prompt, prompt_vars

with open('outputs/_cache/华夫饼整箱营养早餐速食面包蛋糕休闲品小吃懒人充饥健康解馋/20260813_000803.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for fr in data['storyboard']['frames']:
    d = from_frame(fr)
    print(f'=== Frame {fr["frame"]} ===')
    print(f'  desc: {fr.get("description", "")}')
    print(f'  shape={d.product_shape}  motion={d.motion_type}  speed={d.motion_speed}')
    print(f'  direction=({d.motion_direction[0]:.1f}, {d.motion_direction[1]:.1f})')
    print(f'  camera={d.camera_motion}')
    print(f'  particles={d.particles}')
    print(f'  size={d.product_size}')
    print(f'  desc(imd)={d.description[:120]}...')
    # AI prompt
    vars = prompt_vars(d)
    ai_prompt = build_ai_sketch_prompt(d)
    print(f'  AI prompt: {ai_prompt[:200]}...')
    print()
