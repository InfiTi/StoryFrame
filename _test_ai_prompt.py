import json, sys
sys.path.insert(0, '.')
from core.motion_sketch import from_frame, build_ai_sketch_prompt

with open('outputs/_cache/华夫饼整箱营养早餐速食面包蛋糕休闲品小吃懒人充饥健康解馋/20260813_000803.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for fr in data['storyboard']['frames']:
    d = from_frame(fr)
    prompt = build_ai_sketch_prompt(d)
    print(f'=== Frame {d.frame_num} ===')
    print(f'Prompt: {prompt}')
    print()
