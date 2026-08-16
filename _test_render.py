import json, sys, os
sys.path.insert(0, '.')
from core.motion_sketch import from_frame, MotionSketchRenderer

with open('outputs/_cache/华夫饼整箱营养早餐速食面包蛋糕休闲品小吃懒人充饥健康解馋/20260813_000803.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

os.makedirs('outputs/_test_sketch', exist_ok=True)
for fr in data['storyboard']['frames']:
    d = from_frame(fr)
    renderer = MotionSketchRenderer()
    img = renderer.render(d)
    path = f'outputs/_test_sketch/sketch_{d.frame_num}.png'
    img.save(path)
    print(f'Frame {d.frame_num}: saved {path} ({img.size}), motion={d.motion_type}, dir=({d.motion_direction[0]:.1f},{d.motion_direction[1]:.1f}), camera={d.camera_motion}, particles={d.particles}')

print('\nAll 6 frames rendered successfully.')
